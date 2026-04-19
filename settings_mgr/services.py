"""Effective-settings resolver — layers LocationSettings.overrides on BusinessSettings."""

from dataclasses import dataclass, field

from businesses.models import Location
from .models import BusinessSettings, LocationSettings, DEFAULT_CATEGORIES


OVERRIDABLE_FIELDS = (
    "language_mode",
    "tone_mode",
    "allow_customer_language_change",
    "review_length",
    "mention_business_name",
    "negative_filter_threshold",
    "custom_keywords",
    "blocked_phrases",
    "categories_enabled",
    "menu_items",
)


@dataclass
class EffectiveSettings:
    language_mode: str
    tone_mode: str
    allow_customer_language_change: bool
    review_length: str
    mention_business_name: bool
    negative_filter_threshold: int
    custom_keywords: list = field(default_factory=list)
    blocked_phrases: list = field(default_factory=list)
    categories_enabled: dict = field(default_factory=dict)
    menu_items: list = field(default_factory=list)

    def enabled_category_keys(self) -> list[str]:
        return [k for k, v in self.categories_enabled.items() if v]


def get_effective_settings(location: Location) -> EffectiveSettings:
    """Resolve merged settings for a location — business-level values with per-location overrides applied."""
    bs, _ = BusinessSettings.objects.get_or_create(business=location.business)

    overrides: dict = {}
    try:
        ls = location.settings_override
        overrides = ls.overrides or {}
    except LocationSettings.DoesNotExist:
        pass

    def resolve(field_name: str):
        if field_name in overrides:
            return overrides[field_name]
        return getattr(bs, field_name)

    categories = resolve("categories_enabled") or dict(DEFAULT_CATEGORIES)

    return EffectiveSettings(
        language_mode=resolve("language_mode"),
        tone_mode=resolve("tone_mode"),
        allow_customer_language_change=resolve("allow_customer_language_change"),
        review_length=resolve("review_length"),
        mention_business_name=resolve("mention_business_name"),
        negative_filter_threshold=resolve("negative_filter_threshold"),
        custom_keywords=resolve("custom_keywords") or [],
        blocked_phrases=resolve("blocked_phrases") or [],
        categories_enabled=categories,
        menu_items=resolve("menu_items") or [],
    )
