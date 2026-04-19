"""Analytics dashboard (Growth+ gated) and Google-snapshot endpoint."""

import json
from datetime import date

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseBadRequest
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from accounts.gating import require_plan
from accounts.models import User

from .models import GoogleReviewSnapshot
from .services import get_dashboard_data


@login_required
@require_plan(User.PLAN_GROWTH)
def dashboard(request):
    business = request.user.businesses.first()
    if not business:
        return redirect("business_onboarding")

    data = get_dashboard_data(request.user, days=30)

    return render(
        request,
        "analytics/dashboard.html",
        {
            "business": business,
            "data": data,
            "today": timezone.now().date(),
            "chart_payload_json": json.dumps({
                "series_dates": data.series_dates,
                "series_submitted": data.series_submitted,
                "series_generated": data.series_generated,
                "language_labels": data.language_labels,
                "language_counts": data.language_counts,
                "category_labels": data.category_labels,
                "category_counts": data.category_counts,
            }),
        },
    )


@login_required
@require_plan(User.PLAN_GROWTH)
@require_POST
def add_google_snapshot(request):
    business = request.user.businesses.first()
    if not business:
        return HttpResponseBadRequest("No business")

    try:
        count = int((request.POST.get("review_count") or "").strip())
    except (TypeError, ValueError):
        messages.error(request, "Enter a valid number.")
        return redirect("analytics_dashboard")

    if count < 0:
        messages.error(request, "Count must be zero or positive.")
        return redirect("analytics_dashboard")

    snap_date_raw = (request.POST.get("snap_date") or "").strip()
    try:
        snap_date = date.fromisoformat(snap_date_raw) if snap_date_raw else timezone.now().date()
    except ValueError:
        messages.error(request, "Invalid date.")
        return redirect("analytics_dashboard")

    GoogleReviewSnapshot.objects.update_or_create(
        business=business,
        date=snap_date,
        defaults={
            "review_count": count,
            "note": (request.POST.get("note") or "").strip()[:200],
        },
    )
    messages.success(request, "Google review count updated.")
    return redirect("analytics_dashboard")
