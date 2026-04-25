"""Settings management view — business profile, language, tone, categories, menu, keywords, blocked phrases."""

import random
import re

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods, require_POST

from accounts.models import User
from reviews.business_types import (
    TYPE_REGISTRY,
    default_categories_for,
    grouped_choices,
)
from reviews.fallback import build_fallback_variants

from .models import (
    BusinessCategory,
    BusinessSettings,
    LANGUAGE_CHOICES,
    LANGUAGE_HINGLISH,
    LANGUAGE_HINGLISH_DEV,
    LANGUAGE_ENGLISH,
    TONE_CHOICES,
    LENGTH_CHOICES,
)


_KEY_RE = re.compile(r"[^a-z0-9]+")


def _slugify_key(value: str) -> str:
    cleaned = _KEY_RE.sub("_", value.strip().lower()).strip("_")
    return cleaned[:60] or "category"


def _plan_allows_pro(user) -> bool:
    """Custom keywords, blocked phrases, and negative filter are Growth+ features."""
    if not user.is_authenticated:
        return False
    return user.has_active_subscription and user.subscription_plan in (User.PLAN_GROWTH, User.PLAN_BUSINESS)


def _plan_language_options(user):
    """Starter: English + Hinglish only. Growth/Business: all modes."""
    if _plan_allows_pro(user):
        return LANGUAGE_CHOICES
    allowed = {LANGUAGE_ENGLISH, LANGUAGE_HINGLISH, LANGUAGE_HINGLISH_DEV}
    return [(code, label) for code, label in LANGUAGE_CHOICES if code in allowed]


def _build_sample_preview(settings_obj: BusinessSettings, business_name: str) -> str:
    variants = build_fallback_variants(settings_obj.language_mode, business_name, settings_obj.review_length)
    return random.choice(variants)["text"] if variants else ""


def _reseed_categories_for_type(business, new_type: str):
    """When the owner switches business type, replace untouched categories with the new type's defaults.

    Untouched = every existing top-level category came from the previous type's
    default set. If the owner has added/renamed/disabled anything, we leave the
    existing rows alone (only seed new defaults that don't already exist).
    """
    existing_keys = set(
        BusinessCategory.objects.filter(business=business, parent__isnull=True).values_list("key", flat=True)
    )
    prev_default_keys = {c["key"] for c in default_categories_for(business.business_type)}

    if existing_keys and existing_keys.issubset(prev_default_keys):
        # Untouched — wipe and re-seed for new type.
        BusinessCategory.objects.filter(business=business).delete()
        for index, cat in enumerate(default_categories_for(new_type)):
            BusinessCategory.objects.create(
                business=business,
                parent=None,
                key=cat["key"],
                label=cat["label"],
                is_enabled=True,
                sort_order=index * 10,
            )
        return

    # Customised — only fill in defaults that the owner doesn't already have.
    for index, cat in enumerate(default_categories_for(new_type)):
        if cat["key"] in existing_keys:
            continue
        BusinessCategory.objects.create(
            business=business,
            parent=None,
            key=cat["key"],
            label=cat["label"],
            is_enabled=True,
            sort_order=(len(existing_keys) + index) * 10,
        )


def _build_category_tree(business) -> list[dict]:
    """List of dicts the template renders. Each parent has a `subcategories` list."""
    rows = list(
        BusinessCategory.objects
        .filter(business=business)
        .order_by("sort_order", "label")
    )
    by_parent: dict[int | None, list[BusinessCategory]] = {}
    for r in rows:
        by_parent.setdefault(r.parent_id, []).append(r)

    tree: list[dict] = []
    for parent in by_parent.get(None, []):
        tree.append({
            "row": parent,
            "subcategories": by_parent.get(parent.id, []),
        })
    return tree


@login_required
@require_http_methods(["GET", "POST"])
def settings_page(request):
    business = request.user.businesses.first()
    if not business:
        return redirect("business_onboarding")

    settings_obj, _ = BusinessSettings.objects.get_or_create(business=business)
    pro_allowed = _plan_allows_pro(request.user)
    language_options = _plan_language_options(request.user)
    valid_type_keys = set(TYPE_REGISTRY.keys())

    if request.method == "POST":
        # ---- Business profile (type) ----
        posted_type = request.POST.get("business_type", business.business_type)
        if posted_type in valid_type_keys and posted_type != business.business_type:
            with transaction.atomic():
                _reseed_categories_for_type(business, posted_type)
                business.business_type = posted_type
                business.save(update_fields=["business_type"])

        allowed_languages = {code for code, _ in language_options}
        posted_language = request.POST.get("language_mode", settings_obj.language_mode)
        if posted_language in allowed_languages:
            settings_obj.language_mode = posted_language

        posted_tone = request.POST.get("tone_mode", settings_obj.tone_mode)
        if posted_tone in {code for code, _ in TONE_CHOICES}:
            settings_obj.tone_mode = posted_tone

        posted_length = request.POST.get("review_length", settings_obj.review_length)
        if posted_length in {code for code, _ in LENGTH_CHOICES}:
            settings_obj.review_length = posted_length

        settings_obj.allow_customer_language_change = bool(request.POST.get("allow_customer_language_change"))
        settings_obj.mention_business_name = bool(request.POST.get("mention_business_name"))

        # ---- Categories: per-row enable toggle and label rename ----
        owner_categories = BusinessCategory.objects.filter(business=business)
        for row in owner_categories:
            posted_label = (request.POST.get(f"category_label_{row.id}") or "").strip()
            posted_enabled = bool(request.POST.get(f"category_enabled_{row.id}"))
            changed = False
            if posted_label and posted_label != row.label:
                row.label = posted_label[:120]
                changed = True
            if posted_enabled != row.is_enabled:
                row.is_enabled = posted_enabled
                changed = True
            if changed:
                row.save(update_fields=["label", "is_enabled"])

        raw_items = [v.strip()[:80] for v in request.POST.getlist("menu_items") if v.strip()]
        seen = set()
        settings_obj.menu_items = [i for i in raw_items if not (i in seen or seen.add(i))][:100]

        if pro_allowed:
            try:
                threshold = int(request.POST.get("negative_filter_threshold", settings_obj.negative_filter_threshold))
                if threshold in (1, 2, 3):
                    settings_obj.negative_filter_threshold = threshold
            except (TypeError, ValueError):
                pass

            raw_kw = [v.strip()[:60] for v in request.POST.getlist("custom_keywords") if v.strip()]
            seen = set()
            settings_obj.custom_keywords = [k for k in raw_kw if not (k in seen or seen.add(k))][:25]

            raw_bp = [v.strip()[:60] for v in request.POST.getlist("blocked_phrases") if v.strip()]
            seen = set()
            settings_obj.blocked_phrases = [b for b in raw_bp if not (b in seen or seen.add(b))][:25]

        settings_obj.save()
        messages.success(request, "Settings saved.")
        return redirect("settings_page")

    preview = _build_sample_preview(settings_obj, business.name)
    category_tree = _build_category_tree(business)
    parent_choices = [
        (row["row"].id, row["row"].label)
        for row in category_tree
    ]

    return render(
        request,
        "settings/index.html",
        {
            "business": business,
            "settings_obj": settings_obj,
            "business_type_choices": list(grouped_choices()),
            "language_options": language_options,
            "tone_options": TONE_CHOICES,
            "length_options": LENGTH_CHOICES,
            "category_tree": category_tree,
            "parent_choices": parent_choices,
            "menu_items": settings_obj.menu_items or [],
            "custom_keywords": settings_obj.custom_keywords or [],
            "blocked_phrases": settings_obj.blocked_phrases or [],
            "threshold_options": [1, 2, 3],
            "pro_allowed": pro_allowed,
            "preview": preview,
        },
    )


@login_required
@require_POST
def category_add(request):
    business = request.user.businesses.first()
    if not business:
        return redirect("business_onboarding")

    label = (request.POST.get("label") or "").strip()
    if not label:
        messages.error(request, "Category name cannot be empty.")
        return redirect("settings_page")

    parent_id = request.POST.get("parent_id") or ""
    parent = None
    if parent_id:
        try:
            parent = BusinessCategory.objects.get(pk=int(parent_id), business=business, parent__isnull=True)
        except (BusinessCategory.DoesNotExist, ValueError):
            messages.error(request, "Invalid parent category.")
            return redirect("settings_page")

    base_key = _slugify_key(label)
    key = base_key
    suffix = 2
    while BusinessCategory.objects.filter(business=business, parent=parent, key=key).exists():
        key = f"{base_key}_{suffix}"
        suffix += 1

    last_order = (
        BusinessCategory.objects
        .filter(business=business, parent=parent)
        .order_by("-sort_order")
        .values_list("sort_order", flat=True)
        .first()
    )
    next_order = (last_order or 0) + 10

    try:
        BusinessCategory.objects.create(
            business=business,
            parent=parent,
            key=key,
            label=label[:120],
            is_enabled=True,
            sort_order=next_order,
        )
    except IntegrityError:
        messages.error(request, "Could not add — a category with this name already exists.")
        return redirect("settings_page")

    if parent:
        messages.success(request, f"Subcategory “{label}” added under “{parent.label}”.")
    else:
        messages.success(request, f"Category “{label}” added.")
    return redirect("settings_page")


@login_required
@require_POST
def category_delete(request, category_id: int):
    business = request.user.businesses.first()
    if not business:
        return redirect("business_onboarding")

    row = get_object_or_404(BusinessCategory, pk=category_id, business=business)
    label = row.label
    row.delete()  # cascades to subcategories
    messages.success(request, f"Removed “{label}”.")
    return redirect("settings_page")
