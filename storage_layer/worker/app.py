import os
from celery import Celery

broker_url = os.environ.get("CELERY_BROKER_URL", "redis://redis:6379/0")
app = Celery("ptuve", broker=broker_url)

@app.task
def ping():
    return "pong"
