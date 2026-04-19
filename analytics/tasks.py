"""Celery tasks for analytics."""

from datetime import date, timedelta

from celery import shared_task
from django.utils import timezone

from .services import aggregate_day


@shared_task(name="analytics.aggregate_yesterday")
def aggregate_yesterday() -> int:
    yesterday = (timezone.now() - timedelta(days=1)).date()
    return aggregate_day(yesterday)


@shared_task(name="analytics.aggregate_for_date")
def aggregate_for_date(iso_date: str) -> int:
    target = date.fromisoformat(iso_date)
    return aggregate_day(target)
