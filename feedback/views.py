"""Private feedback: customer submit API + business-side inbox + mark-read."""

import json
import logging

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import JsonResponse, HttpResponse, HttpResponseForbidden
from django.shortcuts import render, get_object_or_404
from django.views.decorators.http import require_POST

from businesses.models import Location

from .models import PrivateFeedback

logger = logging.getLogger(__name__)


# ------------------ Customer-side API (existing) ------------------

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


@require_POST
def submit_feedback_api(request):
    body = _parse_json_body(request)
    token = body.get("token")
    if not token:
        return _json_response(False, error="Missing token", status=400)

    try:
        location = Location.objects.select_related("business").get(qr_code_token=token, is_active=True)
    except Location.DoesNotExist:
        return _json_response(False, error="Invalid QR token", status=404)

    try:
        star_rating = int(body.get("star_rating", 0))
    except (TypeError, ValueError):
        return _json_response(False, error="Invalid star_rating", status=400)
    if star_rating < 1 or star_rating > 5:
        return _json_response(False, error="star_rating must be 1-5", status=400)

    feedback_text = str(body.get("feedback_text") or "").strip()
    if not feedback_text:
        return _json_response(False, error="Feedback text is required", status=400)

    customer_name = str(body.get("customer_name") or "").strip()[:200]
    customer_phone = str(body.get("customer_phone") or "").strip()[:30]

    fb = PrivateFeedback.objects.create(
        location=location,
        star_rating=star_rating,
        feedback_text=feedback_text,
        customer_name=customer_name,
        customer_phone=customer_phone,
    )

    return _json_response(True, data={"id": fb.pk})


# ------------------ Business-side inbox ------------------

def _user_feedback_qs(user):
    return (
        PrivateFeedback.objects
        .filter(location__business__owner=user)
        .select_related("location", "location__business")
    )


@login_required
def feedback_inbox(request):
    filter_mode = request.GET.get("filter", "all")
    qs = _user_feedback_qs(request.user)
    if filter_mode == "unread":
        qs = qs.filter(is_read=False)

    paginator = Paginator(qs, 25)
    page_obj = paginator.get_page(request.GET.get("page"))

    unread_total = _user_feedback_qs(request.user).filter(is_read=False).count()
    total = _user_feedback_qs(request.user).count()

    return render(
        request,
        "feedback/inbox.html",
        {
            "page_obj": page_obj,
            "filter_mode": filter_mode,
            "unread_total": unread_total,
            "total": total,
        },
    )


def _toggle_read(request, feedback_id: int, mark_read: bool) -> HttpResponse:
    fb = get_object_or_404(
        _user_feedback_qs(request.user),
        pk=feedback_id,
    )
    if fb.is_read != mark_read:
        fb.is_read = mark_read
        fb.save(update_fields=["is_read"])

    if request.htmx:
        return render(request, "feedback/_feedback_row.html", {"fb": fb})
    return HttpResponse(status=204)


@login_required
@require_POST
def mark_read(request, feedback_id: int):
    return _toggle_read(request, feedback_id, True)


@login_required
@require_POST
def mark_unread(request, feedback_id: int):
    return _toggle_read(request, feedback_id, False)
