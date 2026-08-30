from django.apps import AppConfig


class OuitransferConfig(AppConfig):
    name = 'ouitransfer'

    def ready(self):
        """Start jobs when not using gunicorn (when in dev)"""
        import sys
        if 'gunicorn' in ' '.join(sys.argv).lower():
            return
        from .jobs import start_background_jobs
        start_background_jobs()