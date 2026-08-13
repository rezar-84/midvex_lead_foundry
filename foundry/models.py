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
    product_group = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)
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
    """Reserved for MVX-006: provenance record for AI-assisted runs. No writer yet."""

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
    """Reserved for MVX-006: scheduled candidate digests. No writer yet."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=300)
    generated_at = models.DateTimeField(auto_now_add=True)
    criteria = models.JSONField(default=dict)
    candidate_ids = models.JSONField(default=list)


class ResearchArtifact(OrganizationOwnedModel):
    """Reserved for MVX-011: metered public-web research artifacts. No writer yet."""

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


class LeadProject(OrganizationOwnedModel):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        ACTIVE = "active", "Active"
        PAUSED = "paused", "Paused"
        ARCHIVED = "archived", "Archived"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=100)
    purpose = models.TextField(max_length=2000)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.DRAFT)
    languages = models.JSONField(default=list)
    retention_days = models.PositiveIntegerField()
    monthly_request_budget = models.PositiveIntegerField(default=1000)
    allowed_domains = models.JSONField(default=list, blank=True)
    network_execution_enabled = models.BooleanField(default=False)
    auto_digest_enabled = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "slug"], name="unique_project_slug_per_org"
            )
        ]

    def __str__(self) -> str:
        return self.name


class LeadSource(OrganizationOwnedModel):
    class SourceType(models.TextChoices):
        GMAIL = "gmail", "Gmail"
        IMAP = "imap", "IMAP"
        POP3 = "pop3", "POP3"
        SYNTHETIC = "synthetic", "Synthetic fixture"

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        READY = "ready", "Ready"
        SYNCING = "syncing", "Syncing"
        PAUSED = "paused", "Paused"
        ERROR = "error", "Error"
        REVOKED = "revoked", "Revoked"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(LeadProject, on_delete=models.CASCADE, related_name="sources")
    mailbox = models.OneToOneField(
        MailboxConnection,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="lead_source",
    )
    source_type = models.CharField(max_length=16, choices=SourceType.choices)
    name = models.CharField(max_length=200)
    email_address = models.EmailField(blank=True)
    host = models.CharField(max_length=253, blank=True)
    port = models.PositiveIntegerField(null=True, blank=True)
    username = models.CharField(max_length=320, blank=True)
    encrypted_password = models.TextField(blank=True)
    use_tls = models.BooleanField(default=True)
    rate_limit_per_minute = models.PositiveIntegerField(default=60)
    max_messages_per_run = models.PositiveIntegerField(default=500)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.DRAFT)
    sync_cursor = models.CharField(max_length=500, blank=True)
    last_synced_at = models.DateTimeField(null=True, blank=True)
    last_error_code = models.CharField(max_length=100, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["project", "name"], name="unique_source_name_per_project"
            )
        ]

    def clean(self) -> None:
        if self.organization_id != self.project.organization_id:
            raise ValidationError("Cross-organization project source is forbidden.")
        if self.source_type in {self.SourceType.IMAP, self.SourceType.POP3}:
            if not self.use_tls:
                raise ValidationError("IMAP and POP3 sources require TLS.")
            if not self.host or not self.port or not self.username:
                raise ValidationError("Host, port and username are required.")
            expected_port = 993 if self.source_type == self.SourceType.IMAP else 995
            if self.port != expected_port:
                raise ValidationError(f"Use the standard implicit-TLS port {expected_port}.")
        if not 1 <= self.rate_limit_per_minute <= 600:
            raise ValidationError("Rate limit must be between 1 and 600 requests per minute.")

    @property
    def has_stored_credential(self) -> bool:
        return bool(
            self.encrypted_password or (self.mailbox and self.mailbox.encrypted_refresh_token)
        )


class BatchJob(OrganizationOwnedModel):
    class Kind(models.TextChoices):
        SYNC = "sync", "Source sync"
        ANALYZE = "analyze", "Entity analysis"
        ENRICH = "enrich", "Entity enrichment"
        DEDUP = "dedup", "Contact deduplication"

    class Status(models.TextChoices):
        QUEUED = "queued", "Queued"
        RUNNING = "running", "Running"
        SUCCEEDED = "succeeded", "Succeeded"
        PARTIAL = "partial", "Partial"
        FAILED = "failed", "Failed"
        BLOCKED = "blocked", "Blocked"
        CANCELLED = "cancelled", "Cancelled"

    TERMINAL_STATUSES = frozenset(
        {
            Status.SUCCEEDED,
            Status.PARTIAL,
            Status.FAILED,
            Status.BLOCKED,
            Status.CANCELLED,
        }
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(LeadProject, on_delete=models.CASCADE, related_name="jobs")
    source = models.ForeignKey(
        LeadSource, null=True, blank=True, on_delete=models.CASCADE, related_name="jobs"
    )
    kind = models.CharField(max_length=16, choices=Kind.choices)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.QUEUED)
    target_key = models.CharField(max_length=200, default="project")
    progress_total = models.PositiveIntegerField(default=0)
    progress_processed = models.PositiveIntegerField(default=0)
    error_count = models.PositiveIntegerField(default=0)
    request_budget = models.PositiveIntegerField(default=0)
    requests_used = models.PositiveIntegerField(default=0)
    # rate_limit_remaining is written at sync start but not yet consumed;
    # configuration is rendered on the job detail page but nothing writes it.
    # Both are reserved for MVX-010 (adapter matrices); removal is MVX-022.
    rate_limit_remaining = models.PositiveIntegerField(null=True, blank=True)
    configuration = models.JSONField(default=dict, blank=True)
    error_code = models.CharField(max_length=100, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["project", "kind", "target_key"],
                condition=Q(status__in=["queued", "running"]),
                name="one_active_job_per_target",
            )
        ]
        indexes = [models.Index(fields=["organization", "project", "created_at"])]

    @property
    def progress_percent(self) -> int:
        if not self.progress_total:
            return 0
        return min(100, round(self.progress_processed * 100 / self.progress_total))

    @property
    def is_terminal(self) -> bool:
        return self.status in self.TERMINAL_STATUSES


class BatchJobItem(OrganizationOwnedModel):
    job = models.ForeignKey(BatchJob, on_delete=models.CASCADE, related_name="items")
    entity_type = models.CharField(max_length=48)
    entity_id = models.UUIDField()
    status = models.CharField(max_length=16, default="queued")
    output = models.JSONField(default=dict, blank=True)
    error_code = models.CharField(max_length=100, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["job", "entity_type", "entity_id"], name="unique_job_entity"
            )
        ]


class ProjectEntity(OrganizationOwnedModel):
    project = models.ForeignKey(LeadProject, on_delete=models.CASCADE, related_name="entities")
    entity_type = models.CharField(max_length=48)
    entity_id = models.UUIDField()
    # review_status is written (manual products get "accepted") but not yet
    # read anywhere; the review workflow that consumes it is MVX-005.
    review_status = models.CharField(max_length=24, default="candidate")

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["project", "entity_type", "entity_id"], name="unique_project_entity"
            )
        ]


class Tag(OrganizationOwnedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(LeadProject, on_delete=models.CASCADE, related_name="tags")
    name = models.CharField(max_length=100)
    category = models.CharField(max_length=48, default="general")
    color = models.CharField(max_length=7, default="#466653")

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["project", "category", "name"], name="unique_project_tag"
            )
        ]


class EntityTag(OrganizationOwnedModel):
    tag = models.ForeignKey(Tag, on_delete=models.CASCADE, related_name="assignments")
    entity_type = models.CharField(max_length=48)
    entity_id = models.UUIDField()
    confidence = models.DecimalField(max_digits=5, decimal_places=4, null=True, blank=True)
    evidence_message = models.ForeignKey(
        SourceMessage, null=True, blank=True, on_delete=models.PROTECT
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["tag", "entity_type", "entity_id"], name="unique_entity_tag"
            )
        ]


class EntityRelationship(OrganizationOwnedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(LeadProject, on_delete=models.CASCADE, related_name="relationships")
    source_type = models.CharField(max_length=48)
    source_id = models.UUIDField()
    target_type = models.CharField(max_length=48)
    target_id = models.UUIDField()
    relationship_type = models.CharField(max_length=64)
    confidence = models.DecimalField(max_digits=5, decimal_places=4, null=True, blank=True)
    status = models.CharField(max_length=24, default="candidate")
    evidence_message = models.ForeignKey(SourceMessage, on_delete=models.PROTECT)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "project",
                    "source_type",
                    "source_id",
                    "target_type",
                    "target_id",
                    "relationship_type",
                ],
                name="unique_entity_relationship",
            )
        ]


class ContactMetric(OrganizationOwnedModel):
    project = models.ForeignKey(LeadProject, on_delete=models.CASCADE, related_name="metrics")
    contact = models.ForeignKey(Contact, on_delete=models.CASCADE, related_name="metrics")
    contact_count = models.PositiveIntegerField(default=0)
    inbound_count = models.PositiveIntegerField(default=0)
    outbound_count = models.PositiveIntegerField(default=0)
    first_contact_at = models.DateTimeField(null=True, blank=True)
    last_contact_at = models.DateTimeField(null=True, blank=True)
    frequency_days = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    main_topics = models.JSONField(default=list, blank=True)
    latest_outcome = models.CharField(max_length=100, blank=True)
    sentiment = models.CharField(max_length=24, default="unknown")
    quality_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    scoring_version = models.CharField(max_length=32, default="heuristic-v1")

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["project", "contact"], name="unique_project_contact_metric"
            )
        ]


class ExtractionProfile(OrganizationOwnedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(
        LeadProject, on_delete=models.CASCADE, related_name="extraction_profiles"
    )
    entity_type = models.CharField(max_length=48)
    version = models.PositiveIntegerField(default=1)
    field_rules = models.JSONField(default=dict)
    reviewed_success_count = models.PositiveIntegerField(default=0)
    reviewed_failure_count = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["project", "entity_type", "version"], name="unique_extraction_profile"
            )
        ]


class EnrichmentResult(OrganizationOwnedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(
        LeadProject, on_delete=models.CASCADE, related_name="enrichment_results"
    )
    job_item = models.ForeignKey(
        BatchJobItem, on_delete=models.CASCADE, related_name="enrichment_results"
    )
    source_url = models.URLField(max_length=2048)
    fetched_at = models.DateTimeField(null=True, blank=True)
    content_sha256 = models.CharField(max_length=64, blank=True)
    candidate_data = models.JSONField(default=dict)
    status = models.CharField(max_length=24, default="candidate")
    extraction_profile_version = models.PositiveIntegerField(default=1)


class InstanceSetting(TimestampedModel):
    """Admin-editable configuration override; values encrypted at rest.

    Instance-wide (no organization FK) — one deployment, one configuration
    (ADR 0009/0010). Only keys in runtime_settings.EDITABLE_KEYS are written.
    """

    key = models.CharField(max_length=64, unique=True)
    encrypted_value = models.TextField(blank=True)


class MergeSuggestion(OrganizationOwnedModel):
    """A proposed contact merge awaiting human review (MVX-035 data quality).

    Exact-match duplicates are merged automatically by the dedup job; fuzzy
    matches land here and follow the same human accept/reject pattern as
    opportunity candidates.
    """

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        ACCEPTED = "accepted", "Accepted"
        REJECTED = "rejected", "Rejected"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    primary_contact = models.ForeignKey(
        Contact, on_delete=models.CASCADE, related_name="merge_suggestions_as_primary"
    )
    duplicate_contact = models.ForeignKey(
        Contact, on_delete=models.CASCADE, related_name="merge_suggestions_as_duplicate"
    )
    reason = models.CharField(max_length=64)
    score = models.DecimalField(max_digits=5, decimal_places=4, null=True, blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL
    )
    decided_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "primary_contact", "duplicate_contact"],
                name="unique_merge_suggestion_pair",
            )
        ]
