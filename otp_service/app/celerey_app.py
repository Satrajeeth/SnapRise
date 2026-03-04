from celery import Celery
from app.config import settings

celery_app = Celery(
    "otp_worker"
)

celery_app.conf.broker_url = settings.celery_broker_url


