import os
from celery import Celery

# Read broker and backend URLs from environment variable with fallback
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Initialize Celery using Redis as both the broker and result backend
celery_app = Celery(
    "ctfvigil_worker",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["tasks"]  # Explicitly tell Celery to load tasks.py
)

# Optional configuration settings
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
)