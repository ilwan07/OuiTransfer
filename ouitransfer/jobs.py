from django.conf import settings

import time
import logging
from threading import Thread

log = logging.getLogger(__name__)


def start_background_jobs():
    """Start all the background jobs in a thread"""
    log.info("Starting background jobs")
    if settings.USE_ANTIVIRUS:
        start_job_loop(antivirus_job, 60)


def start_job_loop(fn:function, delay=60):
    """Start a given recurring job in a separate thread"""
    def job_loop():
        while True:
            try:
                fn()
            except Exception as e:
                log.error(f"Failure in job {fn.__name__}: {e}")
            time.sleep(delay)
    job_thread = Thread(target=job_loop)
    job_thread.daemon = True  # Avoid blocking shutdown
    job_thread.start()
    log.debug(f"Started job {fn.__name__}")


def antivirus_job():
    """Scan every pending file"""
    pass  #TODO scan job
