"""
Stats services for the analytics dashboard.

Two layers:
1. Live compute — used by the dashboard so results are always current (no dependency
   on the nightly cron having run).
2. DailyStats cache — written by the aggregation task for historical scale.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal

from django.db.models import Avg, Count, Q
from django.db.models.functions import TruncDate
from django.utils import timezone

from accounts.models import User
from businesses.models import Location
from feedback.models import PrivateFeedback
from reviews.models import ReviewRequest, ReviewVariant

from .models import DailyStats, GoogleReviewSnapshot


@dataclass
class DashboardData:
    # KPI cards — current month + all-time
    generated_month: int
    submitted_month: int
    negative_month: int
    avg_rating_month: float
    generated_total: int
    submitted_total: int
    negative_total: int

    # Time-series for line chart — last N days
    series_dates: list[str]
    series_submitted: list[int]
    series_generated: list[int]

    # Breakdown charts — last N days
    language_labels: list[str]
    language_counts: list[int]
    category_labels: list[str]
    category_counts: list[int]

    # Google snapshot widget
    google_baseline: int | None
    google_current: int | None
    google_delta: int | None
    google_baseline_date: date | None
    google_current_date: date | None


def _month_start(now: datetime) -> datetime:
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def get_dashboard_data(user: User, days: int = 30) -> DashboardData:
    """Compute the whole dashboard payload for a user's businesses, live from the raw tables."""
    now = timezone.now()
    month_start = _month_start(now)
    window_start = (now - timedelta(days=days)).replace(hour=0, minute=0, second=0, microsecond=0)

    loc_q = Q(location__business__owner=user)
    variant_loc_q = Q(request__location__business__owner=user)

    # ------ KPI cards ------
    generated_total = ReviewRequest.objects.filter(loc_q).count()
    submitted_total = ReviewVariant.objects.filter(variant_loc_q, was_submitted=True).count()
    negative_total = PrivateFeedback.objects.filter(loc_q).count()

    generated_month = ReviewRequest.objects.filter(loc_q, created_at__gte=month_start).count()
    submitted_month = ReviewVariant.objects.filter(
        variant_loc_q, was_submitted=True, created_at__gte=month_start
    ).count()
    negative_month = PrivateFeedback.objects.filter(loc_q, created_at__gte=month_start).count()

    avg_month = ReviewRequest.objects.filter(loc_q, created_at__gte=month_start).aggregate(
        avg=Avg("star_rating")
    )["avg"] or 0.0

    # ------ Time series (last N days) ------
    generated_by_day = dict(
        ReviewRequest.objects.filter(loc_q, created_at__gte=window_start)
        .annotate(d=TruncDate("created_at"))
        .values_list("d")
        .annotate(c=Count("id"))
        .values_list("d", "c")
    )
    submitted_by_day = dict(
        ReviewVariant.objects.filter(variant_loc_q, was_submitted=True, created_at__gte=window_start)
        .annotate(d=TruncDate("created_at"))
        .values_list("d")
        .annotate(c=Count("id"))
        .values_list("d", "c")
    )

    series_dates: list[str] = []
    series_submitted: list[int] = []
    series_generated: list[int] = []
    today = now.date()
    for i in range(days - 1, -1, -1):
        d = today - timedelta(days=i)
        series_dates.append(d.strftime("%d %b"))
        series_submitted.append(int(submitted_by_day.get(d, 0)))
        series_generated.append(int(generated_by_day.get(d, 0)))

    # ------ Language breakdown (submitted variants in window) ------
    lang_counter: Counter = Counter(
        ReviewVariant.objects.filter(
            variant_loc_q, was_submitted=True, created_at__gte=window_start
        ).values_list("language", flat=True)
    )
    lang_items = lang_counter.most_common()
    language_labels = [l or "unknown" for l, _ in lang_items]
    language_counts = [c for _, c in lang_items]

    # ------ Category breakdown (ReviewRequest.selected_categories in window) ------
    cat_counter: Counter = Counter()
    for cats in ReviewRequest.objects.filter(loc_q, created_at__gte=window_start).values_list(
        "selected_categories", flat=True
    ):
        for c in cats or []:
            cat_counter[c] += 1
    cat_items = cat_counter.most_common()
    category_labels = [c.title() for c, _ in cat_items]
    category_counts = [n for _, n in cat_items]

    # ------ Google snapshot widget ------
    snapshots = list(
        GoogleReviewSnapshot.objects.filter(business__owner=user).order_by("date")
    )
    g_baseline = snapshots[0] if snapshots else None
    g_current = snapshots[-1] if snapshots else None

    google_baseline = g_baseline.review_count if g_baseline else None
    google_current = g_current.review_count if g_current else None
    google_delta = (
        (google_current - google_baseline)
        if (google_baseline is not None and google_current is not None and g_baseline != g_current)
        else (0 if google_baseline is not None and google_current is not None else None)
    )

    return DashboardData(
        generated_month=generated_month,
        submitted_month=submitted_month,
        negative_month=negative_month,
        avg_rating_month=round(float(avg_month), 2),
        generated_total=generated_total,
        submitted_total=submitted_total,
        negative_total=negative_total,
        series_dates=series_dates,
        series_submitted=series_submitted,
        series_generated=series_generated,
        language_labels=language_labels,
        language_counts=language_counts,
        category_labels=category_labels,
        category_counts=category_counts,
        google_baseline=google_baseline,
        google_current=google_current,
        google_delta=google_delta,
        google_baseline_date=g_baseline.date if g_baseline else None,
        google_current_date=g_current.date if g_current else None,
    )


# ----------------------- Daily aggregation (cache layer) -----------------------

def compute_stats_for_day(location: Location, day: date) -> DailyStats:
    """Compute and upsert a DailyStats row for (location, day) from raw tables."""
    day_start = timezone.make_aware(datetime.combine(day, datetime.min.time()))
    day_end = day_start + timedelta(days=1)

    req_qs = ReviewRequest.objects.filter(
        location=location, created_at__gte=day_start, created_at__lt=day_end
    )
    generated = req_qs.count()
    avg_rating = req_qs.aggregate(avg=Avg("star_rating"))["avg"] or 0

    submitted = ReviewVariant.objects.filter(
        request__location=location,
        was_submitted=True,
        created_at__gte=day_start,
        created_at__lt=day_end,
    ).count()

    neg = PrivateFeedback.objects.filter(
        location=location, created_at__gte=day_start, created_at__lt=day_end
    ).count()

    lang_counter: Counter = Counter(
        ReviewVariant.objects.filter(
            request__location=location,
            was_submitted=True,
            created_at__gte=day_start,
            created_at__lt=day_end,
        ).values_list("language", flat=True)
    )

    cat_counter: Counter = Counter()
    for cats in req_qs.values_list("selected_categories", flat=True):
        for c in cats or []:
            cat_counter[c] += 1

    obj, _ = DailyStats.objects.update_or_create(
        location=location,
        date=day,
        defaults={
            "reviews_generated": generated,
            "reviews_submitted": submitted,
            "negative_redirects": neg,
            "avg_rating": Decimal(str(round(float(avg_rating), 2))),
            "language_breakdown": dict(lang_counter),
            "category_breakdown": dict(cat_counter),
        },
    )
    return obj


def aggregate_day(day: date) -> int:
    """Run compute_stats_for_day for every active location for `day`. Returns row count."""
    count = 0
    for location in Location.objects.filter(is_active=True).select_related("business"):
        compute_stats_for_day(location, day)
        count += 1
    return count
