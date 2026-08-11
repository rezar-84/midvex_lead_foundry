from __future__ import annotations

from collections.abc import Callable
from functools import wraps
from typing import Any

from django.core.exceptions import PermissionDenied
from django.http import HttpRequest, HttpResponse

from .models import Membership

CAPABILITIES: dict[str, frozenset[str]] = {
    Membership.Role.ADMIN: frozenset(
        {
            "view",
            "review",
            "export",
            "manage_sources",
            "manage_users",
            "manage_projects",
            "run_batches",
            "run_enrichment",
        }
    ),
    Membership.Role.ANALYST: frozenset({"view", "run_batches"}),
    Membership.Role.REVIEWER: frozenset({"view", "review"}),
    Membership.Role.EXPORTER: frozenset({"view", "export"}),
}


def membership_for(request: HttpRequest) -> Membership | None:
    if not request.user.is_authenticated:
        return None
    return (
        Membership.objects.select_related("organization")
        .filter(user=request.user, is_active=True)
        .order_by("created_at")
        .first()
    )


def require_capability(
    capability: str,
) -> Callable[[Callable[..., HttpResponse]], Callable[..., HttpResponse]]:
    def decorator(view: Callable[..., HttpResponse]) -> Callable[..., HttpResponse]:
        @wraps(view)
        def wrapped(request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
            membership = membership_for(request)
            if membership is None or capability not in CAPABILITIES.get(
                membership.role, frozenset()
            ):
                raise PermissionDenied
            request.membership = membership  # type: ignore[attr-defined]
            return view(request, *args, **kwargs)

        return wrapped

    return decorator
