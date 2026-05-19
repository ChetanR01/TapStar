"""Add PricingPlan model, seed default rows, and loosen plan-code choices on
SubscriptionPayment + User.subscription_plan so admin-defined plan codes work.
"""

from django.db import migrations, models


DEFAULT_PLANS = [
    {
        "code": "starter",
        "name": "Starter",
        "tagline": "Try it free",
        "tier": "starter",
        "billing_period_days": 0,
        "price_paise": 0,
        "original_price_paise": 0,
        "features": [
            "1 location",
            "5 AI reviews / month",
            "English + Hinglish",
            "QR PNG download",
            "Private feedback inbox",
        ],
        "not_included": [
            "Custom keywords / blocked phrases",
            "Print templates (PDF)",
            "Analytics dashboard",
        ],
        "review_limit": 5,
        "location_limit": 1,
        "highlighted": False,
        "sort_order": 10,
    },
    {
        "code": "monthly",
        "name": "1 Month",
        "tagline": "Try the full toolkit",
        "tier": "growth",
        "billing_period_days": 30,
        "price_paise": 9900,
        "original_price_paise": 14900,
        "features": [
            "1 location",
            "Unlimited AI reviews",
            "All 6 languages (incl. Devanagari)",
            "All 5 print templates (PDF)",
            "Custom keywords & blocked phrases",
            "Analytics dashboard",
            "WhatsApp share link",
        ],
        "not_included": [],
        "review_limit": None,
        "location_limit": 1,
        "highlighted": False,
        "sort_order": 20,
    },
    {
        "code": "halfyearly",
        "name": "6 Months",
        "tagline": "Most popular",
        "tier": "growth",
        "billing_period_days": 180,
        "price_paise": 49900,
        "original_price_paise": 89900,
        "features": [
            "Everything in 1 Month",
            "Save vs monthly pricing",
            "Priority support",
        ],
        "not_included": [],
        "review_limit": None,
        "location_limit": 1,
        "highlighted": True,
        "sort_order": 30,
    },
    {
        "code": "yearly",
        "name": "1 Year",
        "tagline": "Best value",
        "tier": "growth",
        "billing_period_days": 365,
        "price_paise": 89900,
        "original_price_paise": 179900,
        "features": [
            "Everything in 6 Months",
            "Biggest discount",
            "Priority support",
        ],
        "not_included": [],
        "review_limit": None,
        "location_limit": 1,
        "highlighted": False,
        "sort_order": 40,
    },
]


def seed_plans(apps, schema_editor):
    PricingPlan = apps.get_model("accounts", "PricingPlan")
    for cfg in DEFAULT_PLANS:
        PricingPlan.objects.update_or_create(code=cfg["code"], defaults=cfg)

    # Existing users on the old plan codes ("growth", "business") need to keep
    # working. "growth" already collides with the new "growth" tier — no rename
    # needed. "business" maps to "yearly" (closest analog: yearly billing).
    User = apps.get_model("accounts", "User")
    User.objects.filter(subscription_plan="growth").update(subscription_plan="monthly")
    User.objects.filter(subscription_plan="business").update(subscription_plan="yearly")


def unseed_plans(apps, schema_editor):
    PricingPlan = apps.get_model("accounts", "PricingPlan")
    PricingPlan.objects.filter(code__in=[p["code"] for p in DEFAULT_PLANS]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0002_remove_user_razorpay_customer_id_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="PricingPlan",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.CharField(help_text="Stable slug used in URLs and stored on User.subscription_plan. Don't change after launch.", max_length=32, unique=True)),
                ("name", models.CharField(help_text="Public display name. e.g. '1 Month', '6 Months', '1 Year'.", max_length=50)),
                ("tagline", models.CharField(blank=True, help_text="Optional one-liner under the name.", max_length=120)),
                ("tier", models.CharField(choices=[("starter", "Starter"), ("growth", "Growth"), ("business", "Business")], default="growth", help_text="Which feature bucket this plan unlocks. Multiple paid plans can share the same tier.", max_length=20)),
                ("billing_period_days", models.IntegerField(default=30, help_text="How many days a successful payment extends the subscription. 0 for free plans.")),
                ("price_paise", models.IntegerField(default=0, help_text="Current/discounted price in paise. 0 = free.")),
                ("original_price_paise", models.IntegerField(default=0, help_text="Original price (struck-through). 0 or equal to price_paise hides the strike-through.")),
                ("features", models.JSONField(blank=True, default=list, help_text='List of feature strings, e.g. ["Unlimited reviews", "1 location"].')),
                ("not_included", models.JSONField(blank=True, default=list, help_text="Optional list of features explicitly NOT included.")),
                ("review_limit", models.IntegerField(blank=True, help_text="Max review generations per month. Leave blank for unlimited.", null=True)),
                ("location_limit", models.IntegerField(default=1, help_text="Max number of business locations this plan allows.")),
                ("highlighted", models.BooleanField(default=False, help_text="Show 'Most popular' badge.")),
                ("is_active", models.BooleanField(default=True, help_text="Untick to hide from the upgrade page.")),
                ("sort_order", models.IntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "ordering": ["sort_order", "billing_period_days", "price_paise"],
            },
        ),
        migrations.AlterField(
            model_name="subscriptionpayment",
            name="plan",
            field=models.CharField(help_text="PricingPlan.code at the time of payment.", max_length=32),
        ),
        migrations.AlterField(
            model_name="user",
            name="subscription_plan",
            field=models.CharField(default="starter", max_length=32),
        ),
        migrations.RunPython(seed_plans, unseed_plans),
    ]
