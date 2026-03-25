import os
from celery import Celery

broker_url = os.environ.get("REDIS_URL", "redis://redis:6379/0")
app = Celery("ptuve", broker=broker_url)
