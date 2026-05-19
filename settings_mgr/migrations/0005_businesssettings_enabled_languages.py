from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("settings_mgr", "0004_remove_businesssettings_categories_enabled"),
    ]

    operations = [
        migrations.AddField(
            model_name="businesssettings",
            name="enabled_languages",
            field=models.JSONField(
                blank=True,
                default=list,
                help_text=(
                    "List of language codes shown to customers in the review-page language picker. "
                    "Empty = all languages your plan supports."
                ),
            ),
        ),
    ]
