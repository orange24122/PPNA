from celery import Celery

from app.config.settings import get_settings

settings = get_settings()

celery_app = Celery(
    "ppna_tasks",
    broker=settings.broker_url,
    backend=settings.result_backend,
)

celery_app.conf.update(
    task_default_queue=settings.celery_task_default_queue,
    result_expires=3600,
    task_track_started=True,
)

