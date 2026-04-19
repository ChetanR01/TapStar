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

DEFAULT_CATEGORIES = {"food": True, "staff": True, "service": True, "ambiance": True}


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
    categories_enabled = models.JSONField(default=dict, blank=True)
    menu_items = models.JSONField(default=list, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Business settings"

    def __str__(self):
        return f"Settings for {self.business.name}"

    def save(self, *args, **kwargs):
        if not self.categories_enabled:
            self.categories_enabled = dict(DEFAULT_CATEGORIES)
        super().save(*args, **kwargs)


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
