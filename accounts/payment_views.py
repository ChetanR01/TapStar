"""Easebuzz payment views: upgrade page, subscribe initiation, success/failure callbacks, webhook."""

import logging
import uuid
from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseBadRequest, HttpResponse
from django.shortcuts import redirect, render, get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .easebuzz import InitiateParams, initiate_payment, verify_callback_hash
from .models import SubscriptionPayment, User

logger = logging.getLogger(__name__)


PLAN_DETAILS = [
    {
        "code": User.PLAN_STARTER,
        "name": "Starter",
        "price_paise": settings.PLAN_PRICES_PAISE[User.PLAN_STARTER],
        "tagline": "Forever free",
        "features": [
            "50 AI reviews / month",
            "1 location",
            "English + Hinglish",
            "PNG QR code",
        ],
        "not_included": [
            "Negative review filter",
            "Analytics dashboard",
            "Custom keywords",
        ],
    },
    {
        "code": User.PLAN_GROWTH,
        "name": "Growth",
        "price_paise": settings.PLAN_PRICES_PAISE[User.PLAN_GROWTH],
        "tagline": "1 month free trial",
        "features": [
            "Unlimited AI reviews",
            "1 location",
            "All 6 language modes",
            "Negative review filter",
            "Custom keywords + blocked phrases",
            "Analytics dashboard",
            "WhatsApp review links",
            "PNG + SVG + standee PDF",
        ],
        "not_included": [
            "Multi-location dashboard",
            "API access",
            "Custom branding",
        ],
        "highlighted": True,
    },
    {
        "code": User.PLAN_BUSINESS,
        "name": "Business",
        "price_paise": settings.PLAN_PRICES_PAISE[User.PLAN_BUSINESS],
        "tagline": "1 month free trial",
        "features": [
            "Everything in Growth",
            "Up to 5 locations",
            "Multi-location dashboard",
            "SMS review links",
            "Custom branding on review page",
            "API access",
            "Priority support",
        ],
        "not_included": [],
    },
]


@login_required
def upgrade_page(request):
    plans = []
    for p in PLAN_DETAILS:
        plans.append({**p, "price_rupees": f"{p['price_paise'] / 100:.0f}"})
    return render(
        request,
        "accounts/upgrade.html",
        {
            "plans": plans,
            "current_plan": request.user.subscription_plan,
        },
    )


@login_required
@require_POST
def subscribe(request, plan: str):
    if plan not in settings.PLAN_PRICES_PAISE:
        return HttpResponseBadRequest("Unknown plan")
    if plan == User.PLAN_STARTER:
        # Starter is free — just switch plan
        request.user.subscription_plan = plan
        request.user.save(update_fields=["subscription_plan", "updated_at"])
        messages.success(request, "Switched to Starter plan.")
        return redirect("dashboard_home")

    amount_paise = settings.PLAN_PRICES_PAISE[plan]
    amount_rupees = f"{amount_paise / 100:.2f}"

    txnid = f"tap_{plan}_{request.user.pk}_{uuid.uuid4().hex[:10]}"
    payment = SubscriptionPayment.objects.create(
        user=request.user,
        plan=plan,
        amount_paise=amount_paise,
        easebuzz_txnid=txnid,
    )

    first_name = (request.user.first_name or request.user.email.split("@")[0])[:50]

    init_params = InitiateParams(
        txnid=txnid,
        amount_rupees=amount_rupees,
        product_info=f"Tapstar {plan.title()} plan",
        first_name=first_name,
        email=request.user.email,
        phone="",  # we don't collect phone at signup yet
        success_url=request.build_absolute_uri(reverse("payment_success")),
        failure_url=request.build_absolute_uri(reverse("payment_failure")),
        udf1=plan,
        udf2=str(request.user.pk),
    )

    result = initiate_payment(init_params)
    if not result.success:
        payment.status = SubscriptionPayment.STATUS_FAILED
        payment.error_message = result.error[:1000]
        payment.save(update_fields=["status", "error_message", "updated_at"])
        messages.error(request, f"Payment could not start: {result.error}")
        return redirect("upgrade")

    payment.raw_response = {"initiate": result.raw or {}}
    payment.save(update_fields=["raw_response", "updated_at"])

    return redirect(result.pay_url)


def _activate_subscription(user: User, plan: str, days: int = 30):
    now = timezone.now()
    base = user.subscription_active_until if (user.subscription_active_until and user.subscription_active_until > now) else now
    user.subscription_plan = plan
    user.subscription_status = User.STATUS_ACTIVE
    user.subscription_active_until = base + timedelta(days=days)
    user.save(update_fields=["subscription_plan", "subscription_status", "subscription_active_until", "updated_at"])


def _process_callback(request) -> tuple[SubscriptionPayment | None, str]:
    """Shared logic for success/failure/webhook — verifies hash + returns the payment row."""
    posted = {k: request.POST.get(k, "") for k in request.POST.keys()}
    txnid = posted.get("txnid", "")
    if not txnid:
        return None, "missing txnid"

    try:
        payment = SubscriptionPayment.objects.select_for_update().get(easebuzz_txnid=txnid)
    except SubscriptionPayment.DoesNotExist:
        return None, "unknown txnid"

    if not verify_callback_hash(posted):
        return payment, "hash mismatch"

    payment.easebuzz_payment_id = posted.get("easepayid") or posted.get("easebuzz_id", "")
    payment.raw_response = {**(payment.raw_response or {}), "callback": posted}

    status = posted.get("status", "").lower()
    if status == "success":
        payment.status = SubscriptionPayment.STATUS_SUCCESS
        _activate_subscription(payment.user, payment.plan)
    else:
        payment.status = SubscriptionPayment.STATUS_FAILED
        payment.error_message = posted.get("error_Message") or posted.get("error", "")[:1000]

    payment.save()
    return payment, ""


@csrf_exempt
@require_POST
def payment_success(request):
    """Easebuzz posts here on a successful payment (SURL). Browser-facing — renders a result page."""
    with transaction.atomic():
        payment, err = _process_callback(request)
    if err or not payment:
        logger.warning("Easebuzz SURL error: %s — payload=%s", err, request.POST)
        return render(request, "accounts/payment_result.html", {"ok": False, "message": err or "Invalid payment"})

    if payment.status != SubscriptionPayment.STATUS_SUCCESS:
        return render(request, "accounts/payment_result.html", {"ok": False, "message": "Payment was not successful.", "payment": payment})

    messages.success(request, f"Welcome to the {payment.plan.title()} plan!")
    return render(request, "accounts/payment_result.html", {"ok": True, "payment": payment})


@csrf_exempt
@require_POST
def payment_failure(request):
    """Easebuzz posts here on failure (FURL)."""
    with transaction.atomic():
        payment, err = _process_callback(request)
    return render(
        request,
        "accounts/payment_result.html",
        {"ok": False, "message": err or "Payment was not completed.", "payment": payment},
    )


@csrf_exempt
@require_POST
def payment_webhook(request):
    """Easebuzz server-to-server webhook — authoritative. Idempotent."""
    with transaction.atomic():
        payment, err = _process_callback(request)
    if err:
        logger.warning("Easebuzz webhook error: %s", err)
        return HttpResponse(status=400)
    return HttpResponse(status=200)
