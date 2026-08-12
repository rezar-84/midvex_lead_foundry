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
def test_nav_hides_tags_and_settings_from_reviewer(client, workspace):
    organization, _, _, _ = workspace
    project = create_project(organization)
    _login_role(client, organization, Membership.Role.REVIEWER, "nav-reviewer")

    response = client.get(reverse("project_contacts", args=[project.id]))
    content = response.content.decode()
    assert response.status_code == 200
    assert reverse("project_tags", args=[project.id]) not in content
    assert reverse("project_settings", args=[project.id]) not in content


@pytest.mark.django_db
def test_analyst_sees_tag_controls_but_not_enrichment(client, workspace):
    organization, _, _, _ = workspace
    project = create_project(organization)
    _add_contacts(project, 1)
    _login_role(client, organization, Membership.Role.ANALYST, "bulk-analyst")

    response = client.get(reverse("project_contacts", args=[project.id]))
    content = response.content.decode()
    assert "Assign tag" in content
    assert "Start enrichment" not in content
    assert reverse("project_tags", args=[project.id]) in content


@pytest.mark.django_db
def test_enrichment_form_error_preserves_selection(mfa_session, workspace):
    organization, _, _, _ = workspace
    project = create_project(organization)
    contacts = _add_contacts(project, 2)

    response = mfa_session.post(
        reverse("project_enrichment_start", args=[project.id]),
        {"contact_ids": [str(contacts[0].id)], "request_budget": 5},
    )
    content = response.content.decode()
    assert response.status_code == 400
    assert "This field is required." in content
    assert f'value="{contacts[0].id}"\n                     checked' in content or (
        f'value="{contacts[0].id}"' in content and "checked" in content
    )
    assert f'value="{contacts[1].id}"' in content


@pytest.mark.django_db
def test_contacts_paginate(mfa_session, workspace):
    organization, _, _, _ = workspace
    project = create_project(organization)
    _add_contacts(project, 60)

    first = mfa_session.get(reverse("project_contacts", args=[project.id]))
    second = mfa_session.get(reverse("project_contacts", args=[project.id]), {"page": 2})
    assert len(first.context["rows"]) == 50
    assert len(second.context["rows"]) == 10
    assert "Page 1 of 2" in first.content.decode()


@pytest.mark.django_db
def test_opportunities_filter_shows_active_state(mfa_session, workspace):
    response = mfa_session.get(reverse("opportunities"))
    content = response.content.decode()
    assert '?status=pending" aria-current="true"' in content
    assert '?status=accepted" aria-current="true"' not in content


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
def test_empty_states_render(mfa_session, workspace):
    organization, _, _, _ = workspace
    project = create_project(organization)
    contacts = mfa_session.get(reverse("project_contacts", args=[project.id]))
    conversations = mfa_session.get(reverse("conversations"))
    jobs = mfa_session.get(reverse("project_jobs", args=[project.id]))
    assert "No contacts yet" in contacts.content.decode()
    assert "No conversations imported" in conversations.content.decode()
    assert "No jobs have been started" in jobs.content.decode()


@pytest.mark.django_db
def test_instance_settings_admin_only_and_masks_secrets(mfa_session, client, workspace, settings):
    settings.GOOGLE_CLIENT_ID = "1234567890-abcdef.apps.googleusercontent.com"
    settings.GOOGLE_CLIENT_SECRET = "super-secret-value"  # noqa: S105
    organization, _, _, _ = workspace
    response = mfa_session.get(reverse("instance_settings"))
    content = response.content.decode()
    assert response.status_code == 200
    assert "super-secret-value" not in content
    assert "1234567890-abcdef.apps.googleusercontent.com" not in content
    assert "1234…om" in content
    assert "GOOGLE_REDIRECT_URI" in content and "SOURCE_NETWORK_ENABLED" in content

    _login_role(client, organization, Membership.Role.ANALYST, "settings-analyst")
    denied = client.get(reverse("instance_settings"))
    assert denied.status_code == 403


@pytest.mark.django_db
def test_instance_setting_edit_encrypts_and_overrides(mfa_session, client, workspace):
    from foundry.models import InstanceSetting
    from foundry.runtime_settings import runtime_setting

    organization, _, _, _ = workspace
    response = mfa_session.post(
        reverse("instance_setting_update"),
        {"key": "GOOGLE_CLIENT_SECRET", "value": "ui-entered-secret"},
    )
    assert response.status_code == 302
    row = InstanceSetting.objects.get(key="GOOGLE_CLIENT_SECRET")
    assert "ui-entered-secret" not in row.encrypted_value
    assert runtime_setting("GOOGLE_CLIENT_SECRET") == "ui-entered-secret"

    page = mfa_session.get(reverse("instance_settings")).content.decode()
    assert "ui-entered-secret" not in page

    gate = mfa_session.post(
        reverse("instance_setting_update"),
        {"key": "SOURCE_NETWORK_ENABLED", "value": "true"},
    )
    assert gate.status_code == 302
    assert not InstanceSetting.objects.filter(key="SOURCE_NETWORK_ENABLED").exists()

    mfa_session.post(
        reverse("instance_setting_update"), {"key": "GOOGLE_CLIENT_SECRET", "value": ""}
    )
    assert not InstanceSetting.objects.filter(key="GOOGLE_CLIENT_SECRET").exists()

    _login_role(client, organization, Membership.Role.ANALYST, "settings-editor")
    denied = client.post(
        reverse("instance_setting_update"), {"key": "GOOGLE_CLIENT_ID", "value": "x"}
    )
    assert denied.status_code == 403
