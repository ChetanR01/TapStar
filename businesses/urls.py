from django.urls import path

from . import views

urlpatterns = [
    path("", views.dashboard_home, name="dashboard_home"),
    path("onboarding/", views.business_onboarding, name="business_onboarding"),

    # Locations
    path("location/add/", views.location_add, name="location_add"),
    path("location/<int:location_id>/edit/", views.location_edit, name="location_edit"),
    path("location/<int:location_id>/delete/", views.location_delete, name="location_delete"),

    # Downloads
    path("location/<int:location_id>/qr.png", views.download_qr, name="download_qr"),
    path("location/<int:location_id>/qr.svg", views.location_qr_svg, name="location_qr_svg"),
    path("location/<int:location_id>/standee.pdf", views.location_standee_pdf, name="location_standee_pdf"),
    path("location/<int:location_id>/print/", views.location_print_gallery, name="location_print_gallery"),
    path("location/<int:location_id>/print/<slug:design>.pdf", views.location_print_pdf, name="location_print_pdf"),

    # Outreach
    path("location/<int:location_id>/whatsapp/", views.location_whatsapp_link, name="location_whatsapp"),
]
