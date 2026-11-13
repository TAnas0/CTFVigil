import os
from celery import Celery
from celery.schedules import crontab

# Read broker and backend URLs from environment variable with fallback
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Initialize Celery using Redis as both the broker and result backend
celery_app = Celery(
    "ctfvigil_worker",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["tasks.tasks"],  # Explicitly tell Celery to load tasks/tasks.py
)

celery_app.conf.update(
    # ── Serialization ────────────────────────────────────────────────────────
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],

    # ── Time ─────────────────────────────────────────────────────────────────
    timezone="UTC",
    enable_utc=True,

    # ── Result backend ───────────────────────────────────────────────────────
    # Expire stored task results after 1 hour to prevent Redis bloat.
    # Results are only kept for introspection; CTFVigil does not query them
    # in normal operation (data is written to the shared RedisCache instead).
    result_expires=3600,

    # ── Beat schedule ────────────────────────────────────────────────────────
    # Fires sync_ctftime_events_task at the top of every 6th hour (00:00,
    # 06:00, 12:00, 18:00 UTC), keeping the cached event feed fresh without
    # hammering the CTFtime API. The first run occurs at the next scheduled
    # slot after the beat container starts.
    beat_schedule={
        "sync-ctftime-events-every-6h": {
            "task": "tasks.tasks.sync_ctftime_events_task",
            "schedule": crontab(minute=0, hour="*/6"),
            "options": {
                # Route periodic tasks to the default worker queue.
                "queue": "celery",
            },
        },
    },
)
