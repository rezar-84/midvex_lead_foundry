import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "lead_foundry.settings")

app = Celery("lead_foundry")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
