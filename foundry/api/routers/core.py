from __future__ import annotations

from django.conf import settings
from django.http import HttpRequest
from ninja import Router, Schema

from ...runtime_settings import runtime_setting
from ..security import require_membership

router = Router()


class OrganizationOut(Schema):
    id: str
    name: str
    retention_days: int | None


class FlagsOut(Schema):
    gmail_real_data_enabled: bool
    source_network_enabled: bool
    enrichment_network_enabled: bool


class MeOut(Schema):
    username: str
    role: str
    capabilities: list[str]
    organization: OrganizationOut
    brand_name: str
    flags: FlagsOut


@router.get("/me", response=MeOut, url_name="me")
def me(request: HttpRequest) -> MeOut:
    membership = require_membership(request, "view")
    from ...access import CAPABILITIES

    organization = membership.organization
    return MeOut(
        username=membership.user.get_username(),
        role=membership.role,
        capabilities=sorted(CAPABILITIES.get(membership.role, frozenset())),
        organization=OrganizationOut(
            id=str(organization.id),
            name=organization.name,
            retention_days=organization.retention_days,
        ),
        brand_name=runtime_setting("FOUNDRY_BRAND_NAME"),
        flags=FlagsOut(
            gmail_real_data_enabled=bool(settings.GMAIL_REAL_DATA_ENABLED),
            source_network_enabled=bool(settings.SOURCE_NETWORK_ENABLED),
            enrichment_network_enabled=bool(settings.ENRICHMENT_NETWORK_ENABLED),
        ),
    )
