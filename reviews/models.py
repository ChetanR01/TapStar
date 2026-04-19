import uuid
from django.db import models

from businesses.models import Location


class ReviewRequest(models.Model):
    """Anonymous customer session — one per QR scan interaction."""

    location = models.ForeignKey(Location, on_delete=models.CASCADE, related_name="review_requests")
    session_token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    star_rating = models.IntegerField()
    selected_categories = models.JSONField(default=list, blank=True)
    selected_items = models.JSONField(default=list, blank=True)

    language_mode_used = models.CharField(max_length=20, blank=True)
    tone_mode_used = models.CharField(max_length=20, blank=True)

    is_negative = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["location", "-created_at"])]

    def __str__(self):
        return f"Review request #{self.pk} ({self.star_rating} star)"


class ReviewVariant(models.Model):
    request = models.ForeignKey(ReviewRequest, on_delete=models.CASCADE, related_name="variants")
    variant_number = models.IntegerField()
    language = models.CharField(max_length=20)
    tone = models.CharField(max_length=20)
    text = models.TextField()
    was_selected = models.BooleanField(default=False)
    was_submitted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["variant_number"]
        unique_together = [("request", "variant_number")]

    def __str__(self):
        return f"Variant {self.variant_number} ({self.language}/{self.tone})"


class ReviewSubmission(models.Model):
    variant = models.OneToOneField(ReviewVariant, on_delete=models.CASCADE, related_name="submission")
    submitted_at = models.DateTimeField(auto_now_add=True)
    user_agent = models.CharField(max_length=500, blank=True)

    def __str__(self):
        return f"Submission for variant {self.variant_id} at {self.submitted_at:%Y-%m-%d %H:%M}"
