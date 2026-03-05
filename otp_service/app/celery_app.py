from celery import Celery
from app.config import settings

celery_app = Celery(
    "otp_worker"
)

celery_app.conf.broker_url = settings.celery_broker_url
celery_app.conf.result_backend = settings.celery_result_backend

#Route tasks to specific queues
celery_app.config.task_routes = {
    "app.tasks.*": {"queue": "otp_queue"},
}

#Task execution limits
celery_app.conf.task_soft_time_limit = 1500 #25 min
celery_app.conf.task_time_limit = 1800 #30 min

#Timezone configuration
celery_app.conf.timezone = 'UTC'
celery_app.config.enable_utc = True

#Serialization configuration
celery_app.conf.task_serializer = "json"
celery_app.conf.accept_content = ["json"]
celery_app.conf.result_serializer = "json"

#Result expiration
celery_app.conf.result_expires = 3600 

#Reliability config
celery_app.conf.task_acks_late = True

celery_app.conf.task_track_started = True

#Auto discover tasks from app.tasks module
celery_app.autodiscover_tasks(["app.tasks"])

