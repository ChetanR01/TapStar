from django.contrib import admin

from .models import PrivateFeedback


@admin.register(PrivateFeedback)
class PrivateFeedbackAdmin(admin.ModelAdmin):
    list_display = ("id", "location", "star_rating", "customer_name", "customer_phone", "is_read", "created_at")
    list_filter = ("is_read", "star_rating", "created_at")
    search_fields = ("feedback_text", "customer_name", "customer_phone", "location__business__name")
    readonly_fields = ("created_at",)
    actions = ["mark_as_read", "mark_as_unread"]

    @admin.action(description="Mark selected as read")
    def mark_as_read(self, request, queryset):
        queryset.update(is_read=True)

    @admin.action(description="Mark selected as unread")
    def mark_as_unread(self, request, queryset):
        queryset.update(is_read=False)
