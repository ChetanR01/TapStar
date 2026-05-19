"""Subscription gating — decorator for function views and mixin for class-based views.

``required_plan`` is a feature tier label (starter/growth/business). Each
PricingPlan row carries a `tier`, and the user's current PricingPlan
determines their effective tier. Trial users get the growth tier.
"""

from functools import wraps
from django.contrib import messages
from django.shortcuts import redirect

from .models import TIER_BUSINESS, TIER_GROWTH, TIER_STARTER, User


PLAN_ORDER = {TIER_STARTER: 0, TIER_GROWTH: 1, TIER_BUSINESS: 2}


def _has_plan(user, required_plan: str) -> bool:
    if not user.is_authenticated:
        return False
    if not user.has_active_subscription:
        return False
    return PLAN_ORDER.get(user.feature_tier, 0) >= PLAN_ORDER.get(required_plan, 0)


def require_plan(required_plan: str):
    """Decorator for FBVs — redirects to upgrade page if user lacks the required plan."""
    def decorator(view_fn):
        @wraps(view_fn)
        def _wrapped(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect("login")
            if not _has_plan(request.user, required_plan):
                messages.info(
                    request,
                    f"This feature needs the {required_plan.title()} plan. Upgrade to continue."
                )
                return redirect("upgrade")
            return view_fn(request, *args, **kwargs)
        return _wrapped
    return decorator


class SubscriptionGate:
    """CBV mixin. Set `required_plan` on the class."""
    required_plan: str = User.PLAN_STARTER

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("login")
        if not _has_plan(request.user, self.required_plan):
            messages.info(
                request,
                f"This feature needs the {self.required_plan.title()} plan. Upgrade to continue."
            )
            return redirect("upgrade")
        return super().dispatch(request, *args, **kwargs)
