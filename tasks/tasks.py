from tasks.celery_app import celery_app


@celery_app.task(bind=True, max_retries=3)
def sync_ctftime_events_task(self):
    """Heavy operation running entirely outside the Discord bot loop."""
    try:
        print("Fetching fresh CTF data from external API...")
        # Your API scraping or database syncing logic here
    except Exception as exc:
        # Automatic exponential backoff retry on failure
        raise self.retry(exc=exc, countdown=60)


@celery_app.task(bind=True, max_retries=3)
def check_ctfd_ctf(self, ctf_url: str):
    """Given"""
    try:
        print(f"Checking CTF platform at {ctf_url} for CTFd infrastructure...")
        # TODO ensure the URL points to a CTFd instance
    except Exception as exc:
        # Automatic exponential backoff retry on failure
        raise self.retry(exc=exc, countdown=60)
