from django.conf import settings

import os
import time
import logging
from threading import Thread

from .models import ShareModel, RequestModel, FileModel

log = logging.getLogger(__name__)


def start_background_jobs():
    """Start all the background jobs in a thread"""
    if os.environ.get("RUN_MAIN") != "true" and settings.DEBUG == True:
        return  # prevent starting the jobs multiple times in development
    log.info("Starting background jobs")

    if settings.USE_ANTIVIRUS:
        start_job_loop(antivirus_job, 30)


def start_job_loop(fn:function, delay:int):
    """Start a given recurring job in a separate thread"""
    def job_loop():
        while True:
            try:
                fn()
            except Exception as e:
                log.error(f"Failure in job {fn.__name__}: {e}")
            time.sleep(delay)
    job_thread = Thread(target=job_loop)
    job_thread.daemon = True  # stop threads with the program
    job_thread.start()
    log.debug(f"Started job {fn.__name__}")


def antivirus_job():
    """Scan every pending file"""
    to_scan = FileModel.objects.filter(upload_completed=True, antivirus_status=0)
    for item in to_scan:
        try:
            item.perform_antivirus()
            item.save()
        except Exception as e:
            log.error(f"Failed to perform antivirus job on file {item.id}")
