from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import PricingPlan, SubscriptionPayment, User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    list_display = ("email", "username", "subscription_plan", "subscription_status", "subscription_active_until", "trial_ends_at", "is_staff")
    list_filter = ("subscription_plan", "subscription_status", "is_staff", "is_superuser")
    search_fields = ("email", "username", "first_name", "last_name")
    ordering = ("-date_joined",)

    fieldsets = DjangoUserAdmin.fieldsets + (
        ("Subscription", {
            "fields": (
                "subscription_plan",
                "subscription_status",
                "trial_ends_at",
                "subscription_active_until",
            )
        }),
    )


@admin.register(PricingPlan)
class PricingPlanAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "code",
        "tier",
        "billing_period_days",
        "price_rupees_display",
        "original_price_rupees_display",
        "discount_percent_display",
        "highlighted",
        "is_active",
        "sort_order",
    )
    list_editable = ("highlighted", "is_active", "sort_order")
    list_filter = ("tier", "is_active", "highlighted")
    search_fields = ("code", "name", "tagline")
    fieldsets = (
        (None, {"fields": ("code", "name", "tagline", "tier", "is_active", "highlighted", "sort_order")}),
        ("Pricing (paise — Rs.99 = 9900)", {"fields": ("price_paise", "original_price_paise", "billing_period_days")}),
        ("Limits", {"fields": ("review_limit", "location_limit")}),
        ("Marketing copy (one item per line in JSON)", {"fields": ("features", "not_included")}),
    )

    @admin.display(description="Price", ordering="price_paise")
    def price_rupees_display(self, obj):
        return f"Rs.{obj.price_rupees}" if not obj.is_free else "Free"

    @admin.display(description="Original", ordering="original_price_paise")
    def original_price_rupees_display(self, obj):
        if obj.original_price_paise <= obj.price_paise:
            return "—"
        return f"Rs.{obj.original_price_rupees}"

    @admin.display(description="Discount")
    def discount_percent_display(self, obj):
        return f"{obj.discount_percent}%" if obj.has_discount else "—"


@admin.register(SubscriptionPayment)
class SubscriptionPaymentAdmin(admin.ModelAdmin):
    list_display = ("easebuzz_txnid", "user", "plan", "amount_paise", "status", "created_at")
    list_filter = ("status", "plan", "created_at")
    search_fields = ("easebuzz_txnid", "easebuzz_payment_id", "user__email")
    readonly_fields = ("easebuzz_txnid", "easebuzz_payment_id", "raw_response", "created_at", "updated_at")
