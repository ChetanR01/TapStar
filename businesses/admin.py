from django.contrib import admin

from .models import Business, Location


class LocationInline(admin.TabularInline):
    model = Location
    extra = 0
    readonly_fields = ("qr_code_token", "qr_code_image", "created_at")


@admin.register(Business)
class BusinessAdmin(admin.ModelAdmin):
    list_display = ("name", "business_type", "owner", "is_active", "created_at")
    list_filter = ("business_type", "is_active", "created_at")
    search_fields = ("name", "owner__email", "google_place_id")
    readonly_fields = ("created_at", "updated_at", "google_review_url")
    inlines = [LocationInline]


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ("__str__", "business", "qr_code_token", "is_active", "created_at")
    list_filter = ("is_active", "created_at")
    search_fields = ("name", "business__name", "google_place_id")
    readonly_fields = ("qr_code_token", "qr_code_image", "google_review_url", "created_at")
