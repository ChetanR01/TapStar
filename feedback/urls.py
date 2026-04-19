from django.urls import path

from . import views

urlpatterns = [
    path("", views.feedback_inbox, name="feedback_inbox"),
    path("<int:feedback_id>/read/", views.mark_read, name="feedback_mark_read"),
    path("<int:feedback_id>/unread/", views.mark_unread, name="feedback_mark_unread"),
]
