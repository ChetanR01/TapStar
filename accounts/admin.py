from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import User, SubscriptionPayment


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


@admin.register(SubscriptionPayment)
class SubscriptionPaymentAdmin(admin.ModelAdmin):
    list_display = ("easebuzz_txnid", "user", "plan", "amount_paise", "status", "created_at")
    list_filter = ("status", "plan", "created_at")
    search_fields = ("easebuzz_txnid", "easebuzz_payment_id", "user__email")
    readonly_fields = ("easebuzz_txnid", "easebuzz_payment_id", "raw_response", "created_at", "updated_at")
