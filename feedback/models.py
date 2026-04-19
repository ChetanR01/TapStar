from django.db import models

from businesses.models import Location


class PrivateFeedback(models.Model):
    """Low-rating feedback captured privately. Never reaches Google."""

    location = models.ForeignKey(Location, on_delete=models.CASCADE, related_name="private_feedback")
    star_rating = models.IntegerField()
    feedback_text = models.TextField()
    customer_name = models.CharField(max_length=200, blank=True)
    customer_phone = models.CharField(max_length=30, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["location", "is_read", "-created_at"])]
        verbose_name_plural = "Private feedback"

    def __str__(self):
        return f"Feedback ({self.star_rating} star) — {self.location} — {self.created_at:%Y-%m-%d}"
