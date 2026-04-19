from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from datetime import timedelta


class User(AbstractUser):
    """Custom user with subscription fields. Uses email as the primary identifier."""

    PLAN_STARTER = "starter"
    PLAN_GROWTH = "growth"
    PLAN_BUSINESS = "business"
    PLAN_CHOICES = [
        (PLAN_STARTER, "Starter"),
        (PLAN_GROWTH, "Growth"),
        (PLAN_BUSINESS, "Business"),
    ]

    STATUS_TRIAL = "trial"
    STATUS_ACTIVE = "active"
    STATUS_EXPIRED = "expired"
    STATUS_CANCELLED = "cancelled"
    STATUS_CHOICES = [
        (STATUS_TRIAL, "Trial"),
        (STATUS_ACTIVE, "Active"),
        (STATUS_EXPIRED, "Expired"),
        (STATUS_CANCELLED, "Cancelled"),
    ]

    email = models.EmailField(unique=True)
    subscription_plan = models.CharField(max_length=20, choices=PLAN_CHOICES, default=PLAN_STARTER)
    subscription_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_TRIAL)
    trial_ends_at = models.DateTimeField(null=True, blank=True)
    subscription_active_until = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    def __str__(self):
        return self.email

    def save(self, *args, **kwargs):
        if not self.trial_ends_at and self.subscription_status == self.STATUS_TRIAL:
            self.trial_ends_at = timezone.now() + timedelta(days=30)
        super().save(*args, **kwargs)

    @property
    def is_trialing(self) -> bool:
        return (
            self.subscription_status == self.STATUS_TRIAL
            and self.trial_ends_at is not None
            and self.trial_ends_at > timezone.now()
        )

    @property
    def has_active_subscription(self) -> bool:
        if self.is_trialing:
            return True
        if self.subscription_status != self.STATUS_ACTIVE:
            return False
        if self.subscription_active_until is None:
            return False
        return self.subscription_active_until > timezone.now()

    @property
    def subscription_days_remaining(self) -> int | None:
        target = self.subscription_active_until or self.trial_ends_at
        if not target:
            return None
        delta = target - timezone.now()
        return max(0, delta.days)


class SubscriptionPayment(models.Model):
    """One Easebuzz payment for a plan cycle. Each successful payment extends user.subscription_active_until by 30 days."""

    STATUS_PENDING = "pending"
    STATUS_SUCCESS = "success"
    STATUS_FAILED = "failed"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_SUCCESS, "Success"),
        (STATUS_FAILED, "Failed"),
    ]

    user = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="payments")
    plan = models.CharField(max_length=20, choices=User.PLAN_CHOICES)
    amount_paise = models.IntegerField()

    # Our internal transaction id sent to Easebuzz as `txnid`
    easebuzz_txnid = models.CharField(max_length=64, unique=True)
    # Easebuzz's transaction id — populated on callback
    easebuzz_payment_id = models.CharField(max_length=128, blank=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    error_message = models.TextField(blank=True)

    raw_response = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["user", "-created_at"])]

    def __str__(self):
        return f"{self.easebuzz_txnid} — {self.user.email} — {self.plan} ({self.status})"
