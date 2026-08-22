import os
import django

def on_starting(server):
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ouitransfer.settings")
    django.setup()

    # start the background jobs once for the whole project
    from ouitransfer.jobs import start_background_jobs
    start_background_jobs()
