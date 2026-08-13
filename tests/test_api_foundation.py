"""MVX-030: API foundation — auth behaviour, /api/me, and SPA catch-all ordering."""

from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.urls import resolve

from foundry.models import Membership, MFADevice


@pytest.mark.django_db
def test_api_me_requires_authentication(client):
    response = client.get("/api/me")
    assert response.status_code == 401
    assert response.headers["Content-Type"].startswith("application/json")


@pytest.mark.django_db
def test_api_returns_mfa_required_json_instead_of_redirect(client, workspace):
    _, user, _, _ = workspace
    client.force_login(user)
    response = client.get("/api/me")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "mfa_required"


@pytest.mark.django_db
def test_api_mfa_required_when_device_unverified(client, workspace):
    _, user, _, _ = workspace
    MFADevice.objects.create(
        user=user,
        encrypted_secret="test",  # noqa: S106
        confirmed_at="2026-01-01T00:00:00Z",
    )
    client.force_login(user)  # no mfa_verified in session
    response = client.get("/api/me")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "mfa_required"


@pytest.mark.django_db
def test_api_me_returns_membership_payload(mfa_session, workspace):
    organization, user, membership, _ = workspace
    response = mfa_session.get("/api/me")
    assert response.status_code == 200
    payload = response.json()
    assert payload["username"] == user.username
    assert payload["role"] == Membership.Role.ADMIN
    assert "review" in payload["capabilities"]
    assert payload["organization"]["id"] == str(organization.id)
    assert payload["organization"]["name"] == organization.name
    assert set(payload["flags"]) == {
        "gmail_real_data_enabled",
        "source_network_enabled",
        "enrichment_network_enabled",
    }


@pytest.mark.django_db
def test_api_me_denied_without_membership(client, db):
    user = get_user_model().objects.create_user(
        username="orphan",
        password="a-strong-test-password",  # noqa: S106
    )
    MFADevice.objects.create(
        user=user,
        encrypted_secret="test",  # noqa: S106
        confirmed_at="2026-01-01T00:00:00Z",
    )
    client.force_login(user)
    session = client.session
    session["mfa_verified"] = True
    session.save()
    response = client.get("/api/me")
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden"


def test_spa_catch_all_does_not_shadow_real_routes():
    # These must keep resolving to their Django views, never to the SPA.
    assert resolve("/health/").view_name == "health"
    assert resolve("/admin/").view_name == "admin:index"
    assert resolve("/exports/csv/").view_name == "export_csv"
    assert resolve("/accounts/login/").view_name == "login"
    assert resolve("/api/me").view_name == "api:me"


def test_unknown_paths_resolve_to_spa():
    assert resolve("/some/future/spa/route").view_name == "spa_index"


@pytest.mark.django_db
def test_spa_index_serves_html_or_build_missing_notice(mfa_session):
    response = mfa_session.get("/some/future/spa/route")
    assert response.status_code in (200, 501)
