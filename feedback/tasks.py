"""Celery tasks for the feedback app."""

import logging

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string

from .models import PrivateFeedback

logger = logging.getLogger(__name__)


@shared_task(name="feedback.send_owner_notification")
def send_owner_notification(feedback_id: int) -> None:
    try:
        fb = (
            PrivateFeedback.objects
            .select_related("location", "location__business", "location__business__owner")
            .get(pk=feedback_id)
        )
    except PrivateFeedback.DoesNotExist:
        logger.warning("send_owner_notification: feedback %s missing", feedback_id)
        return

    owner = fb.location.business.owner
    if not owner.email:
        return

    inbox_url = f"{settings.SITE_URL.rstrip('/')}/feedback/"
    subject = f"New {fb.star_rating}-star feedback for {fb.location.business.name}"
    body = render_to_string(
        "email/new_feedback.txt",
        {"fb": fb, "inbox_url": inbox_url, "business": fb.location.business},
    )

    send_mail(
        subject=subject,
        message=body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[owner.email],
        fail_silently=True,
    )
