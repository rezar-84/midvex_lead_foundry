from django.urls import path

from . import views

# Everything user-facing is the SPA (served by the catch-all in lead_foundry/urls.py,
# backed by /api/). Only full-page flows stay server-rendered: MFA, the CSV download,
# and the Gmail OAuth redirect handshake.
urlpatterns = [
    path("health/", views.health, name="health"),
    path("mfa/setup/", views.mfa_setup, name="mfa_setup"),
    path("mfa/verify/", views.mfa_verify, name="mfa_verify"),
    path("exports/csv/", views.export_csv, name="export_csv"),
    path("integrations/gmail/connect/", views.gmail_connect, name="gmail_connect"),
    path("integrations/gmail/callback/", views.gmail_callback, name="gmail_callback"),
    path(
        "integrations/gmail/projects/<uuid:project_id>/sources/<uuid:source_id>/connect/",
        views.source_gmail_connect,
        name="project_source_gmail_connect",
    ),
]
