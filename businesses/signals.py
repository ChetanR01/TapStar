"""Signals: generate QR codes on Location save, auto-create BusinessSettings on Business save."""

from io import BytesIO
import logging

import qrcode
from django.conf import settings
from django.core.files.base import ContentFile
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Business, Location

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Business)
def create_business_settings(sender, instance: Business, created: bool, **kwargs):
    if not created:
        return
    from settings_mgr.models import BusinessCategory, BusinessSettings
    from reviews.business_types import default_categories_for

    BusinessSettings.objects.get_or_create(business=instance)

    # Seed top-level categories from the type registry on first creation only.
    if not BusinessCategory.objects.filter(business=instance, parent__isnull=True).exists():
        defaults = default_categories_for(instance.business_type)
        for index, cat in enumerate(defaults):
            BusinessCategory.objects.create(
                business=instance,
                parent=None,
                key=cat["key"],
                label=cat["label"],
                is_enabled=True,
                sort_order=index * 10,
            )


@receiver(post_save, sender=Location)
def generate_qr_image(sender, instance: Location, created: bool, **kwargs):
    if instance.qr_code_image:
        return

    url = f"{settings.SITE_URL.rstrip('/')}{instance.customer_page_path}"

    try:
        qr = qrcode.QRCode(
            version=None,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=10,
            border=4,
        )
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")

        buffer = BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)

        filename = f"{instance.qr_code_token}.png"
        instance.qr_code_image.save(filename, ContentFile(buffer.getvalue()), save=False)
        # Avoid recursion: update only this field
        Location.objects.filter(pk=instance.pk).update(qr_code_image=instance.qr_code_image.name)
    except Exception as exc:
        logger.exception("Failed to generate QR for location %s: %s", instance.pk, exc)
