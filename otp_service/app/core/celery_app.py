import os
from celery import Celery

celery_app = Celery(
    "otp_worker",
    broker=os.getenv("CELERY_BROKER_URL"),
    backend=os.getenv("CELERY_RESULT_BACKEND"),
)

celery_app.conf.task_routes = {
    "app.tasks.*": {"queue": "otp_queue"},
}