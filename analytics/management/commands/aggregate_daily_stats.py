"""
Usage:
  python manage.py aggregate_daily_stats              # aggregates yesterday
  python manage.py aggregate_daily_stats 2026-04-18   # specific day
"""

from datetime import date, timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from analytics.services import aggregate_day


class Command(BaseCommand):
    help = "Aggregate DailyStats for the given date (default: yesterday)."

    def add_arguments(self, parser):
        parser.add_argument("target_date", nargs="?", default=None, help="YYYY-MM-DD")

    def handle(self, *args, **options):
        if options["target_date"]:
            day = date.fromisoformat(options["target_date"])
        else:
            day = (timezone.now() - timedelta(days=1)).date()

        n = aggregate_day(day)
        self.stdout.write(self.style.SUCCESS(f"Aggregated DailyStats for {day} — {n} locations."))
