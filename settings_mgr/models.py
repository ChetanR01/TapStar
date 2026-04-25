from django.db import models

from businesses.models import Business, Location


LANGUAGE_HINGLISH = "hinglish"
LANGUAGE_HINGLISH_DEV = "hinglish_devanagari"
LANGUAGE_MINGLISH = "minglish"
LANGUAGE_HINDI = "hindi"
LANGUAGE_MARATHI = "marathi"
LANGUAGE_ENGLISH = "english"
LANGUAGE_RANDOM = "random"
LANGUAGE_CHOICES = [
    (LANGUAGE_ENGLISH, "English"),
    (LANGUAGE_HINGLISH, "Hinglish (Roman script)"),
    (LANGUAGE_HINGLISH_DEV, "Hinglish (देवनागरी script)"),
    (LANGUAGE_HINDI, "Hindi (हिंदी)"),
    (LANGUAGE_MARATHI, "Marathi (मराठी)"),
    (LANGUAGE_MINGLISH, "Minglish (Marathi + English)"),
    (LANGUAGE_RANDOM, "Random mix"),
]

TONE_CASUAL = "casual"
TONE_FORMAL = "formal"
TONE_ENTHUSIASTIC = "enthusiastic"
TONE_RANDOM = "random"
TONE_CHOICES = [
    (TONE_CASUAL, "Casual"),
    (TONE_FORMAL, "Formal"),
    (TONE_ENTHUSIASTIC, "Enthusiastic"),
    (TONE_RANDOM, "Random mix"),
]

LENGTH_SHORT = "short"
LENGTH_MEDIUM = "medium"
LENGTH_DETAILED = "detailed"
LENGTH_CHOICES = [
    (LENGTH_SHORT, "Short (1-2 sentences)"),
    (LENGTH_MEDIUM, "Medium (3-4 sentences)"),
    (LENGTH_DETAILED, "Detailed (5-7 sentences)"),
]


class BusinessSettings(models.Model):
    business = models.OneToOneField(Business, on_delete=models.CASCADE, related_name="review_settings")

    language_mode = models.CharField(max_length=20, choices=LANGUAGE_CHOICES, default=LANGUAGE_RANDOM)
    tone_mode = models.CharField(max_length=20, choices=TONE_CHOICES, default=TONE_RANDOM)
    allow_customer_language_change = models.BooleanField(default=True)
    review_length = models.CharField(max_length=20, choices=LENGTH_CHOICES, default=LENGTH_MEDIUM)
    mention_business_name = models.BooleanField(default=True)

    negative_filter_threshold = models.IntegerField(default=2)

    custom_keywords = models.JSONField(default=list, blank=True)
    blocked_phrases = models.JSONField(default=list, blank=True)
    menu_items = models.JSONField(default=list, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Business settings"

    def __str__(self):
        return f"Settings for {self.business.name}"


class BusinessCategory(models.Model):
    """Per-business review category. Replaces the old categories_enabled JSON.

    A category may have a parent — top-level entries are categories, children
    are subcategories. The customer review page renders all enabled rows as
    chips; the AI prompt restricts itself to enabled rows. Disabled rows are
    hidden from customers and the model entirely.
    """

    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name="categories")
    parent = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.CASCADE, related_name="subcategories"
    )
    key = models.CharField(max_length=80)
    label = models.CharField(max_length=120)
    is_enabled = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "label"]
        constraints = [
            models.UniqueConstraint(
                fields=["business", "parent", "key"], name="uniq_category_per_business"
            )
        ]
        verbose_name = "Business category"
        verbose_name_plural = "Business categories"

    def __str__(self):
        prefix = f"{self.parent.label} › " if self.parent_id else ""
        return f"{self.business.name}: {prefix}{self.label}"


class LocationSettings(models.Model):
    """Per-location overrides — only stores fields that differ from business-level."""

    location = models.OneToOneField(Location, on_delete=models.CASCADE, related_name="settings_override")
    overrides = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Location settings"

    def __str__(self):
        return f"Overrides for {self.location}"
