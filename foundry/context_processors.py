from django.http import HttpRequest

from .access import CAPABILITIES, membership_for
from .runtime_settings import runtime_setting


def active_membership(request: HttpRequest) -> dict[str, object]:
    membership = membership_for(request)
    capabilities = CAPABILITIES.get(membership.role, frozenset()) if membership else frozenset()
    return {
        "active_membership": membership,
        "capabilities": capabilities,
        "brand_name": runtime_setting("FOUNDRY_BRAND_NAME"),
    }
