from django.contrib import admin

from .models import ReviewRequest, ReviewVariant, ReviewSubmission


class ReviewVariantInline(admin.TabularInline):
    model = ReviewVariant
    extra = 0
    readonly_fields = ("variant_number", "language", "tone", "text", "was_selected", "was_submitted", "created_at")
    can_delete = False


@admin.register(ReviewRequest)
class ReviewRequestAdmin(admin.ModelAdmin):
    list_display = ("id", "location", "star_rating", "is_negative", "language_mode_used", "tone_mode_used", "created_at")
    list_filter = ("is_negative", "star_rating", "language_mode_used", "created_at")
    search_fields = ("location__name", "location__business__name")
    readonly_fields = ("session_token", "created_at")
    inlines = [ReviewVariantInline]


@admin.register(ReviewVariant)
class ReviewVariantAdmin(admin.ModelAdmin):
    list_display = ("id", "request", "variant_number", "language", "tone", "was_selected", "was_submitted")
    list_filter = ("language", "tone", "was_selected", "was_submitted")


@admin.register(ReviewSubmission)
class ReviewSubmissionAdmin(admin.ModelAdmin):
    list_display = ("id", "variant", "submitted_at")
    readonly_fields = ("variant", "submitted_at", "user_agent")
