from celery import Celery
from app.config import settings

celery_app = Celery(
    "scraper",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.tasks.email_tasks", "app.tasks.scrape_tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    task_acks_late=True,
    task_reject_on_worker_lost=True,
)
