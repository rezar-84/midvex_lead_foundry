from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache

from django.core.exceptions import ValidationError

from .models import ExtractionProfile, LeadProject

MESSAGE_ENTITY_TYPE = "message"
MAX_PATTERN_LENGTH = 500
MAX_GROUP_PATTERNS = 32

# The shipped extraction rules. A project without an ExtractionProfile row uses
# exactly these, so upgrading the defaults upgrades every non-customised project.
DEFAULT_FIELD_RULES: dict[str, object] = {
    "product_pattern": (
        r"\b(?:for|about|regarding|interested in|ilgili)\s+(?:the\s+)?"
        r"([\wÀ-ž][\wÀ-ž -]{2,60}?(?:product|scanner|software|service|system|cihaz|ürün|yazılım))\b"
    ),
    "topics": {
        "pricing": r"\b(price|pricing|quote|quotation|fiyat|teklif)\b",
        "demo": r"\b(demo|demonstration|tanıtım)\b",
        "meeting": r"\b(meeting|call|toplantı|görüşme)\b",
        "support": r"\b(support|problem|issue|destek|sorun)\b",
    },
    "roles": {
        "buyer": r"\b(buyer|purchas(?:e|ing)|alıcı|satın alma)\b",
        "vendor": r"\b(vendor|supplier|satıcı|tedarikçi)\b",
        "manufacturer": r"\b(manufacturer|producer|üretici|imalatçı)\b",
    },
    "positive": r"\b(thank|great|approved|interested|teşekkür|onay|memnun)\b",
    "negative": r"\b(cancel|complaint|problem|reject|iptal|şikayet|sorun|ret)\b",
    "outcome": r"\b(proposal sent|approved|ordered|won|lost|teklif gönder|onay|sipariş)\b",
    "opportunity": (
        r"\b(quote|quotation|proposal|pricing|price|budget|demo|meeting|follow[ -]?up|"
        r"teklif|fiyat|bütçe|demo|toplantı|geri dönüş)\b"
    ),
    "exclusion": r"\b(unsubscribe|newsletter|receipt|fatura|bülten)\b",
}


@dataclass(frozen=True)
class CompiledProfile:
    version: int
    product_pattern: re.Pattern[str]
    topics: dict[str, re.Pattern[str]]
    roles: dict[str, re.Pattern[str]]
    positive: re.Pattern[str]
    negative: re.Pattern[str]
    outcome: re.Pattern[str]
    opportunity: re.Pattern[str]
    exclusion: re.Pattern[str]


def _compile(name: str, pattern: object) -> re.Pattern[str]:
    if not isinstance(pattern, str):
        raise ValidationError(f"Rule '{name}' must be a regular-expression string.")
    if len(pattern) > MAX_PATTERN_LENGTH:
        raise ValidationError(f"Rule '{name}' exceeds {MAX_PATTERN_LENGTH} characters.")
    try:
        return re.compile(pattern, re.IGNORECASE)
    except re.error as exc:
        raise ValidationError(f"Rule '{name}' is not a valid pattern: {exc}") from exc


def _compile_group(name: str, group: object) -> dict[str, re.Pattern[str]]:
    if not isinstance(group, dict):
        raise ValidationError(f"Rule group '{name}' must map labels to patterns.")
    if len(group) > MAX_GROUP_PATTERNS:
        raise ValidationError(f"Rule group '{name}' exceeds {MAX_GROUP_PATTERNS} entries.")
    return {str(label): _compile(f"{name}.{label}", pattern) for label, pattern in group.items()}


def compile_rules(field_rules: dict[str, object], *, version: int = 0) -> CompiledProfile:
    unknown = set(field_rules) - set(DEFAULT_FIELD_RULES)
    if unknown:
        raise ValidationError(f"Unknown rule keys: {', '.join(sorted(unknown))}")
    merged = {**DEFAULT_FIELD_RULES, **field_rules}
    return CompiledProfile(
        version=version,
        product_pattern=_compile("product_pattern", merged["product_pattern"]),
        topics=_compile_group("topics", merged["topics"]),
        roles=_compile_group("roles", merged["roles"]),
        positive=_compile("positive", merged["positive"]),
        negative=_compile("negative", merged["negative"]),
        outcome=_compile("outcome", merged["outcome"]),
        opportunity=_compile("opportunity", merged["opportunity"]),
        exclusion=_compile("exclusion", merged["exclusion"]),
    )


def validate_field_rules(field_rules: dict[str, object]) -> None:
    compile_rules(field_rules)


@lru_cache(maxsize=1)
def default_profile() -> CompiledProfile:
    return compile_rules({}, version=1)


def active_profile(project: LeadProject) -> CompiledProfile:
    record = (
        ExtractionProfile.objects.filter(project=project, entity_type=MESSAGE_ENTITY_TYPE)
        .order_by("-version")
        .first()
    )
    if record is None:
        return default_profile()
    return compile_rules(record.field_rules, version=record.version)
