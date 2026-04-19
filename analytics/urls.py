from django.urls import path

from . import views

urlpatterns = [
    path("", views.dashboard, name="analytics_dashboard"),
    path("google-snapshot/", views.add_google_snapshot, name="analytics_google_snapshot"),
]
