"""Settings management view — business profile, language, tone, categories, menu, keywords, blocked phrases."""

import random

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from accounts.models import User
from reviews.business_types import (
    TYPE_REGISTRY,
    default_categories_for,
    default_categories_map,
    grouped_choices,
)
from reviews.fallback import build_fallback_variants

from .models import (
    BusinessSettings,
    DEFAULT_CATEGORIES,
    LANGUAGE_CHOICES,
    LANGUAGE_HINGLISH,
    LANGUAGE_HINGLISH_DEV,
    LANGUAGE_ENGLISH,
    TONE_CHOICES,
    LENGTH_CHOICES,
)


# Legacy 4-category default set — if categories_enabled matches this exactly,
# we assume the owner never customised it and re-seed from the new type registry.
_LEGACY_DEFAULT_KEYS = frozenset({"food", "staff", "service", "ambiance"})


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


def _categories_look_untouched(cats: dict) -> bool:
    """Heuristic: the categories map is either empty or still the legacy 4-item default."""
    if not cats:
        return True
    keys = {k for k, v in cats.items() if v}
    return keys.issubset(_LEGACY_DEFAULT_KEYS) or keys == set(DEFAULT_CATEGORIES.keys())


def _maybe_reseed_categories(business, settings_obj: BusinessSettings, new_type: str):
    """When business type changes and categories haven't been customised, reseed."""
    if business.business_type == new_type:
        return False
    if not _categories_look_untouched(settings_obj.categories_enabled):
        return False
    settings_obj.categories_enabled = default_categories_map(new_type)
    return True


@login_required
@require_http_methods(["GET", "POST"])
def settings_page(request):
    business = request.user.businesses.first()
    if not business:
        return redirect("business_onboarding")

    settings_obj, _ = BusinessSettings.objects.get_or_create(business=business)
    pro_allowed = _plan_allows_pro(request.user)
    language_options = _plan_language_options(request.user)

    # Category chips available in the UI are driven by the current business type.
    type_default_categories = default_categories_for(business.business_type)
    valid_type_keys = set(TYPE_REGISTRY.keys())

    if request.method == "POST":
        # ---- Business profile (type) ----
        posted_type = request.POST.get("business_type", business.business_type)
        if posted_type in valid_type_keys and posted_type != business.business_type:
            _maybe_reseed_categories(business, settings_obj, posted_type)
            business.business_type = posted_type
            business.save(update_fields=["business_type"])
            # Refresh defaults for the category checkbox rendering below
            type_default_categories = default_categories_for(business.business_type)

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

        # Categories: which chips are enabled. Only accept keys that belong
        # to this business type's registry entry.
        type_cat_keys = [c["key"] for c in type_default_categories]
        cats = {}
        for key in type_cat_keys:
            cats[key] = bool(request.POST.get(f"category_{key}"))
        # Preserve any custom keys the owner already had set and didn't post
        # (so one accidental type change doesn't wipe customisations):
        for k, v in (settings_obj.categories_enabled or {}).items():
            if k not in cats:
                cats[k] = v
        settings_obj.categories_enabled = cats

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

    # Build category rows — union of type defaults and any previously saved keys,
    # so owners don't lose custom chips when rendering.
    saved_cats = settings_obj.categories_enabled or {}
    type_keys = [c["key"] for c in type_default_categories]
    ordered_keys: list[str] = list(type_keys)
    for k in saved_cats.keys():
        if k not in ordered_keys:
            ordered_keys.append(k)

    key_to_label = {c["key"]: c["label"] for c in type_default_categories}
    # Legacy labels for any keys no longer in the registry for this type
    legacy_labels = {"food": "Food", "staff": "Staff", "service": "Service", "ambiance": "Ambiance"}

    category_rows = [
        (
            k,
            key_to_label.get(k, legacy_labels.get(k, k.replace("_", " ").title())),
            bool(saved_cats.get(k, k in type_keys)),
        )
        for k in ordered_keys
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
            "category_rows": category_rows,
            "menu_items": settings_obj.menu_items or [],
            "custom_keywords": settings_obj.custom_keywords or [],
            "blocked_phrases": settings_obj.blocked_phrases or [],
            "threshold_options": [1, 2, 3],
            "pro_allowed": pro_allowed,
            "preview": preview,
        },
    )
