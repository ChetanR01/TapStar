"""Celery application config."""

import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tapstar_project.settings")

app = Celery("tapstar")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
