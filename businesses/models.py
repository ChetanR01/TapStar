import uuid
from django.conf import settings
from django.db import models


def _business_type_choices():
    # Late import so the registry module isn't pulled during Django app loading
    # in a cycle — businesses imports reviews via this lazy resolver only.
    from reviews.business_types import flat_choices
    return flat_choices()


class Business(models.Model):
    TYPE_RESTAURANT = "restaurant"
    TYPE_SALON = "salon"
    TYPE_CLINIC = "clinic"
    TYPE_RETAIL = "retail"
    TYPE_OTHER = "other"
    # Kept for any legacy code; the full canonical list lives in
    # reviews/business_types.py and is used at model-choice resolution time.
    TYPE_CHOICES = _business_type_choices()

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="businesses")
    name = models.CharField(max_length=200)
    business_type = models.CharField(max_length=40, choices=TYPE_CHOICES, default=TYPE_OTHER)
    google_place_id = models.CharField(max_length=255, blank=True)
    google_review_url = models.URLField(max_length=500, blank=True)
    google_photo_url = models.URLField(max_length=800, blank=True)
    address = models.TextField(blank=True)
    logo = models.ImageField(upload_to="business_logos/", blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if self.google_place_id and not self.google_review_url:
            self.google_review_url = self._build_google_review_url(self.google_place_id)
        super().save(*args, **kwargs)

    @staticmethod
    def _build_google_review_url(place_id: str) -> str:
        return f"https://search.google.com/local/writereview?placeid={place_id}"


class Location(models.Model):
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name="locations")
    name = models.CharField(max_length=200, default="Main")
    google_place_id = models.CharField(max_length=255, blank=True)
    google_review_url = models.URLField(max_length=500, blank=True)
    qr_code_token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    qr_code_image = models.ImageField(upload_to="qr_codes/", blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.business.name} — {self.name}"

    def save(self, *args, **kwargs):
        if not self.google_place_id and self.business_id:
            self.google_place_id = self.business.google_place_id
        if self.google_place_id and not self.google_review_url:
            self.google_review_url = Business._build_google_review_url(self.google_place_id)
        super().save(*args, **kwargs)

    @property
    def customer_page_path(self) -> str:
        return f"/r/{self.qr_code_token}/"
