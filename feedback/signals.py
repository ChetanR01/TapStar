"""Fire owner email on new PrivateFeedback."""

from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import PrivateFeedback
from .tasks import send_owner_notification


@receiver(post_save, sender=PrivateFeedback)
def notify_owner_on_create(sender, instance: PrivateFeedback, created: bool, **kwargs):
    if not created:
        return
    # Runs eagerly in dev (CELERY_TASK_ALWAYS_EAGER=True); queued in prod.
    send_owner_notification.delay(instance.pk)
