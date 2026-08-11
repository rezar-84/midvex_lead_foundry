from django.urls import path

from . import views

urlpatterns = [
    path("health/", views.health, name="health"),
    path("mfa/setup/", views.mfa_setup, name="mfa_setup"),
    path("mfa/verify/", views.mfa_verify, name="mfa_verify"),
    path("", views.dashboard, name="dashboard"),
    path("conversations/", views.conversations, name="conversations"),
    path("knowledge/", views.knowledge, name="knowledge"),
    path("opportunities/", views.opportunities, name="opportunities"),
    path("opportunities/<uuid:candidate_id>/", views.opportunity_detail, name="opportunity_detail"),
    path(
        "opportunities/<uuid:candidate_id>/review/",
        views.review_opportunity,
        name="review_opportunity",
    ),
    path("exports/csv/", views.export_csv, name="export_csv"),
    path("sources/", views.sources, name="sources"),
    path("sources/gmail/connect/", views.gmail_connect, name="gmail_connect"),
    path("sources/gmail/callback/", views.gmail_callback, name="gmail_callback"),
]
