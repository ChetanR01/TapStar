from decimal import Decimal
from django.db import models

from businesses.models import Business, Location


class GoogleReviewSnapshot(models.Model):
    """Manual monthly input by the business owner — their live Google review count.

    Earliest row = baseline (before-joining count). Latest row = current count.
    Used for the "since joining" comparison widget.
    """

    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name="google_snapshots")
    date = models.DateField()
    review_count = models.IntegerField()
    note = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date"]
        unique_together = [("business", "date")]
        indexes = [models.Index(fields=["business", "-date"])]

    def __str__(self):
        return f"{self.business.name} — {self.date} — {self.review_count}"


class DailyStats(models.Model):
    location = models.ForeignKey(Location, on_delete=models.CASCADE, related_name="daily_stats")
    date = models.DateField()

    reviews_generated = models.IntegerField(default=0)
    reviews_submitted = models.IntegerField(default=0)
    negative_redirects = models.IntegerField(default=0)
    avg_rating = models.DecimalField(max_digits=3, decimal_places=2, default=Decimal("0.00"))

    language_breakdown = models.JSONField(default=dict, blank=True)
    category_breakdown = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-date"]
        unique_together = [("location", "date")]
        indexes = [models.Index(fields=["location", "-date"])]
        verbose_name_plural = "Daily stats"

    def __str__(self):
        return f"{self.location} — {self.date}"
