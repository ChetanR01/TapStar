from django.urls import path

from . import payment_views

urlpatterns = [
    path("upgrade/", payment_views.upgrade_page, name="upgrade"),
    path("subscribe/<str:plan>/", payment_views.subscribe, name="subscribe"),
    path("success/", payment_views.payment_success, name="payment_success"),
    path("failure/", payment_views.payment_failure, name="payment_failure"),
    path("webhook/", payment_views.payment_webhook, name="payment_webhook"),
]
