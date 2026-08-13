from __future__ import annotations

from django.http import HttpRequest
from ninja.errors import HttpError

from ..access import CAPABILITIES, membership_for
from ..models import Membership


def require_membership(request: HttpRequest, capability: str) -> Membership:
    """API equivalent of ``require_capability``: resolve and attach the membership.

    Raises 403 as a JSON error instead of rendering the HTML error page.
    """
    membership = membership_for(request)
    if membership is None or capability not in CAPABILITIES.get(membership.role, frozenset()):
        raise HttpError(403, "This action needs a role with the given capability.")
    request.membership = membership  # type: ignore[attr-defined]
    return membership
