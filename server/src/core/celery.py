# your_project/celery.py
import os

from celery import Celery
from celery.schedules import timedelta

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")

app = Celery("core")

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object("django.conf:settings", namespace="CELERY")

# Load task modules from all registered Django app configs.
app.autodiscover_tasks()

# Define beat schedule for periodic tasks
app.conf.beat_schedule = {
    "ingest-polygon-data-every-30-seconds": {
        "task": "market_data.tasks.ingest_polygon_data_task",
        "schedule": timedelta(
            seconds=30
        ),  # Adjust based on your Polygon tier and requirements
        "args": (
            ["SPY", "NVDA", "TSLA", "AAPL"],
        ),  # Or pass empty tuple to use COMMON_TICKERS from task
        "options": {"queue": "data_ingestion"},  # Optional: dedicated queue
    },
    # Add other periodic tasks here
}
