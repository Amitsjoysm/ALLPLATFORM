from celery import Celery
from celery.schedules import crontab
from config import settings
import logging

logger = logging.getLogger(__name__)

# Create Celery app
celery_app = Celery(
    "traffic_engine",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour
    task_soft_time_limit=3000,  # 50 minutes
)

# Import tasks for autodiscovery
celery_app.conf.imports = ("celery_tasks",)

# Celery Beat schedule - hourly scraping
celery_app.conf.beat_schedule = {
    "hourly-traffic-scan": {
        "task": "celery_tasks.run_hourly_scan",
        "schedule": crontab(minute=0),  # Every hour
    },
}
