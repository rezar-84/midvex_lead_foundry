from django.conf import settings
from django.http import HttpRequest

from .access import CAPABILITIES, membership_for


def active_membership(request: HttpRequest) -> dict[str, object]:
    membership = membership_for(request)
    capabilities = CAPABILITIES.get(membership.role, frozenset()) if membership else frozenset()
    return {
        "active_membership": membership,
        "capabilities": capabilities,
        "brand_name": settings.FOUNDRY_BRAND_NAME,
    }
