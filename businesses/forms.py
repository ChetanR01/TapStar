from django import forms

from .models import Business, Location
from .utils import fetch_place_photo_url, resolve_and_parse


PLACE_FIELD_HELP = (
    "Paste your Google Place ID, Maps URL, or review link — we'll figure it out. "
    "Tip: open your business on Google Maps → Share → Copy link."
)


class _PlaceIdParsingMixin:
    """Accepts Place ID OR Google link in the google_place_id field.

    Stores the parsed place_id (if found) and the normalised review URL
    on the instance. Any extraction note is exposed as ``place_parse_note``
    for the view to surface to the user.
    """

    def clean_google_place_id(self):
        raw = (self.cleaned_data.get("google_place_id") or "").strip()
        if not raw:
            return ""
        parsed = resolve_and_parse(raw)
        self._parsed_place = parsed
        if not parsed["place_id"] and not parsed["review_url"]:
            raise forms.ValidationError(
                "We couldn't recognise that as a Place ID or Google link. "
                "Try pasting the URL from Google Maps → Share → Copy link."
            )
        return parsed["place_id"]

    def save(self, commit=True):
        instance = super().save(commit=False)
        parsed = getattr(self, "_parsed_place", None)
        if parsed:
            if parsed["review_url"]:
                instance.google_review_url = parsed["review_url"]
            elif not parsed["place_id"]:
                instance.google_review_url = ""

            # Only Business has google_photo_url — refresh it when the
            # place_id changes (best-effort; no-op without API key).
            if isinstance(instance, Business) and parsed["place_id"]:
                photo = fetch_place_photo_url(parsed["place_id"])
                if photo:
                    instance.google_photo_url = photo
        if commit:
            instance.save()
        return instance

    @property
    def place_parse_note(self) -> str:
        parsed = getattr(self, "_parsed_place", None)
        return parsed["note"] if parsed else ""


class BusinessOnboardingForm(_PlaceIdParsingMixin, forms.ModelForm):
    class Meta:
        model = Business
        fields = ("name", "business_type", "google_place_id", "address", "logo")
        labels = {
            "google_place_id": "Google Place ID or review link",
        }
        help_texts = {
            "google_place_id": PLACE_FIELD_HELP,
        }
        widgets = {
            "address": forms.Textarea(attrs={"rows": 3}),
            "google_place_id": forms.TextInput(attrs={
                "placeholder": "ChIJ… or https://maps.app.goo.gl/…",
                "autocomplete": "off",
                "spellcheck": "false",
            }),
        }


class LocationForm(_PlaceIdParsingMixin, forms.ModelForm):
    class Meta:
        model = Location
        fields = ("name", "google_place_id")
        labels = {
            "google_place_id": "Google Place ID or review link",
        }
        help_texts = {
            "google_place_id": (
                "Optional — overrides the business-level link if this branch "
                "has its own Google listing. " + PLACE_FIELD_HELP
            ),
        }
        widgets = {
            "google_place_id": forms.TextInput(attrs={
                "placeholder": "ChIJ… or https://maps.app.goo.gl/…",
                "autocomplete": "off",
                "spellcheck": "false",
            }),
        }
