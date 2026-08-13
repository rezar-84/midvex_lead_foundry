from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from foundry.models import Contact, Membership, MFADevice, ProjectEntity

from .test_project_operations import create_project


def _login_role(client, organization, role: str, username: str):
    user = get_user_model().objects.create_user(
        username=username,
        password="a-strong-test-password",  # noqa: S106
    )
    Membership.objects.create(organization=organization, user=user, role=role)
    MFADevice.objects.create(
        user=user,
        encrypted_secret="test",  # noqa: S106
        confirmed_at="2026-01-01T00:00:00Z",
    )
    client.force_login(user)
    session = client.session
    session["mfa_verified"] = True
    session.save()
    return client


def _add_contacts(project, count: int) -> list[Contact]:
    contacts = []
    for index in range(count):
        contact = Contact.objects.create(
            organization=project.organization,
            display_name=f"Contact {index:03d}",
            primary_email=f"contact{index:03d}@example.test",
        )
        ProjectEntity.objects.create(
            organization=project.organization,
            project=project,
            entity_type="contact",
            entity_id=contact.id,
        )
        contacts.append(contact)
    return contacts


@pytest.mark.django_db
def test_analyst_cannot_start_enrichment(client, workspace):
    organization, _, _, _ = workspace
    project = create_project(organization)
    contacts = _add_contacts(project, 1)
    _login_role(client, organization, Membership.Role.ANALYST, "bulk-analyst")

    response = client.post(
        f"/api/projects/{project.id}/enrichment/start",
        data={
            "contact_ids": [str(contacts[0].id)],
            "request_budget": 5,
            "confirm_scope": True,
        },
        content_type="application/json",
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden"


@pytest.mark.django_db
def test_enrichment_start_requires_confirmed_scope(mfa_session, workspace):
    organization, _, _, _ = workspace
    project = create_project(organization)
    contacts = _add_contacts(project, 2)

    response = mfa_session.post(
        f"/api/projects/{project.id}/enrichment/start",
        data={
            "contact_ids": [str(contacts[0].id)],
            "request_budget": 5,
            "confirm_scope": False,
        },
        content_type="application/json",
    )
    assert response.status_code == 400
    error = response.json()["error"]
    assert error["code"] == "validation_error"
    assert "confirm_scope" in error["fields"]

    invalid_ids = mfa_session.post(
        f"/api/projects/{project.id}/enrichment/start",
        data={
            "contact_ids": ["11111111-1111-1111-1111-111111111111"],
            "request_budget": 5,
            "confirm_scope": True,
        },
        content_type="application/json",
    )
    assert invalid_ids.status_code == 400
    assert "contact_ids" in invalid_ids.json()["error"]["fields"]


@pytest.mark.django_db
def test_contacts_paginate(mfa_session, workspace):
    organization, _, _, _ = workspace
    project = create_project(organization)
    _add_contacts(project, 60)

    first = mfa_session.get(f"/api/projects/{project.id}/contacts")
    second = mfa_session.get(f"/api/projects/{project.id}/contacts?page=2")
    assert first.status_code == 200
    assert first.json()["count"] == 60
    assert first.json()["pages"] == 2
    assert first.json()["per_page"] == 50
    assert len(first.json()["items"]) == 50
    assert len(second.json()["items"]) == 10


@pytest.mark.django_db
def test_mfa_setup_renders_qr_code(client, db):
    user = get_user_model().objects.create_user(
        username="fresh-user",
        password="a-strong-test-password",  # noqa: S106
    )
    client.force_login(user)
    response = client.get(reverse("mfa_setup"))
    content = response.content.decode()
    assert response.status_code == 200
    assert "data:image/svg+xml" in content
    assert "QR code for authenticator enrolment" in content


@pytest.mark.django_db
def test_login_page_uses_shared_form_rendering(client, db):
    response = client.get(reverse("login"))
    content = response.content.decode()
    assert response.status_code == 200
    assert "Username" in content and "Password" in content


@pytest.mark.django_db
def test_instance_settings_admin_only_and_masks_secrets(mfa_session, client, workspace, settings):
    settings.GOOGLE_CLIENT_ID = "1234567890-abcdef.apps.googleusercontent.com"
    settings.GOOGLE_CLIENT_SECRET = "super-secret-value"  # noqa: S105
    organization, _, _, _ = workspace
    response = mfa_session.get("/api/instance-settings")
    assert response.status_code == 200
    rows = {row["key"]: row["value"] for group in response.json() for row in group["rows"]}
    values = set(rows.values())
    assert "super-secret-value" not in values
    assert "1234567890-abcdef.apps.googleusercontent.com" not in values
    assert rows["GOOGLE_CLIENT_ID"] == "1234…om"
    assert "GOOGLE_REDIRECT_URI" in rows
    assert "SOURCE_NETWORK_ENABLED" in rows

    _login_role(client, organization, Membership.Role.ANALYST, "settings-analyst")
    denied = client.get("/api/instance-settings")
    assert denied.status_code == 403
    assert denied.json()["error"]["code"] == "forbidden"


@pytest.mark.django_db
def test_instance_setting_edit_encrypts_and_overrides(mfa_session, client, workspace):
    from foundry.models import InstanceSetting
    from foundry.runtime_settings import runtime_setting

    organization, _, _, _ = workspace
    response = mfa_session.put(
        "/api/instance-settings/GOOGLE_CLIENT_SECRET",
        data={"value": "ui-entered-secret"},
        content_type="application/json",
    )
    assert response.status_code == 200
    assert response.json() == {"key": "GOOGLE_CLIENT_SECRET", "state": "updated"}
    row = InstanceSetting.objects.get(key="GOOGLE_CLIENT_SECRET")
    assert "ui-entered-secret" not in row.encrypted_value
    assert runtime_setting("GOOGLE_CLIENT_SECRET") == "ui-entered-secret"

    listing = mfa_session.get("/api/instance-settings").content.decode()
    assert "ui-entered-secret" not in listing

    # Policy gates stay environment-only: not editable from the interface.
    gate = mfa_session.put(
        "/api/instance-settings/SOURCE_NETWORK_ENABLED",
        data={"value": "true"},
        content_type="application/json",
    )
    assert gate.status_code == 404
    assert not InstanceSetting.objects.filter(key="SOURCE_NETWORK_ENABLED").exists()

    cleared = mfa_session.put(
        "/api/instance-settings/GOOGLE_CLIENT_SECRET",
        data={"value": ""},
        content_type="application/json",
    )
    assert cleared.status_code == 200
    assert cleared.json()["state"] == "cleared"
    assert not InstanceSetting.objects.filter(key="GOOGLE_CLIENT_SECRET").exists()

    _login_role(client, organization, Membership.Role.ANALYST, "settings-editor")
    denied = client.put(
        "/api/instance-settings/GOOGLE_CLIENT_ID",
        data={"value": "x"},
        content_type="application/json",
    )
    assert denied.status_code == 403
