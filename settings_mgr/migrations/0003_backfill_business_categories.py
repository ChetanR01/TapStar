"""Data migration: seed BusinessCategory rows for every existing business.

For each business, walks the type registry's default categories and creates
one row per default. Each row's is_enabled is taken from BusinessSettings.
categories_enabled when present, else True. Custom keys present in the JSON
that aren't in the registry are also imported so nothing the owner already
toggled gets lost.
"""

from django.db import migrations


def _registry():
    # Local import — registry lives in the reviews app and is safe to read at
    # migration time because it has no Django dependencies.
    from reviews.business_types import TYPE_REGISTRY
    return TYPE_REGISTRY


def backfill(apps, schema_editor):
    Business = apps.get_model("businesses", "Business")
    BusinessSettings = apps.get_model("settings_mgr", "BusinessSettings")
    BusinessCategory = apps.get_model("settings_mgr", "BusinessCategory")

    registry = _registry()

    for business in Business.objects.all():
        if BusinessCategory.objects.filter(business=business, parent__isnull=True).exists():
            continue

        try:
            bs = BusinessSettings.objects.get(business=business)
        except BusinessSettings.DoesNotExist:
            bs = None

        enabled_map = (bs.categories_enabled if bs else None) or {}

        type_entry = registry.get(business.business_type) or registry["other"]
        defaults = type_entry["default_categories"]

        seen_keys: set[str] = set()
        for index, cat in enumerate(defaults):
            key = cat["key"]
            label = cat["label"]
            BusinessCategory.objects.create(
                business=business,
                parent=None,
                key=key,
                label=label,
                is_enabled=bool(enabled_map.get(key, True)),
                sort_order=index * 10,
            )
            seen_keys.add(key)

        # Carry over any owner-customised keys that aren't in the registry
        for extra_index, (key, value) in enumerate(enabled_map.items()):
            if key in seen_keys:
                continue
            BusinessCategory.objects.create(
                business=business,
                parent=None,
                key=key,
                label=key.replace("_", " ").title(),
                is_enabled=bool(value),
                sort_order=(len(defaults) + extra_index) * 10,
            )


def noop_reverse(apps, schema_editor):
    BusinessCategory = apps.get_model("settings_mgr", "BusinessCategory")
    BusinessCategory.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ("settings_mgr", "0002_alter_businesssettings_language_mode_and_more"),
    ]

    operations = [
        migrations.RunPython(backfill, noop_reverse),
    ]
