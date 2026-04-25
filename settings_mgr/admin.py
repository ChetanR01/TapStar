from django.contrib import admin

from .models import BusinessCategory, BusinessSettings, LocationSettings


@admin.register(BusinessSettings)
class BusinessSettingsAdmin(admin.ModelAdmin):
    list_display = ("business", "language_mode", "tone_mode", "review_length", "negative_filter_threshold")
    list_filter = ("language_mode", "tone_mode", "review_length")
    search_fields = ("business__name",)


@admin.register(BusinessCategory)
class BusinessCategoryAdmin(admin.ModelAdmin):
    list_display = ("business", "label", "key", "parent", "is_enabled", "sort_order")
    list_filter = ("is_enabled", "business")
    list_editable = ("is_enabled", "sort_order")
    search_fields = ("business__name", "label", "key")
    autocomplete_fields = ("business", "parent")


@admin.register(LocationSettings)
class LocationSettingsAdmin(admin.ModelAdmin):
    list_display = ("location", "updated_at")
    search_fields = ("location__name", "location__business__name")
