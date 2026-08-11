from django.urls import path

from . import project_views, views

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
    path("projects/", project_views.project_list, name="project_list"),
    path("projects/new/", project_views.project_create, name="project_create"),
    path("projects/<uuid:project_id>/", project_views.project_detail, name="project_detail"),
    path(
        "projects/<uuid:project_id>/settings/",
        project_views.project_settings,
        name="project_settings",
    ),
    path(
        "projects/<uuid:project_id>/sources/new/",
        project_views.source_create,
        name="project_source_create",
    ),
    path(
        "projects/<uuid:project_id>/sources/<uuid:source_id>/",
        project_views.source_detail,
        name="project_source_detail",
    ),
    path(
        "projects/<uuid:project_id>/sources/<uuid:source_id>/edit/",
        project_views.source_edit,
        name="project_source_edit",
    ),
    path(
        "projects/<uuid:project_id>/sources/<uuid:source_id>/sync/",
        project_views.source_sync,
        name="project_source_sync",
    ),
    path(
        "projects/<uuid:project_id>/sources/<uuid:source_id>/gmail/connect/",
        project_views.source_gmail_connect,
        name="project_source_gmail_connect",
    ),
    path(
        "projects/<uuid:project_id>/analysis/start/",
        project_views.analysis_start,
        name="project_analysis_start",
    ),
    path("projects/<uuid:project_id>/jobs/", project_views.job_list, name="project_jobs"),
    path(
        "projects/<uuid:project_id>/jobs/<uuid:job_id>/",
        project_views.job_detail,
        name="project_job_detail",
    ),
    path(
        "projects/<uuid:project_id>/jobs/<uuid:job_id>/status/",
        project_views.job_status,
        name="project_job_status",
    ),
    path(
        "projects/<uuid:project_id>/jobs/<uuid:job_id>/cancel/",
        project_views.job_cancel,
        name="project_job_cancel",
    ),
    path(
        "projects/<uuid:project_id>/contacts/",
        project_views.project_contacts,
        name="project_contacts",
    ),
    path(
        "projects/<uuid:project_id>/contacts/<uuid:contact_id>/",
        project_views.contact_detail,
        name="project_contact_detail",
    ),
    path(
        "projects/<uuid:project_id>/enrichment/<uuid:result_id>/review/",
        project_views.enrichment_review,
        name="project_enrichment_review",
    ),
    path(
        "projects/<uuid:project_id>/enrichment/start/",
        project_views.enrichment_start,
        name="project_enrichment_start",
    ),
    path(
        "projects/<uuid:project_id>/contacts/tags/assign/",
        project_views.contact_tag_assign,
        name="project_contact_tag_assign",
    ),
    path("projects/<uuid:project_id>/tags/", project_views.project_tags, name="project_tags"),
    path(
        "projects/<uuid:project_id>/products/",
        project_views.project_products,
        name="project_products",
    ),
    path(
        "projects/<uuid:project_id>/products/new/",
        project_views.product_create,
        name="project_product_create",
    ),
]
