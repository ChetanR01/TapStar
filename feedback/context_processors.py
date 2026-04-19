"""Expose unread feedback count on authenticated pages."""

from .models import PrivateFeedback


def unread_feedback(request):
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return {"unread_feedback_count": 0}
    count = PrivateFeedback.objects.filter(
        location__business__owner=user,
        is_read=False,
    ).count()
    return {"unread_feedback_count": count}
