from __future__ import annotations

from django.http import HttpRequest

from .models import AuditEvent, Organization


def record_event(
    request: HttpRequest,
    organization: Organization,
    event_type: str,
    *,
    object_type: str = "",
    object_id: str = "",
    metadata: dict[str, object] | None = None,
) -> AuditEvent:
    safe_metadata = {
        key: value
        for key, value in (metadata or {}).items()
        if key not in {"body", "token", "secret"}
    }
    return AuditEvent.objects.create(
        organization=organization,
        actor=request.user if request.user.is_authenticated else None,
        event_type=event_type,
        object_type=object_type,
        object_id=object_id,
        metadata=safe_metadata,
    )
