from __future__ import annotations

from dataclasses import dataclass

from django.conf import settings

from .crypto import decrypt, encrypt


@dataclass(frozen=True)
class EditableKey:
    label: str
    group: str
    secret: bool = False


# Keys an admin may override from the UI. Deliberately excluded: the policy
# gates (human-approval surface per AGENTS §9), SECRET_KEY, TOKEN_ENCRYPTION_KEY
# and infrastructure URLs — those stay environment-only.
EDITABLE_KEYS: dict[str, EditableKey] = {
    "FOUNDRY_BRAND_NAME": EditableKey("Brand name", "Branding & locale"),
    "FOUNDRY_USER_AGENT": EditableKey("Enrichment user-agent", "Branding & locale"),
    "GOOGLE_CLIENT_ID": EditableKey("Client ID", "Google OAuth (Gmail read-only)"),
    "GOOGLE_CLIENT_SECRET": EditableKey(
        "Client secret", "Google OAuth (Gmail read-only)", secret=True
    ),
    "GOOGLE_REDIRECT_URI": EditableKey("Redirect URI", "Google OAuth (Gmail read-only)"),
    "ENRICHMENT_EGRESS_PROXY": EditableKey(
        "Enrichment egress proxy", "Policy gates (human approval required to enable)", secret=True
    ),
}


def runtime_setting(key: str) -> str:
    """DB override if present, otherwise the environment-provided setting."""
    from .models import InstanceSetting

    if key in EDITABLE_KEYS:
        row = InstanceSetting.objects.filter(key=key).first()
        if row is not None:
            return decrypt(row.encrypted_value) if row.encrypted_value else ""
    return str(getattr(settings, key, ""))


def set_runtime_setting(key: str, value: str) -> None:
    from .models import InstanceSetting

    if key not in EDITABLE_KEYS:
        raise ValueError(f"'{key}' is not editable at runtime")
    if value:
        InstanceSetting.objects.update_or_create(
            key=key, defaults={"encrypted_value": encrypt(value)}
        )
    else:
        InstanceSetting.objects.filter(key=key).delete()
