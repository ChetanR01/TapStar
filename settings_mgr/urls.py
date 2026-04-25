from django.urls import path

from . import views

urlpatterns = [
    path("", views.settings_page, name="settings_page"),
    path("categories/add/", views.category_add, name="settings_category_add"),
    path("categories/<int:category_id>/delete/", views.category_delete, name="settings_category_delete"),
]
