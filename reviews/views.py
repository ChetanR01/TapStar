"""Customer review page + AI generation + submission tracking."""

import json
import logging
import random
from urllib.parse import quote

from django.conf import settings
from django.db import transaction
from django.http import Http404, JsonResponse, HttpResponseBadRequest
from django.shortcuts import render, get_object_or_404
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_POST

from businesses.models import Location
from settings_mgr.services import get_effective_settings

from .ai import GenerationInput, generate_variants
from .models import ReviewRequest, ReviewVariant, ReviewSubmission

logger = logging.getLogger(__name__)


# Languages exposed in the customer UI when business allows switching.
# Native-script labels so Hindi/Marathi speakers can spot their option instantly.
CUSTOMER_LANGUAGE_OPTIONS = [
    {"code": "english", "label": "English"},
    {"code": "hinglish", "label": "Hinglish"},
    {"code": "hinglish_devanagari", "label": "Hinglish (देवनागरी)"},
    {"code": "hindi", "label": "हिंदी"},
    {"code": "marathi", "label": "मराठी"},
    {"code": "minglish", "label": "Marathi-English"},
    {"code": "random", "label": "Surprise me"},
]


def _json_response(success: bool, data=None, error: str | None = None, status: int = 200) -> JsonResponse:
    payload: dict = {"success": success}
    if success:
        payload["data"] = data or {}
    else:
        payload["error"] = error or "Unknown error"
    return JsonResponse(payload, status=status)


def _parse_json_body(request) -> dict:
    try:
        return json.loads(request.body.decode("utf-8") or "{}")
    except (json.JSONDecodeError, UnicodeDecodeError):
        return {}


@ensure_csrf_cookie
def customer_review_page(request, token):
    """Public customer QR landing page. Sets CSRF cookie for subsequent AJAX calls."""
    location = get_object_or_404(Location, qr_code_token=token, is_active=True)
    business = location.business
    if not business.is_active:
        raise Http404()

    effective = get_effective_settings(location)
    enabled_categories = [
        {"key": c.key, "label": c.display_label}
        for c in effective.enabled_categories
    ]

    # Config passed to frontend JS
    page_config = {
        "token": str(location.qr_code_token),
        "businessName": business.name,
        "businessType": business.get_business_type_display(),
        "googleReviewUrl": location.google_review_url or business.google_review_url or "",
        "categories": enabled_categories,
        "menuItems": effective.menu_items,
        "allowLanguageChange": effective.allow_customer_language_change,
        "defaultLanguage": effective.language_mode,
        "languageOptions": CUSTOMER_LANGUAGE_OPTIONS,
        "negativeThreshold": effective.negative_filter_threshold,
        "apiUrls": {
            "generate": "/api/generate-review/",
            "submit": "/api/submit-review/",
            "feedback": "/api/submit-feedback/",
        },
    }

    return render(
        request,
        "reviews/customer_page.html",
        {
            "business": business,
            "location": location,
            "page_config_json": json.dumps(page_config),
        },
    )


@require_POST
def generate_review_api(request):
    """Generate 4 AI review variants for a QR scan session."""
    body = _parse_json_body(request)
    token = body.get("token")
    if not token:
        return _json_response(False, error="Missing token", status=400)

    try:
        location = Location.objects.select_related("business").get(qr_code_token=token, is_active=True)
    except Location.DoesNotExist:
        return _json_response(False, error="Invalid QR token", status=404)

    if not location.business.is_active:
        return _json_response(False, error="Business unavailable", status=404)

    try:
        star_rating = int(body.get("star_rating", 0))
    except (TypeError, ValueError):
        return _json_response(False, error="Invalid star_rating", status=400)
    if star_rating < 1 or star_rating > 5:
        return _json_response(False, error="star_rating must be 1-5", status=400)

    raw_categories = [str(c) for c in body.get("categories") or []]
    raw_items = [str(i) for i in body.get("items") or []]
    requested_language = str(body.get("language") or "").lower().strip()

    effective = get_effective_settings(location)

    # Allow customer to override language only if permitted
    language_mode = effective.language_mode
    if effective.allow_customer_language_change and requested_language:
        valid = {opt["code"] for opt in CUSTOMER_LANGUAGE_OPTIONS}
        if requested_language in valid:
            language_mode = requested_language

    tone_mode = effective.tone_mode

    # Disabled categories must never reach the prompt. Pull the labels straight
    # off the resolver — it already filters out disabled rows.
    enabled_labels_by_key = {c.key: c.display_label for c in effective.enabled_categories}
    enabled_label_list = list(enabled_labels_by_key.values())

    # Customer-submitted categories: keep only those the owner has enabled.
    sanitized_categories = [
        enabled_labels_by_key[c] for c in raw_categories if c in enabled_labels_by_key
    ]

    # If the customer didn't pick a category, randomly pick ONE enabled category
    # to anchor the variants on, so the AI cannot drift to an off-list topic.
    if sanitized_categories:
        focus_categories = sanitized_categories
    elif enabled_label_list:
        focus_categories = [random.choice(enabled_label_list)]
    else:
        focus_categories = []

    # Items: only allow items the owner configured for this business. Anything
    # else is rejected so the model never names an item that wasn't explicitly
    # selected.
    allowed_items = {str(i).strip().lower(): str(i).strip() for i in (effective.menu_items or [])}
    sanitized_items = [
        allowed_items[i.strip().lower()] for i in raw_items if i.strip().lower() in allowed_items
    ]

    gen_input = GenerationInput(
        business=location.business,
        location_name=location.name,
        star_rating=star_rating,
        categories=sanitized_categories,
        items=sanitized_items,
        language_mode=language_mode,
        tone_mode=tone_mode,
        enabled_category_labels=enabled_label_list,
        focus_categories=focus_categories,
    )

    with transaction.atomic():
        review_request = ReviewRequest.objects.create(
            location=location,
            star_rating=star_rating,
            selected_categories=sanitized_categories,
            selected_items=sanitized_items,
            language_mode_used=language_mode,
            tone_mode_used=tone_mode,
            is_negative=star_rating <= effective.negative_filter_threshold,
        )

        variants, used_fallback = generate_variants(gen_input, effective)

        variant_objs = [
            ReviewVariant.objects.create(
                request=review_request,
                variant_number=v["variant_number"],
                language=v["language"],
                tone=v["tone"],
                text=v["text"],
            )
            for v in variants
        ]

    return _json_response(
        True,
        data={
            "request_id": review_request.pk,
            "session_token": str(review_request.session_token),
            "used_fallback": used_fallback,
            "variants": [
                {
                    "id": vo.pk,
                    "variant_number": vo.variant_number,
                    "language": vo.language,
                    "tone": vo.tone,
                    "text": vo.text,
                }
                for vo in variant_objs
            ],
        },
    )


@require_POST
def submit_review_api(request):
    """Mark the selected variant as submitted and return the Google review URL (text prefill attempted)."""
    body = _parse_json_body(request)
    variant_id = body.get("variant_id")
    session_token = body.get("session_token")
    final_text = str(body.get("text") or "").strip()

    if not variant_id or not session_token:
        return _json_response(False, error="Missing variant_id or session_token", status=400)

    try:
        variant = ReviewVariant.objects.select_related("request__location__business").get(pk=variant_id)
    except ReviewVariant.DoesNotExist:
        return _json_response(False, error="Variant not found", status=404)

    if str(variant.request.session_token) != str(session_token):
        return _json_response(False, error="Session mismatch", status=403)

    with transaction.atomic():
        if final_text and final_text != variant.text:
            variant.text = final_text
        variant.was_selected = True
        variant.was_submitted = True
        variant.save(update_fields=["text", "was_selected", "was_submitted"])

        ReviewSubmission.objects.get_or_create(
            variant=variant,
            defaults={"user_agent": request.META.get("HTTP_USER_AGENT", "")[:500]},
        )

    location = variant.request.location
    base_review_url = location.google_review_url or location.business.google_review_url
    # Best-effort prefill — Google does not officially support the review.content param,
    # so the frontend always copies the text to the clipboard as a fallback.
    prefilled_url = ""
    if base_review_url:
        prefilled_url = f"{base_review_url}&review.content={quote(variant.text)}"

    return _json_response(
        True,
        data={
            "google_review_url": base_review_url or "",
            "prefilled_url": prefilled_url,
            "text": variant.text,
        },
    )
