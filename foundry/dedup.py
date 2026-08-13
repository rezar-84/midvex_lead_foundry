from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Iterable

from django.db import IntegrityError, transaction

from .models import (
    AuditEvent,
    BatchJobItem,
    Contact,
    ContactMetric,
    DerivedFact,
    EntityRelationship,
    EntityTag,
    MergeSuggestion,
    Organization,
    ProjectEntity,
)

_WHITESPACE = re.compile(r"\s+")

# Fuzzy suggestions need enough signal to be worth a human's time.
MIN_NAME_LENGTH = 5


def normalize_email(value: str) -> str:
    return value.strip().lower()


def normalize_name(value: str) -> str:
    return _WHITESPACE.sub(" ", value.strip()).casefold()


def _repoint_pairs(
    model: type[ProjectEntity] | type[EntityTag] | type[BatchJobItem],
    duplicate: Contact,
    primary: Contact,
) -> None:
    """Repoint (entity_type, entity_id) rows from duplicate to primary.

    Rows whose target already exists on the primary (unique constraints) are
    deleted rather than moved.
    """
    for row in model.objects.filter(entity_type="contact", entity_id=duplicate.id):
        row.entity_id = primary.id
        try:
            with transaction.atomic():
                row.save(update_fields=["entity_id", "updated_at"])
        except IntegrityError:
            row.entity_id = duplicate.id
            row.delete()


def merge_contacts(primary: Contact, duplicate: Contact, *, reason: str = "manual") -> None:
    """Fold `duplicate` into `primary` and delete it. Audit-logged, transactional."""
    if primary.id == duplicate.id:
        return
    if primary.organization_id != duplicate.organization_id:
        raise ValueError("Contacts belong to different organizations")
    with transaction.atomic():
        changed: list[str] = []
        if not primary.display_name and duplicate.display_name:
            primary.display_name = duplicate.display_name
            changed.append("display_name")
        if not primary.phone and duplicate.phone:
            primary.phone = duplicate.phone
            changed.append("phone")
        if not primary.company_id and duplicate.company_id:
            primary.company = duplicate.company
            changed.append("company")
        if changed:
            primary.save(update_fields=[*changed, "updated_at"])

        # Metrics: repoint, folding counts where the primary already has a row.
        primary_metrics = {
            metric.project_id: metric for metric in ContactMetric.objects.filter(contact=primary)
        }
        for metric in ContactMetric.objects.filter(contact=duplicate):
            existing = primary_metrics.get(metric.project_id)
            if existing is None:
                metric.contact = primary
                metric.save(update_fields=["contact", "updated_at"])
                continue
            existing.contact_count += metric.contact_count
            existing.inbound_count += metric.inbound_count
            existing.outbound_count += metric.outbound_count
            if metric.first_contact_at and (
                existing.first_contact_at is None
                or metric.first_contact_at < existing.first_contact_at
            ):
                existing.first_contact_at = metric.first_contact_at
            if metric.last_contact_at and (
                existing.last_contact_at is None
                or metric.last_contact_at > existing.last_contact_at
            ):
                existing.last_contact_at = metric.last_contact_at
            existing.save(
                update_fields=[
                    "contact_count",
                    "inbound_count",
                    "outbound_count",
                    "first_contact_at",
                    "last_contact_at",
                    "updated_at",
                ]
            )
            metric.delete()

        DerivedFact.objects.filter(subject_type="contact", subject_id=duplicate.id).update(
            subject_id=primary.id
        )
        _repoint_pairs(ProjectEntity, duplicate, primary)
        _repoint_pairs(EntityTag, duplicate, primary)
        _repoint_pairs(BatchJobItem, duplicate, primary)
        for relation in EntityRelationship.objects.filter(
            source_type="contact", source_id=duplicate.id
        ):
            relation.source_id = primary.id
            try:
                with transaction.atomic():
                    relation.save(update_fields=["source_id", "updated_at"])
            except IntegrityError:
                relation.source_id = duplicate.id
                relation.delete()
        for relation in EntityRelationship.objects.filter(
            target_type="contact", target_id=duplicate.id
        ):
            relation.target_id = primary.id
            try:
                with transaction.atomic():
                    relation.save(update_fields=["target_id", "updated_at"])
            except IntegrityError:
                relation.target_id = duplicate.id
                relation.delete()

        MergeSuggestion.objects.filter(duplicate_contact=duplicate).exclude(
            status=MergeSuggestion.Status.PENDING
        ).delete()
        MergeSuggestion.objects.filter(primary_contact=duplicate).delete()

        AuditEvent.objects.create(
            organization=primary.organization,
            event_type="contact.merged",
            object_type="contact",
            object_id=str(primary.id),
            metadata={
                "duplicate_id": str(duplicate.id),
                "duplicate_email": duplicate.primary_email,
                "reason": reason,
                "fields_filled": changed,
            },
        )
        duplicate.delete()


def find_exact_duplicates(organization: Organization) -> list[list[Contact]]:
    """Groups of contacts sharing the same normalized non-empty email, oldest first."""
    groups: dict[str, list[Contact]] = defaultdict(list)
    for contact in Contact.objects.filter(organization=organization).order_by("created_at"):
        email = normalize_email(contact.primary_email)
        if email:
            groups[email].append(contact)
    return [group for group in groups.values() if len(group) > 1]


def find_fuzzy_pairs(organization: Organization) -> Iterable[tuple[Contact, Contact, str]]:
    """(primary, duplicate, reason) candidates that need human review."""
    contacts = list(Contact.objects.filter(organization=organization).order_by("created_at"))
    seen: set[tuple[str, str]] = set()

    by_name: dict[str, list[Contact]] = defaultdict(list)
    for contact in contacts:
        name = normalize_name(contact.display_name)
        if len(name) >= MIN_NAME_LENGTH:
            by_name[name].append(contact)
    for group in by_name.values():
        primary = group[0]
        for duplicate in group[1:]:
            if normalize_email(primary.primary_email) != normalize_email(duplicate.primary_email):
                key = (str(primary.id), str(duplicate.id))
                if key not in seen:
                    seen.add(key)
                    yield primary, duplicate, "same_name"

    by_local_part: dict[str, list[Contact]] = defaultdict(list)
    for contact in contacts:
        email = normalize_email(contact.primary_email)
        local = email.partition("@")[0]
        if len(local) >= MIN_NAME_LENGTH:
            by_local_part[local].append(contact)
    for group in by_local_part.values():
        primary = group[0]
        for duplicate in group[1:]:
            if normalize_email(primary.primary_email) != normalize_email(duplicate.primary_email):
                key = (str(primary.id), str(duplicate.id))
                if key not in seen:
                    seen.add(key)
                    yield primary, duplicate, "same_email_local_part"
