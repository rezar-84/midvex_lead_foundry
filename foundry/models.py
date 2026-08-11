from __future__ import annotations

import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q


class TimestampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Organization(TimestampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=80, unique=True)
    retention_days = models.PositiveIntegerField(null=True, blank=True)
    internal_addresses = models.JSONField(default=list, blank=True)
    internal_domains = models.JSONField(default=list, blank=True)

    def __str__(self) -> str:
        return self.name


class Membership(TimestampedModel):
    class Role(models.TextChoices):
        ADMIN = "admin", "Admin"
        ANALYST = "analyst", "Analyst"
        REVIEWER = "reviewer", "Reviewer"
        EXPORTER = "exporter", "Exporter"

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    role = models.CharField(max_length=16, choices=Role.choices)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["organization", "user"], name="one_membership_per_org")
        ]


class MFADevice(TimestampedModel):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    encrypted_secret = models.TextField()
    confirmed_at = models.DateTimeField(null=True, blank=True)
    last_counter = models.BigIntegerField(default=-1)


class OrganizationOwnedModel(TimestampedModel):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)

    class Meta:
        abstract = True


class MailboxConnection(OrganizationOwnedModel):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        ACTIVE = "active", "Active"
        PAUSED = "paused", "Paused"
        REVOKED = "revoked", "Revoked"
        ERROR = "error", "Error"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    provider = models.CharField(max_length=32, default="gmail")
    email_address = models.EmailField()
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.DRAFT)
    encrypted_refresh_token = models.TextField(blank=True)
    scopes = models.JSONField(default=list)
    history_cursor = models.CharField(max_length=200, blank=True)
    last_synced_at = models.DateTimeField(null=True, blank=True)
    last_error_code = models.CharField(max_length=80, blank=True)
    policy_confirmed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "provider", "email_address"], name="unique_mailbox"
            )
        ]

    def clean(self) -> None:
        if self.status == self.Status.ACTIVE and not self.organization.retention_days:
            raise ValidationError("A retention policy is required before activation.")


class SyncRun(OrganizationOwnedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    mailbox = models.ForeignKey(MailboxConnection, on_delete=models.CASCADE)
    status = models.CharField(max_length=24, default="queued")
    cursor_started = models.CharField(max_length=200, blank=True)
    cursor_finished = models.CharField(max_length=200, blank=True)
    processed_count = models.PositiveIntegerField(default=0)
    error_count = models.PositiveIntegerField(default=0)
    finished_at = models.DateTimeField(null=True, blank=True)


class SourceMessage(OrganizationOwnedModel):
    class Safety(models.TextChoices):
        PENDING = "pending", "Pending"
        CLEAN = "clean", "Clean"
        QUARANTINED = "quarantined", "Quarantined"
        ERROR = "error", "Error"

    class Direction(models.TextChoices):
        INBOUND = "inbound", "Inbound"
        OUTBOUND = "outbound", "Outbound"
        INTERNAL = "internal", "Internal"
        UNKNOWN = "unknown", "Unknown"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    mailbox = models.ForeignKey(MailboxConnection, on_delete=models.CASCADE)
    provider_message_id = models.CharField(max_length=255)
    provider_thread_id = models.CharField(max_length=255, blank=True)
    internet_message_id = models.CharField(max_length=998, blank=True)
    subject = models.CharField(max_length=998, blank=True)
    sender = models.JSONField(default=dict)
    recipients = models.JSONField(default=list)
    sent_at = models.DateTimeField(null=True, blank=True)
    received_at = models.DateTimeField(null=True, blank=True)
    labels = models.JSONField(default=list)
    raw_object_key = models.CharField(max_length=1024)
    raw_sha256 = models.CharField(max_length=64)
    body_text = models.TextField(blank=True)
    snippet = models.CharField(max_length=500, blank=True)
    safety_status = models.CharField(max_length=16, choices=Safety.choices, default=Safety.PENDING)
    direction = models.CharField(
        max_length=16, choices=Direction.choices, default=Direction.UNKNOWN
    )
    deleted_at_source = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["mailbox", "provider_message_id"], name="unique_provider_message"
            ),
        ]
        indexes = [
            models.Index(fields=["organization", "sent_at"]),
            models.Index(fields=["organization", "safety_status"]),
        ]


class Attachment(OrganizationOwnedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    message = models.ForeignKey(SourceMessage, on_delete=models.CASCADE, related_name="attachments")
    filename = models.CharField(max_length=500, blank=True)
    declared_content_type = models.CharField(max_length=255, blank=True)
    detected_content_type = models.CharField(max_length=255, blank=True)
    size_bytes = models.PositiveBigIntegerField()
    sha256 = models.CharField(max_length=64)
    object_key = models.CharField(max_length=1024)
    scan_status = models.CharField(max_length=24, default="pending")
    extracted_text = models.TextField(blank=True)


class SpamAssessment(OrganizationOwnedModel):
    message = models.OneToOneField(
        SourceMessage, on_delete=models.CASCADE, related_name="spam_assessment"
    )
    source = models.CharField(max_length=32)
    score = models.DecimalField(max_digits=8, decimal_places=3, null=True, blank=True)
    required_score = models.DecimalField(max_digits=8, decimal_places=3, null=True, blank=True)
    action = models.CharField(max_length=32)
    symbols = models.JSONField(default=dict)
    overridden_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL
    )
    overridden_at = models.DateTimeField(null=True, blank=True)


class Conversation(OrganizationOwnedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    source_key = models.CharField(max_length=500)
    subject = models.CharField(max_length=998, blank=True)
    last_message_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "source_key"], name="unique_conversation"
            )
        ]


class ConversationMessage(OrganizationOwnedModel):
    conversation = models.ForeignKey(
        Conversation, on_delete=models.CASCADE, related_name="conversation_messages"
    )
    message = models.OneToOneField(SourceMessage, on_delete=models.CASCADE)

    def clean(self) -> None:
        if (
            len(
                {
                    self.organization_id,
                    self.conversation.organization_id,
                    self.message.organization_id,
                }
            )
            != 1
        ):
            raise ValidationError("Cross-organization conversation links are forbidden.")


class Company(OrganizationOwnedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=300)
    domain = models.CharField(max_length=253, blank=True)
    website = models.URLField(blank=True)
    status = models.CharField(max_length=24, default="candidate")

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "domain"],
                condition=~Q(domain=""),
                name="unique_company_domain_per_org",
            )
        ]


class Contact(OrganizationOwnedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    display_name = models.CharField(max_length=300, blank=True)
    primary_email = models.EmailField(blank=True)
    phone = models.CharField(max_length=64, blank=True)
    company = models.ForeignKey(
        Company, null=True, blank=True, on_delete=models.SET_NULL, related_name="contacts"
    )
    status = models.CharField(max_length=24, default="candidate")

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "primary_email"],
                condition=~Q(primary_email=""),
                name="unique_contact_email_per_org",
            )
        ]


class ProductConcept(OrganizationOwnedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    canonical_name = models.CharField(max_length=300)
    aliases = models.JSONField(default=list)
    status = models.CharField(max_length=24, default="candidate")

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "canonical_name"], name="unique_product_name"
            )
        ]


class Interaction(OrganizationOwnedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(
        Conversation, on_delete=models.CASCADE, related_name="interactions"
    )
    interaction_type = models.CharField(max_length=48)
    occurred_at = models.DateTimeField(null=True, blank=True)
    summary = models.TextField(blank=True)
    confidence = models.DecimalField(max_digits=5, decimal_places=4, null=True, blank=True)


class ModelRun(OrganizationOwnedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    provider = models.CharField(max_length=100)
    model = models.CharField(max_length=200)
    prompt_version = models.CharField(max_length=64)
    schema_version = models.CharField(max_length=64)
    input_sha256 = models.CharField(max_length=64)
    status = models.CharField(max_length=24)
    input_tokens = models.PositiveIntegerField(null=True, blank=True)
    output_tokens = models.PositiveIntegerField(null=True, blank=True)
    error_code = models.CharField(max_length=80, blank=True)


class DerivedFact(OrganizationOwnedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    subject_type = models.CharField(max_length=48)
    subject_id = models.UUIDField()
    predicate = models.CharField(max_length=100)
    value = models.JSONField()
    confidence = models.DecimalField(max_digits=5, decimal_places=4, null=True, blank=True)
    model_run = models.ForeignKey(ModelRun, null=True, blank=True, on_delete=models.PROTECT)
    status = models.CharField(max_length=24, default="candidate")


class EvidenceCitation(OrganizationOwnedModel):
    fact = models.ForeignKey(
        DerivedFact, null=True, blank=True, on_delete=models.CASCADE, related_name="evidence"
    )
    message = models.ForeignKey(SourceMessage, on_delete=models.PROTECT)
    locator = models.CharField(max_length=500)
    excerpt = models.TextField(blank=True)
    excerpt_sha256 = models.CharField(max_length=64)

    def clean(self) -> None:
        organization_ids = {self.organization_id, self.message.organization_id}
        if self.fact is not None:
            organization_ids.add(self.fact.organization_id)
        if len(organization_ids) != 1:
            raise ValidationError("Cross-organization evidence links are forbidden.")


class OpportunityCandidate(OrganizationOwnedModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        ACCEPTED = "accepted", "Accepted"
        REJECTED = "rejected", "Rejected"
        DEFERRED = "deferred", "Deferred"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(
        Conversation, on_delete=models.CASCADE, related_name="opportunities"
    )
    rule_code = models.CharField(max_length=80)
    title = models.CharField(max_length=300)
    reason = models.TextField()
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    score = models.DecimalField(max_digits=6, decimal_places=3, null=True, blank=True)
    confidence = models.DecimalField(max_digits=5, decimal_places=4, null=True, blank=True)
    last_communication_at = models.DateTimeField(null=True, blank=True)
    evidence_message = models.ForeignKey(SourceMessage, on_delete=models.PROTECT)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "conversation", "rule_code"], name="unique_opportunity_rule"
            )
        ]


class ReviewDecision(OrganizationOwnedModel):
    candidate = models.ForeignKey(
        OpportunityCandidate, on_delete=models.CASCADE, related_name="decisions"
    )
    reviewer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    decision = models.CharField(max_length=16, choices=OpportunityCandidate.Status.choices)
    note = models.TextField(blank=True)

    def clean(self) -> None:
        if self.organization_id != self.candidate.organization_id:
            raise ValidationError("Cross-organization review links are forbidden.")


class Digest(OrganizationOwnedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=300)
    generated_at = models.DateTimeField(auto_now_add=True)
    criteria = models.JSONField(default=dict)
    candidate_ids = models.JSONField(default=list)


class ResearchArtifact(OrganizationOwnedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    subject_type = models.CharField(max_length=48)
    subject_id = models.UUIDField()
    source_url = models.URLField(max_length=2048)
    fetched_at = models.DateTimeField()
    content_sha256 = models.CharField(max_length=64)
    extracted = models.JSONField(default=dict)
    status = models.CharField(max_length=24, default="candidate")


class ExportBatch(OrganizationOwnedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    schema_version = models.CharField(max_length=32, default="csv-v1")
    idempotency_key = models.CharField(max_length=100)
    manifest_sha256 = models.CharField(max_length=64, blank=True)
    record_count = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "idempotency_key"], name="unique_export_key"
            )
        ]


class ExportRecord(OrganizationOwnedModel):
    batch = models.ForeignKey(ExportBatch, on_delete=models.CASCADE, related_name="records")
    candidate = models.ForeignKey(OpportunityCandidate, on_delete=models.PROTECT)
    payload = models.JSONField()

    def clean(self) -> None:
        if (
            len({self.organization_id, self.batch.organization_id, self.candidate.organization_id})
            != 1
        ):
            raise ValidationError("Cross-organization export links are forbidden.")


class AuditEvent(OrganizationOwnedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL
    )
    event_type = models.CharField(max_length=80)
    object_type = models.CharField(max_length=80, blank=True)
    object_id = models.CharField(max_length=100, blank=True)
    metadata = models.JSONField(default=dict)
    occurred_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["organization", "occurred_at"])]
