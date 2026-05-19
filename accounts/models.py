from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from datetime import timedelta


# Feature tier codes — used by the gating layer to decide which features a
# user can access. A "starter" tier is the free fallback, "growth" unlocks
# the full single-location toolkit, "business" adds multi-location.
# These are tier labels, not billing options — billing options live in the
# PricingPlan table, where each row carries a `tier` field.
TIER_STARTER = "starter"
TIER_GROWTH = "growth"
TIER_BUSINESS = "business"
TIER_CHOICES = [
    (TIER_STARTER, "Starter"),
    (TIER_GROWTH, "Growth"),
    (TIER_BUSINESS, "Business"),
]


class User(AbstractUser):
    """Custom user with subscription fields. Uses email as the primary identifier."""

    # Kept for backwards-compatibility with code that imports User.PLAN_STARTER /
    # User.PLAN_GROWTH / User.PLAN_BUSINESS. They now refer to FEATURE TIERS, not
    # billing options. Billing options (monthly, half-yearly, yearly, ...) are
    # rows in PricingPlan, each carrying a `tier` field.
    PLAN_STARTER = TIER_STARTER
    PLAN_GROWTH = TIER_GROWTH
    PLAN_BUSINESS = TIER_BUSINESS

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
    # Holds a PricingPlan.code. Free string — choices live in the DB so the
    # admin can add new billing options without a migration.
    subscription_plan = models.CharField(max_length=32, default=TIER_STARTER)
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

    @property
    def feature_tier(self) -> str:
        """Tier label for feature gating. Trial users get the Growth tier."""
        if self.is_trialing:
            return TIER_GROWTH
        if not self.has_active_subscription:
            return TIER_STARTER
        plan = PricingPlan.objects.filter(code=self.subscription_plan).first()
        return plan.tier if plan else TIER_STARTER

    @property
    def has_paid_features(self) -> bool:
        """True if user can access Growth/Business-tier features."""
        return self.feature_tier in (TIER_GROWTH, TIER_BUSINESS)


class PricingPlan(models.Model):
    """A billing option shown on the upgrade page — fully configurable from the Django admin.

    The owner can add new options ("3-month plan", "lifetime", ...) without a
    code change. Each row maps to a feature `tier` (starter/growth/business)
    so existing feature gating keeps working.
    """

    code = models.CharField(
        max_length=32,
        unique=True,
        help_text="Stable slug used in URLs and stored on User.subscription_plan. Don't change after launch.",
    )
    name = models.CharField(max_length=50, help_text="Public display name. e.g. '1 Month', '6 Months', '1 Year'.")
    tagline = models.CharField(max_length=120, blank=True, help_text="Optional one-liner under the name.")
    tier = models.CharField(
        max_length=20,
        choices=TIER_CHOICES,
        default=TIER_GROWTH,
        help_text="Which feature bucket this plan unlocks. Multiple paid plans can share the same tier.",
    )

    billing_period_days = models.IntegerField(
        default=30,
        help_text="How many days a successful payment extends the subscription. 0 for free plans.",
    )
    price_paise = models.IntegerField(
        default=0,
        help_text="Current/discounted price in paise. 0 = free.",
    )
    original_price_paise = models.IntegerField(
        default=0,
        help_text="Original price (struck-through). 0 or equal to price_paise hides the strike-through.",
    )

    features = models.JSONField(
        default=list,
        blank=True,
        help_text='List of feature strings, e.g. ["Unlimited reviews", "1 location"].',
    )
    not_included = models.JSONField(
        default=list,
        blank=True,
        help_text="Optional list of features explicitly NOT included.",
    )

    review_limit = models.IntegerField(
        null=True,
        blank=True,
        help_text="Max review generations per month. Leave blank for unlimited.",
    )
    location_limit = models.IntegerField(
        default=1,
        help_text="Max number of business locations this plan allows.",
    )

    highlighted = models.BooleanField(default=False, help_text="Show 'Most popular' badge.")
    is_active = models.BooleanField(default=True, help_text="Untick to hide from the upgrade page.")
    sort_order = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "billing_period_days", "price_paise"]

    def __str__(self):
        return f"{self.name} ({self.code})"

    @property
    def is_free(self) -> bool:
        return self.price_paise <= 0

    @property
    def price_rupees(self) -> str:
        return f"{self.price_paise / 100:.0f}"

    @property
    def original_price_rupees(self) -> str:
        return f"{self.original_price_paise / 100:.0f}"

    @property
    def has_discount(self) -> bool:
        return self.original_price_paise > self.price_paise and self.price_paise > 0

    @property
    def discount_percent(self) -> int:
        if not self.has_discount:
            return 0
        return round((self.original_price_paise - self.price_paise) * 100 / self.original_price_paise)

    @property
    def period_label(self) -> str:
        days = self.billing_period_days
        if days <= 0:
            return "forever"
        if days % 365 == 0 and days >= 365:
            years = days // 365
            return "/ year" if years == 1 else f"/ {years} years"
        if days % 30 == 0:
            months = days // 30
            return "/ month" if months == 1 else f"for {months} months"
        return f"for {days} days"


class SubscriptionPayment(models.Model):
    """One Easebuzz payment for a plan cycle. Each successful payment extends user.subscription_active_until by the plan's billing_period_days."""

    STATUS_PENDING = "pending"
    STATUS_SUCCESS = "success"
    STATUS_FAILED = "failed"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_SUCCESS, "Success"),
        (STATUS_FAILED, "Failed"),
    ]

    user = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="payments")
    plan = models.CharField(max_length=32, help_text="PricingPlan.code at the time of payment.")
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
