"""Settings management view — language/tone/categories/menu/keywords/blocked phrases."""

import random

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from accounts.models import User
from reviews.fallback import build_fallback_variants

from .models import (
    BusinessSettings,
    DEFAULT_CATEGORIES,
    LANGUAGE_CHOICES,
    TONE_CHOICES,
    LENGTH_CHOICES,
)


CATEGORY_CHOICES = [
    ("food", "Food"),
    ("staff", "Staff"),
    ("service", "Service"),
    ("ambiance", "Ambiance"),
]


def _plan_allows_pro(user) -> bool:
    """Custom keywords, blocked phrases, and negative filter are Growth+ features."""
    if not user.is_authenticated:
        return False
    return user.has_active_subscription and user.subscription_plan in (User.PLAN_GROWTH, User.PLAN_BUSINESS)


def _plan_language_options(user):
    """Starter: English + Hinglish only. Growth/Business: all 6 modes."""
    if _plan_allows_pro(user):
        return LANGUAGE_CHOICES
    allowed = {"english", "hinglish"}
    return [(code, label) for code, label in LANGUAGE_CHOICES if code in allowed]


def _build_sample_preview(settings_obj: BusinessSettings, business_name: str) -> str:
    variants = build_fallback_variants(settings_obj.language_mode, business_name)
    return random.choice(variants)["text"] if variants else ""


@login_required
@require_http_methods(["GET", "POST"])
def settings_page(request):
    business = request.user.businesses.first()
    if not business:
        return redirect("business_onboarding")

    settings_obj, _ = BusinessSettings.objects.get_or_create(business=business)
    pro_allowed = _plan_allows_pro(request.user)
    language_options = _plan_language_options(request.user)

    if request.method == "POST":
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

        cats = {}
        for key, _label in CATEGORY_CHOICES:
            cats[key] = bool(request.POST.get(f"category_{key}"))
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

    category_rows = [
        (key, label, bool((settings_obj.categories_enabled or DEFAULT_CATEGORIES).get(key, True)))
        for key, label in CATEGORY_CHOICES
    ]

    return render(
        request,
        "settings/index.html",
        {
            "business": business,
            "settings_obj": settings_obj,
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
