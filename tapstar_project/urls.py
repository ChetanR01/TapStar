"""Root URL configuration for Tapstar."""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from businesses import views as business_views
from reviews import views as review_views
from feedback import views as feedback_views

urlpatterns = [
    path("admin/", admin.site.urls),

    # Public landing
    path("", business_views.landing_page, name="landing"),

    # Customer review page (public, no auth)
    path("r/<uuid:token>/", review_views.customer_review_page, name="customer_review"),

    # Public customer-side APIs
    path("api/generate-review/", review_views.generate_review_api, name="generate_review"),
    path("api/submit-review/", review_views.submit_review_api, name="submit_review"),
    path("api/submit-feedback/", feedback_views.submit_feedback_api, name="submit_feedback"),

    # Auth
    path("auth/", include("accounts.urls")),

    # Dashboard (login required)
    path("dashboard/", include("businesses.urls")),

    # Feedback inbox (login required)
    path("feedback/", include("feedback.urls")),

    # Analytics dashboard (Growth+)
    path("analytics/", include("analytics.urls")),

    # Business settings
    path("settings/", include("settings_mgr.urls")),

    # Payments
    path("payments/", include("accounts.payment_urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
