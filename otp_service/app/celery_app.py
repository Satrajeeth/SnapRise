from celery import Celery

from app.config import get_settings

settings = get_settings()

celery_app = Celery("otp_worker")
celery_app.conf.broker_url = settings.celery_broker_url
celery_app.conf.result_backend = settings.celery_result_backend
celery_app.conf.task_routes = {"app.tasks.*": {"queue": "otp_queue"}}
celery_app.conf.task_soft_time_limit = 1500
celery_app.conf.task_time_limit = 1800
celery_app.conf.timezone = "UTC"
celery_app.conf.enable_utc = True
celery_app.conf.task_serializer = "json"
celery_app.conf.accept_content = ["json"]
celery_app.conf.result_serializer = "json"
celery_app.conf.result_expires = 3600
celery_app.conf.task_acks_late = True
celery_app.conf.task_track_started = True
celery_app.autodiscover_tasks(["app.tasks"])
