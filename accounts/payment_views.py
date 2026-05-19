"""Easebuzz payment views: upgrade page, subscribe initiation, success/failure callbacks, webhook."""

import logging
import uuid
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseBadRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .easebuzz import InitiateParams, initiate_payment, verify_callback_hash
from .models import PricingPlan, SubscriptionPayment, User

logger = logging.getLogger(__name__)


def _active_plans():
    return list(PricingPlan.objects.filter(is_active=True))


def _plan_view_context(plan: PricingPlan) -> dict:
    return {
        "code": plan.code,
        "name": plan.name,
        "tagline": plan.tagline,
        "tier": plan.tier,
        "price_paise": plan.price_paise,
        "price_rupees": plan.price_rupees,
        "original_price_paise": plan.original_price_paise,
        "original_price_rupees": plan.original_price_rupees,
        "has_discount": plan.has_discount,
        "discount_percent": plan.discount_percent,
        "period": plan.period_label,
        "features": list(plan.features or []),
        "not_included": list(plan.not_included or []),
        "highlighted": plan.highlighted,
        "is_free": plan.is_free,
    }


@login_required
def upgrade_page(request):
    plans = [_plan_view_context(p) for p in _active_plans()]
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
    try:
        pricing_plan = PricingPlan.objects.get(code=plan, is_active=True)
    except PricingPlan.DoesNotExist:
        return HttpResponseBadRequest("Unknown plan")

    if pricing_plan.is_free:
        # Free plan — just switch.
        request.user.subscription_plan = pricing_plan.code
        request.user.save(update_fields=["subscription_plan", "updated_at"])
        messages.success(request, f"Switched to the {pricing_plan.name} plan.")
        return redirect("dashboard_home")

    amount_paise = pricing_plan.price_paise
    amount_rupees = f"{amount_paise / 100:.2f}"

    txnid = f"tap_{pricing_plan.code}_{request.user.pk}_{uuid.uuid4().hex[:10]}"
    payment = SubscriptionPayment.objects.create(
        user=request.user,
        plan=pricing_plan.code,
        amount_paise=amount_paise,
        easebuzz_txnid=txnid,
    )

    first_name = (request.user.first_name or request.user.email.split("@")[0])[:50]

    init_params = InitiateParams(
        txnid=txnid,
        amount_rupees=amount_rupees,
        product_info=f"Tapstar {pricing_plan.name} plan",
        first_name=first_name,
        email=request.user.email,
        phone="",  # we don't collect phone at signup yet
        success_url=request.build_absolute_uri(reverse("payment_success")),
        failure_url=request.build_absolute_uri(reverse("payment_failure")),
        udf1=pricing_plan.code,
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


def _activate_subscription(user: User, plan_code: str, days: int | None = None):
    if days is None:
        pricing_plan = PricingPlan.objects.filter(code=plan_code).first()
        days = pricing_plan.billing_period_days if pricing_plan else 30
    now = timezone.now()
    base = user.subscription_active_until if (user.subscription_active_until and user.subscription_active_until > now) else now
    user.subscription_plan = plan_code
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
