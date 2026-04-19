from io import BytesIO
from urllib.parse import quote

import qrcode
import qrcode.image.svg as qr_svg

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import Http404, HttpResponse, HttpResponseForbidden
from django.shortcuts import redirect, render, get_object_or_404
from django.urls import reverse
from django.views.decorators.http import require_POST

from accounts.gating import require_plan
from accounts.models import User

from .forms import BusinessOnboardingForm, LocationForm
from .models import Business, Location
from .pdf import (
    build_a4_poster_pdf,
    build_counter_card_pdf,
    build_standee_pdf,
    build_sticker_sheet_pdf,
    build_table_tent_pdf,
)


def landing_page(request):
    if request.user.is_authenticated:
        return redirect("dashboard_home")
    return render(request, "landing.html")


@login_required
def business_onboarding(request):
    existing = request.user.businesses.first()
    if existing:
        return redirect("dashboard_home")

    if request.method == "POST":
        form = BusinessOnboardingForm(request.POST, request.FILES)
        if form.is_valid():
            with transaction.atomic():
                business = form.save(commit=False)
                business.owner = request.user
                business.save()
                # Auto-create first Location — triggers QR generation signal
                Location.objects.create(business=business, name="Main")
            messages.success(request, "Business created. Your QR code is ready.")
            if form.place_parse_note:
                messages.info(request, form.place_parse_note)
            return redirect("dashboard_home")
    else:
        form = BusinessOnboardingForm()
    return render(request, "businesses/onboarding.html", {"form": form})


@login_required
def dashboard_home(request):
    from django.db.models import Avg
    from reviews.models import ReviewRequest, ReviewVariant
    from feedback.models import PrivateFeedback

    business = request.user.businesses.prefetch_related("locations").first()
    if not business:
        return redirect("business_onboarding")
    locations = list(business.locations.all())
    location_limit = _location_limit_for(request.user)
    pro_allowed = (
        request.user.has_active_subscription
        and request.user.subscription_plan in (User.PLAN_GROWTH, User.PLAN_BUSINESS)
    )

    owner_filter = {"location__business__owner": request.user}
    variant_owner_filter = {"request__location__business__owner": request.user}
    stats_generated = ReviewRequest.objects.filter(**owner_filter).count()
    stats_submitted = ReviewVariant.objects.filter(was_submitted=True, **variant_owner_filter).count()
    stats_negative = PrivateFeedback.objects.filter(**owner_filter).count()
    avg = ReviewRequest.objects.filter(**owner_filter).aggregate(a=Avg("star_rating"))["a"]
    stats_avg = f"{avg:.1f}" if avg else None

    locations_missing_link = [
        loc for loc in locations
        if not (loc.google_review_url or business.google_review_url)
    ]

    return render(
        request,
        "businesses/dashboard_home.html",
        {
            "business": business,
            "locations": locations,
            "location_limit": location_limit,
            "can_add_location": len(locations) < location_limit,
            "pro_allowed": pro_allowed,
            "stats_generated": stats_generated,
            "stats_submitted": stats_submitted,
            "stats_negative": stats_negative,
            "stats_avg": stats_avg,
            "locations_missing_link": locations_missing_link,
        },
    )


@login_required
def download_qr(request, location_id: int):
    location = get_object_or_404(Location, pk=location_id, business__owner=request.user)
    if not location.qr_code_image:
        raise Http404("QR code not generated yet.")
    with location.qr_code_image.open("rb") as f:
        data = f.read()
    safe_name = f"tapstar-qr-{location.business.name}-{location.name}.png".replace(" ", "_")
    response = HttpResponse(data, content_type="image/png")
    response["Content-Disposition"] = f'attachment; filename="{safe_name}"'
    return response


# ----------------- Multi-location CRUD -----------------

def _location_limit_for(user: User) -> int:
    plan = user.subscription_plan if user.has_active_subscription else User.PLAN_STARTER
    return settings.PLAN_LOCATION_LIMITS.get(plan, 1)


@login_required
def location_add(request):
    business = request.user.businesses.first()
    if not business:
        return redirect("business_onboarding")

    limit = _location_limit_for(request.user)
    current_count = business.locations.count()
    if current_count >= limit:
        if limit == 1:
            messages.info(request, "Upgrade to the Business plan to run up to 5 locations.")
        else:
            messages.warning(request, f"You've hit your {limit}-location limit.")
        return redirect("upgrade")

    if request.method == "POST":
        form = LocationForm(request.POST)
        if form.is_valid():
            loc = form.save(commit=False)
            loc.business = business
            loc.save()
            messages.success(request, f"Location '{loc.name}' added.")
            if form.place_parse_note:
                messages.info(request, form.place_parse_note)
            return redirect("dashboard_home")
    else:
        form = LocationForm()
    return render(
        request,
        "businesses/location_form.html",
        {"form": form, "mode": "add", "business": business},
    )


@login_required
def location_edit(request, location_id: int):
    location = get_object_or_404(Location, pk=location_id, business__owner=request.user)

    if request.method == "POST":
        form = LocationForm(request.POST, instance=location)
        if form.is_valid():
            form.save()
            messages.success(request, "Location updated.")
            if form.place_parse_note:
                messages.info(request, form.place_parse_note)
            return redirect("dashboard_home")
    else:
        form = LocationForm(instance=location)
    return render(
        request,
        "businesses/location_form.html",
        {"form": form, "mode": "edit", "location": location, "business": location.business},
    )


@login_required
def location_delete(request, location_id: int):
    location = get_object_or_404(Location, pk=location_id, business__owner=request.user)

    # Refuse to delete the last remaining location — the business needs at least one
    if location.business.locations.count() <= 1:
        messages.error(request, "You need at least one location. Add another before deleting this one.")
        return redirect("dashboard_home")

    if request.method == "POST":
        name = location.name
        location.delete()
        messages.success(request, f"Location '{name}' deleted.")
        return redirect("dashboard_home")
    return render(
        request,
        "businesses/location_delete.html",
        {"location": location},
    )


# ----------------- Standee PDF + SVG QR (Growth+) -----------------

def _review_page_url(request, location: Location) -> str:
    return request.build_absolute_uri(reverse("customer_review", args=[location.qr_code_token]))


_PRINT_DESIGNS = {
    "standee": ("A5 standee", build_standee_pdf),
    "poster": ("A4 poster", build_a4_poster_pdf),
    "tent": ("Table tent (A4)", build_table_tent_pdf),
    "counter": ("Counter card (A6)", build_counter_card_pdf),
    "stickers": ("Sticker sheet (A4, 6-up)", build_sticker_sheet_pdf),
}


def _render_print_pdf(request, location_id: int, design_key: str):
    if design_key not in _PRINT_DESIGNS:
        raise Http404("Unknown design")
    location = get_object_or_404(Location, pk=location_id, business__owner=request.user)
    url = _review_page_url(request, location)
    _, builder = _PRINT_DESIGNS[design_key]
    pdf_bytes = builder(location, url)
    safe_name = (
        f"tapstar-{design_key}-{location.business.name}-{location.name}.pdf"
    ).replace(" ", "_")
    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    # ?preview=1 → show in browser tab; otherwise force download
    disposition = "inline" if request.GET.get("preview") else "attachment"
    response["Content-Disposition"] = f'{disposition}; filename="{safe_name}"'
    return response


@login_required
@require_plan(User.PLAN_GROWTH)
def location_standee_pdf(request, location_id: int):
    return _render_print_pdf(request, location_id, "standee")


@login_required
@require_plan(User.PLAN_GROWTH)
def location_print_pdf(request, location_id: int, design: str):
    return _render_print_pdf(request, location_id, design)


@login_required
def location_print_gallery(request, location_id: int):
    """Preview gallery for all print-ready QR templates."""
    location = get_object_or_404(Location, pk=location_id, business__owner=request.user)
    pro_allowed = (
        request.user.has_active_subscription
        and request.user.subscription_plan in (User.PLAN_GROWTH, User.PLAN_BUSINESS)
    )
    designs = [
        {
            "key": "standee",
            "title": "A5 Standee",
            "subtitle": "Counter/table standee",
            "size": "148 × 210 mm",
            "best_for": "Restaurants, salons, clinics",
        },
        {
            "key": "poster",
            "title": "A4 Poster",
            "subtitle": "Bold wall poster",
            "size": "210 × 297 mm",
            "best_for": "Entry doors, walls, high-traffic spots",
        },
        {
            "key": "tent",
            "title": "Table Tent",
            "subtitle": "Folded A4 landscape",
            "size": "297 × 210 mm (folded to 297 × 105)",
            "best_for": "Restaurant tables, waiting areas",
        },
        {
            "key": "counter",
            "title": "Counter Card",
            "subtitle": "Compact A6 card",
            "size": "105 × 148 mm",
            "best_for": "Checkout counters, register desks",
        },
        {
            "key": "stickers",
            "title": "Sticker Sheet",
            "subtitle": "6 stickers per A4",
            "size": "70 × 90 mm each",
            "best_for": "Menus, bills, packaging",
        },
    ]
    return render(
        request,
        "businesses/print_gallery.html",
        {
            "location": location,
            "business": location.business,
            "designs": designs,
            "pro_allowed": pro_allowed,
        },
    )


@login_required
@require_plan(User.PLAN_GROWTH)
def location_qr_svg(request, location_id: int):
    location = get_object_or_404(Location, pk=location_id, business__owner=request.user)
    url = _review_page_url(request, location)
    img = qrcode.make(url, image_factory=qr_svg.SvgImage, box_size=10, border=4)
    buf = BytesIO()
    img.save(buf)
    safe_name = f"tapstar-qr-{location.business.name}-{location.name}.svg".replace(" ", "_")
    response = HttpResponse(buf.getvalue(), content_type="image/svg+xml")
    response["Content-Disposition"] = f'attachment; filename="{safe_name}"'
    return response


@login_required
@require_plan(User.PLAN_GROWTH)
def location_whatsapp_link(request, location_id: int):
    """Render a small page with the WhatsApp share link pre-built — also exposed as JSON for AJAX."""
    location = get_object_or_404(Location, pk=location_id, business__owner=request.user)
    url = _review_page_url(request, location)
    default_msg = (
        f"Hi! Thanks for visiting {location.business.name}. "
        f"Would you mind leaving us a quick review? It takes 10 seconds: {url}"
    )
    wa_link = f"https://wa.me/?text={quote(default_msg)}"
    return render(
        request,
        "businesses/whatsapp_share.html",
        {"location": location, "review_url": url, "default_msg": default_msg, "wa_link": wa_link},
    )
