from django.contrib import admin

from .models import BusinessSettings, LocationSettings


@admin.register(BusinessSettings)
class BusinessSettingsAdmin(admin.ModelAdmin):
    list_display = ("business", "language_mode", "tone_mode", "review_length", "negative_filter_threshold")
    list_filter = ("language_mode", "tone_mode", "review_length")
    search_fields = ("business__name",)


@admin.register(LocationSettings)
class LocationSettingsAdmin(admin.ModelAdmin):
    list_display = ("location", "updated_at")
    search_fields = ("location__name", "location__business__name")
