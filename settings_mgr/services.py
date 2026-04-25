"""Effective-settings resolver — layers LocationSettings.overrides on BusinessSettings."""

from dataclasses import dataclass, field

from businesses.models import Business, Location
from .models import BusinessCategory, BusinessSettings, LocationSettings


OVERRIDABLE_FIELDS = (
    "language_mode",
    "tone_mode",
    "allow_customer_language_change",
    "review_length",
    "mention_business_name",
    "negative_filter_threshold",
    "custom_keywords",
    "blocked_phrases",
    "menu_items",
)


@dataclass
class EnabledCategory:
    key: str
    label: str
    parent_key: str | None = None
    parent_label: str | None = None

    @property
    def display_label(self) -> str:
        if self.parent_label:
            return f"{self.parent_label} › {self.label}"
        return self.label


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
    enabled_categories: list[EnabledCategory] = field(default_factory=list)
    menu_items: list = field(default_factory=list)

    def enabled_category_keys(self) -> list[str]:
        return [c.key for c in self.enabled_categories]

    def enabled_category_labels(self) -> list[str]:
        return [c.display_label for c in self.enabled_categories]

    def label_for_key(self, key: str) -> str | None:
        for c in self.enabled_categories:
            if c.key == key:
                return c.display_label
        return None


def get_enabled_categories(business: Business) -> list[EnabledCategory]:
    """Flat list of every enabled category row for a business, parents and children alike.

    Children whose parent is disabled are also excluded — disabling a parent
    cascades visibility-wise.
    """
    rows = (
        BusinessCategory.objects
        .filter(business=business)
        .select_related("parent")
        .order_by("sort_order", "label")
    )
    enabled: list[EnabledCategory] = []
    enabled_parent_ids: set[int] = set()
    for row in rows:
        if row.parent_id is None and row.is_enabled:
            enabled_parent_ids.add(row.id)
    for row in rows:
        if not row.is_enabled:
            continue
        if row.parent_id is None:
            enabled.append(EnabledCategory(key=row.key, label=row.label))
        elif row.parent_id in enabled_parent_ids:
            enabled.append(
                EnabledCategory(
                    key=row.key,
                    label=row.label,
                    parent_key=row.parent.key,
                    parent_label=row.parent.label,
                )
            )
    return enabled


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

    return EffectiveSettings(
        language_mode=resolve("language_mode"),
        tone_mode=resolve("tone_mode"),
        allow_customer_language_change=resolve("allow_customer_language_change"),
        review_length=resolve("review_length"),
        mention_business_name=resolve("mention_business_name"),
        negative_filter_threshold=resolve("negative_filter_threshold"),
        custom_keywords=resolve("custom_keywords") or [],
        blocked_phrases=resolve("blocked_phrases") or [],
        enabled_categories=get_enabled_categories(location.business),
        menu_items=resolve("menu_items") or [],
    )
