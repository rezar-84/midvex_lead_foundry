from __future__ import annotations

import csv
import hashlib
import io
import json
import uuid

from django.contrib.auth.models import User
from django.db import transaction

from .models import ExportBatch, ExportRecord, OpportunityCandidate, Organization

CSV_FIELDS = [
    "candidate_id",
    "title",
    "status",
    "score",
    "reason",
    "last_communication_at",
    "evidence_message_id",
    "conversation_id",
]


@transaction.atomic
def accepted_candidates_csv(organization: Organization, user: User) -> tuple[ExportBatch, str]:
    candidates = list(
        OpportunityCandidate.objects.filter(
            organization=organization, status=OpportunityCandidate.Status.ACCEPTED
        )
        .select_related("evidence_message")
        .order_by("created_at", "id")
    )
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=CSV_FIELDS)
    writer.writeheader()
    rows: list[dict[str, str]] = []
    for candidate in candidates:
        row = {
            "candidate_id": str(candidate.id),
            "title": candidate.title,
            "status": candidate.status,
            "score": str(candidate.score or ""),
            "reason": candidate.reason,
            "last_communication_at": candidate.last_communication_at.isoformat()
            if candidate.last_communication_at
            else "",
            "evidence_message_id": str(candidate.evidence_message_id),
            "conversation_id": str(candidate.conversation_id),
        }
        rows.append(row)
        writer.writerow(row)
    content = output.getvalue()
    manifest = hashlib.sha256(json.dumps(rows, sort_keys=True).encode()).hexdigest()
    batch = ExportBatch.objects.create(
        organization=organization,
        created_by=user,
        idempotency_key=str(uuid.uuid4()),
        manifest_sha256=manifest,
        record_count=len(rows),
    )
    ExportRecord.objects.bulk_create(
        [
            ExportRecord(organization=organization, batch=batch, candidate=candidate, payload=row)
            for candidate, row in zip(candidates, rows, strict=True)
        ]
    )
    return batch, content
