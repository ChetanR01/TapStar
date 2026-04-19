from django.contrib import admin

from .models import DailyStats, GoogleReviewSnapshot


@admin.register(DailyStats)
class DailyStatsAdmin(admin.ModelAdmin):
    list_display = ("location", "date", "reviews_generated", "reviews_submitted", "negative_redirects", "avg_rating")
    list_filter = ("date",)
    search_fields = ("location__name", "location__business__name")
    readonly_fields = ("date",)


@admin.register(GoogleReviewSnapshot)
class GoogleReviewSnapshotAdmin(admin.ModelAdmin):
    list_display = ("business", "date", "review_count", "created_at")
    list_filter = ("date",)
    search_fields = ("business__name",)
