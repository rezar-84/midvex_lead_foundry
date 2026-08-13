from __future__ import annotations

from datetime import datetime
from typing import Any, cast
from uuid import UUID

from django.conf import settings
from django.contrib.auth.models import User
from django.db import IntegrityError, transaction
from django.db.models import QuerySet
from django.forms import Form, ModelForm
from django.http import HttpRequest
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.text import slugify
from ninja import Body, Router, Schema
from ninja.errors import HttpError
from pydantic import Field

from ...audit import record_event
from ...forms import LeadProjectForm, LeadSourceForm, ProductForm, TagForm
from ...models import (
    BatchJob,
    BatchJobItem,
    Contact,
    ContactMetric,
    EnrichmentResult,
    EntityRelationship,
    EntityTag,
    LeadProject,
    LeadSource,
    Membership,
    Organization,
    ProductConcept,
    ProjectEntity,
    Tag,
)
from ...tasks import run_entity_analysis, run_entity_enrichment, run_source_sync
from ..errors import FormValidationError
from ..pagination import paginate_queryset
from ..security import require_membership

router = Router()


# --- helpers -----------------------------------------------------------------


def _validated(form: Form | ModelForm) -> None:  # type: ignore[type-arg]
    if not form.is_valid():
        raise FormValidationError(
            {name: [str(error) for error in errors] for name, errors in form.errors.items()}
        )


def _project_for(membership: Membership, project_id: str) -> LeadProject:
    return get_object_or_404(LeadProject, id=project_id, organization=membership.organization)


def _unique_slug(organization: Organization, name: str) -> str:
    base = slugify(name)[:80] or "project"
    candidate = base
    index = 2
    while LeadProject.objects.filter(organization=organization, slug=candidate).exists():
        candidate = f"{base[:75]}-{index}"
        index += 1
    return candidate


def _create_job(
    request: HttpRequest,
    project: LeadProject,
    kind: str,
    target_key: str,
    *,
    source: LeadSource | None = None,
    budget: int = 0,
) -> BatchJob:
    membership = request.membership  # type: ignore[attr-defined]
    try:
        with transaction.atomic():
            return BatchJob.objects.create(
                organization=membership.organization,
                project=project,
                source=source,
                kind=kind,
                target_key=target_key,
                request_budget=budget,
                created_by=cast(User, request.user),
            )
    except IntegrityError as exc:
        raise HttpError(409, "An active job already exists for this operation.") from exc


def _project_contact_queryset(project: LeadProject) -> QuerySet[Contact]:
    ids = ProjectEntity.objects.filter(project=project, entity_type="contact").values_list(
        "entity_id", flat=True
    )
    return (
        Contact.objects.filter(organization=project.organization, id__in=ids)
        .select_related("company")
        .order_by("display_name", "primary_email")
    )


# --- schemas -----------------------------------------------------------------


class PageMeta(Schema):
    count: int
    page: int
    pages: int
    per_page: int


class ProjectOut(Schema):
    id: str
    name: str
    slug: str
    purpose: str
    status: str
    languages: list[str]
    retention_days: int
    monthly_request_budget: int
    allowed_domains: list[str]
    network_execution_enabled: bool
    auto_digest_enabled: bool
    updated_at: datetime


class SourceOut(Schema):
    id: str
    source_type: str
    name: str
    email_address: str
    host: str
    port: int | None
    username: str
    use_tls: bool
    rate_limit_per_minute: int
    max_messages_per_run: int
    status: str
    last_synced_at: datetime | None
    last_error_code: str
    has_password: bool
    mailbox_connected: bool


class JobOut(Schema):
    id: str
    kind: str
    status: str
    status_display: str
    processed: int
    total: int
    percent: int
    error_count: int
    requests_used: int
    request_budget: int
    error_code: str
    terminal: bool
    target_key: str
    source_id: str | None
    created_at: datetime
    finished_at: datetime | None


class JobPageOut(PageMeta):
    items: list[JobOut]


class ProjectDetailOut(ProjectOut):
    entity_counts: dict[str, int]
    sources: list[SourceOut]
    jobs: list[JobOut]


class TagOut(Schema):
    id: str
    name: str
    category: str
    color: str


class MetricOut(Schema):
    contact_count: int
    inbound_count: int
    outbound_count: int
    first_contact_at: datetime | None
    last_contact_at: datetime | None
    quality_score: float | None
    sentiment: str
    latest_outcome: str
    main_topics: list[str]


class ProductRefOut(Schema):
    id: str
    canonical_name: str
    relationship_type: str


class ContactRowOut(Schema):
    id: str
    display_name: str
    primary_email: str
    phone: str
    company_name: str | None
    metric: MetricOut | None
    products: list[ProductRefOut]
    tags: list[TagOut]


class ContactPageOut(PageMeta):
    items: list[ContactRowOut]


class EnrichmentResultOut(Schema):
    id: str
    source_url: str
    status: str
    candidate_data: dict[str, Any]
    created_at: datetime


class ContactDetailOut(ContactRowOut):
    enrichment_results: list[EnrichmentResultOut]


class ProductOut(Schema):
    id: str
    canonical_name: str
    aliases: list[str]
    product_group: str
    description: str
    status: str


class ProductPageOut(PageMeta):
    items: list[ProductOut]


class TagAssignIn(Schema):
    contact_ids: list[UUID] = Field(min_length=1)
    tag_id: UUID


class EnrichmentStartIn(Schema):
    contact_ids: list[UUID] = Field(min_length=1)
    request_budget: int = Field(default=25, ge=1, le=1000)
    confirm_scope: bool


class EnrichmentReviewIn(Schema):
    decision: str


# --- serializers -------------------------------------------------------------


def _project_out(project: LeadProject) -> ProjectOut:
    return ProjectOut(
        id=str(project.id),
        name=project.name,
        slug=project.slug,
        purpose=project.purpose,
        status=project.status,
        languages=[str(code) for code in project.languages],
        retention_days=project.retention_days,
        monthly_request_budget=project.monthly_request_budget,
        allowed_domains=[str(domain) for domain in project.allowed_domains],
        network_execution_enabled=project.network_execution_enabled,
        auto_digest_enabled=project.auto_digest_enabled,
        updated_at=project.updated_at,
    )


def _source_out(source: LeadSource) -> SourceOut:
    return SourceOut(
        id=str(source.id),
        source_type=source.source_type,
        name=source.name,
        email_address=source.email_address,
        host=source.host,
        port=source.port,
        username=source.username,
        use_tls=source.use_tls,
        rate_limit_per_minute=source.rate_limit_per_minute,
        max_messages_per_run=source.max_messages_per_run,
        status=source.status,
        last_synced_at=source.last_synced_at,
        last_error_code=source.last_error_code,
        has_password=bool(source.encrypted_password),
        mailbox_connected=source.mailbox_id is not None,
    )


def _job_out(job: BatchJob) -> JobOut:
    return JobOut(
        id=str(job.id),
        kind=job.kind,
        status=job.status,
        status_display=job.get_status_display(),
        processed=job.progress_processed,
        total=job.progress_total,
        percent=job.progress_percent,
        error_count=job.error_count,
        requests_used=job.requests_used,
        request_budget=job.request_budget,
        error_code=job.error_code,
        terminal=job.is_terminal,
        target_key=job.target_key,
        source_id=str(job.source_id) if job.source_id else None,
        created_at=job.created_at,
        finished_at=job.finished_at,
    )


def _metric_out(metric: ContactMetric | None) -> MetricOut | None:
    if metric is None:
        return None
    return MetricOut(
        contact_count=metric.contact_count,
        inbound_count=metric.inbound_count,
        outbound_count=metric.outbound_count,
        first_contact_at=metric.first_contact_at,
        last_contact_at=metric.last_contact_at,
        quality_score=float(metric.quality_score) if metric.quality_score is not None else None,
        sentiment=metric.sentiment,
        latest_outcome=metric.latest_outcome,
        main_topics=[str(topic) for topic in metric.main_topics],
    )


def _tag_out(tag: Tag) -> TagOut:
    return TagOut(id=str(tag.id), name=tag.name, category=tag.category, color=tag.color)


def _contact_row(
    contact: Contact,
    metric: ContactMetric | None,
    products: list[tuple[str, ProductConcept]],
    tags: list[Tag],
) -> ContactRowOut:
    return ContactRowOut(
        id=str(contact.id),
        display_name=contact.display_name,
        primary_email=contact.primary_email,
        phone=contact.phone,
        company_name=contact.company.name if contact.company else None,
        metric=_metric_out(metric),
        products=[
            ProductRefOut(
                id=str(product.id),
                canonical_name=product.canonical_name,
                relationship_type=relationship_type,
            )
            for relationship_type, product in products
        ],
        tags=[_tag_out(tag) for tag in tags],
    )


# --- projects ----------------------------------------------------------------


@router.get("/projects", response=list[ProjectOut], url_name="project_list")
def project_list(request: HttpRequest) -> list[ProjectOut]:
    membership = require_membership(request, "view")
    projects = LeadProject.objects.filter(organization=membership.organization).order_by(
        "-updated_at"
    )
    return [_project_out(project) for project in projects]


@router.post("/projects", response=ProjectOut, url_name="project_create")
def project_create(request: HttpRequest, payload: Body[dict[str, Any]]) -> ProjectOut:
    membership = require_membership(request, "manage_projects")
    form = LeadProjectForm(payload)
    _validated(form)
    project = form.save(commit=False)
    project.organization = membership.organization
    project.slug = _unique_slug(membership.organization, project.name)
    project.save()
    record_event(
        request,
        membership.organization,
        "project.created",
        object_type="lead_project",
        object_id=str(project.id),
    )
    return _project_out(project)


@router.get("/projects/{project_id}", response=ProjectDetailOut, url_name="project_detail")
def project_detail(request: HttpRequest, project_id: str) -> ProjectDetailOut:
    membership = require_membership(request, "view")
    project = _project_for(membership, project_id)
    base = _project_out(project)
    return ProjectDetailOut(
        **base.model_dump(),
        entity_counts={
            kind: ProjectEntity.objects.filter(project=project, entity_type=kind).count()
            for kind in ("contact", "company", "product", "opportunity")
        },
        sources=[_source_out(source) for source in project.sources.order_by("name")],
        jobs=[_job_out(job) for job in project.jobs.order_by("-created_at")[:8]],
    )


@router.patch("/projects/{project_id}", response=ProjectOut, url_name="project_settings")
def project_update(
    request: HttpRequest, project_id: str, payload: Body[dict[str, Any]]
) -> ProjectOut:
    membership = require_membership(request, "manage_projects")
    project = _project_for(membership, project_id)
    form = LeadProjectForm(payload, instance=project)
    _validated(form)
    form.save()
    return _project_out(project)


# --- sources -----------------------------------------------------------------


@router.get("/projects/{project_id}/sources", response=list[SourceOut], url_name="project_sources")
def source_list(request: HttpRequest, project_id: str) -> list[SourceOut]:
    membership = require_membership(request, "view")
    project = _project_for(membership, project_id)
    return [_source_out(source) for source in project.sources.order_by("name")]


class SourceCreateOut(Schema):
    source: SourceOut
    job_id: str | None


@router.post(
    "/projects/{project_id}/sources", response=SourceCreateOut, url_name="project_source_create"
)
def source_create(
    request: HttpRequest, project_id: str, payload: Body[dict[str, Any]]
) -> SourceCreateOut:
    membership = require_membership(request, "manage_sources")
    project = _project_for(membership, project_id)
    instance = LeadSource(project=project, organization=membership.organization)
    form = LeadSourceForm(payload, instance=instance)
    _validated(form)
    source = form.save(commit=False)
    source.project = project
    source.organization = membership.organization
    source.status = (
        LeadSource.Status.DRAFT
        if source.source_type == LeadSource.SourceType.GMAIL
        else LeadSource.Status.READY
    )
    source.full_clean()
    source.save()
    record_event(
        request,
        membership.organization,
        "lead_source.created",
        object_type="lead_source",
        object_id=str(source.id),
        metadata={"source_type": source.source_type},
    )
    job_id: str | None = None
    should_start = source.source_type == LeadSource.SourceType.SYNTHETIC or (
        settings.SOURCE_NETWORK_ENABLED
        and project.network_execution_enabled
        and source.source_type in {LeadSource.SourceType.IMAP, LeadSource.SourceType.POP3}
    )
    if should_start:
        job = _create_job(request, project, BatchJob.Kind.SYNC, str(source.id), source=source)
        run_source_sync.delay(str(job.id))
        job_id = str(job.id)
    return SourceCreateOut(source=_source_out(source), job_id=job_id)


@router.get(
    "/projects/{project_id}/sources/{source_id}",
    response=SourceOut,
    url_name="project_source_detail",
)
def source_detail(request: HttpRequest, project_id: str, source_id: str) -> SourceOut:
    membership = require_membership(request, "view")
    project = _project_for(membership, project_id)
    source = get_object_or_404(LeadSource, project=project, id=source_id)
    return _source_out(source)


@router.patch(
    "/projects/{project_id}/sources/{source_id}",
    response=SourceOut,
    url_name="project_source_edit",
)
def source_update(
    request: HttpRequest, project_id: str, source_id: str, payload: Body[dict[str, Any]]
) -> SourceOut:
    membership = require_membership(request, "manage_sources")
    project = _project_for(membership, project_id)
    source = get_object_or_404(LeadSource, project=project, id=source_id)
    form = LeadSourceForm(payload, instance=source)
    _validated(form)
    updated = form.save(commit=False)
    updated.full_clean()
    updated.save()
    return _source_out(updated)


@router.post(
    "/projects/{project_id}/sources/{source_id}/sync",
    response=JobOut,
    url_name="project_source_sync",
)
def source_sync(request: HttpRequest, project_id: str, source_id: str) -> JobOut:
    membership = require_membership(request, "manage_sources")
    project = _project_for(membership, project_id)
    source = get_object_or_404(LeadSource, project=project, id=source_id)
    job = _create_job(request, project, BatchJob.Kind.SYNC, str(source.id), source=source)
    run_source_sync.delay(str(job.id))
    return _job_out(job)


# --- jobs --------------------------------------------------------------------


@router.post("/projects/{project_id}/analysis/start", response=JobOut, url_name="analysis_start")
def analysis_start(request: HttpRequest, project_id: str) -> JobOut:
    membership = require_membership(request, "run_batches")
    project = _project_for(membership, project_id)
    job = _create_job(request, project, BatchJob.Kind.ANALYZE, "project")
    run_entity_analysis.delay(str(job.id))
    return _job_out(job)


@router.get("/projects/{project_id}/jobs", response=JobPageOut, url_name="project_jobs")
def job_list(request: HttpRequest, project_id: str, page: int = 1) -> JobPageOut:
    membership = require_membership(request, "view")
    project = _project_for(membership, project_id)
    objects, meta = paginate_queryset(project.jobs.order_by("-created_at"), page, per_page=25)
    return JobPageOut(items=[_job_out(job) for job in objects], **meta)


@router.get("/projects/{project_id}/jobs/{job_id}", response=JobOut, url_name="project_job_detail")
def job_detail(request: HttpRequest, project_id: str, job_id: str) -> JobOut:
    membership = require_membership(request, "view")
    project = _project_for(membership, project_id)
    job = get_object_or_404(BatchJob, project=project, id=job_id)
    return _job_out(job)


@router.post(
    "/projects/{project_id}/jobs/{job_id}/cancel", response=JobOut, url_name="project_job_cancel"
)
def job_cancel(request: HttpRequest, project_id: str, job_id: str) -> JobOut:
    membership = require_membership(request, "run_batches")
    project = _project_for(membership, project_id)
    job = get_object_or_404(BatchJob, project=project, id=job_id)
    cancelled = BatchJob.objects.filter(
        id=job.id, status__in=[BatchJob.Status.QUEUED, BatchJob.Status.RUNNING]
    ).update(status=BatchJob.Status.CANCELLED, finished_at=timezone.now())
    if not cancelled:
        raise HttpError(409, "Only queued or running jobs can be cancelled.")
    record_event(
        request,
        project.organization,
        "batch_job.cancelled",
        object_type="batch_job",
        object_id=str(job.id),
    )
    job.refresh_from_db()
    return _job_out(job)


# --- contacts ----------------------------------------------------------------


@router.get("/projects/{project_id}/contacts", response=ContactPageOut, url_name="project_contacts")
def project_contacts(request: HttpRequest, project_id: str, page: int = 1) -> ContactPageOut:
    membership = require_membership(request, "view")
    project = _project_for(membership, project_id)
    objects, meta = paginate_queryset(_project_contact_queryset(project), page, per_page=50)
    contacts = cast(list[Contact], objects)
    metrics = {
        metric.contact_id: metric
        for metric in ContactMetric.objects.filter(project=project, contact__in=contacts)
    }
    products = {
        item.id: item
        for item in ProductConcept.objects.filter(
            organization=project.organization,
            id__in=EntityRelationship.objects.filter(
                project=project, source_type="contact", target_type="product"
            ).values_list("target_id", flat=True),
        )
    }
    relationships: dict[object, list[tuple[str, ProductConcept]]] = {}
    for relation in EntityRelationship.objects.filter(
        project=project, source_type="contact", target_type="product"
    ):
        product = products.get(relation.target_id)
        if product:
            relationships.setdefault(relation.source_id, []).append(
                (relation.relationship_type, product)
            )
    entity_tags: dict[object, list[Tag]] = {}
    for assignment in EntityTag.objects.filter(
        tag__project=project,
        entity_type="contact",
        entity_id__in=[contact.id for contact in contacts],
    ).select_related("tag"):
        entity_tags.setdefault(assignment.entity_id, []).append(assignment.tag)
    return ContactPageOut(
        items=[
            _contact_row(
                contact,
                metrics.get(contact.id),
                relationships.get(contact.id, []),
                entity_tags.get(contact.id, []),
            )
            for contact in contacts
        ],
        **meta,
    )


@router.get(
    "/projects/{project_id}/contacts/{contact_id}",
    response=ContactDetailOut,
    url_name="project_contact_detail",
)
def contact_detail(request: HttpRequest, project_id: str, contact_id: str) -> ContactDetailOut:
    membership = require_membership(request, "view")
    project = _project_for(membership, project_id)
    project_contact_ids = ProjectEntity.objects.filter(
        project=project, entity_type="contact"
    ).values("entity_id")
    contact = get_object_or_404(
        Contact.objects.select_related("company"),
        id=contact_id,
        organization=project.organization,
        id__in=project_contact_ids,
    )
    metric = ContactMetric.objects.filter(project=project, contact=contact).first()
    products = list(
        ProductConcept.objects.filter(
            organization=project.organization,
            id__in=EntityRelationship.objects.filter(
                project=project,
                source_type="contact",
                source_id=contact.id,
                target_type="product",
            ).values_list("target_id", flat=True),
        )
    )
    tags = list(
        Tag.objects.filter(
            project=project,
            assignments__entity_type="contact",
            assignments__entity_id=contact.id,
        )
    )
    row = _contact_row(
        contact,
        metric,
        [("mentions", product) for product in products],
        tags,
    )
    results = EnrichmentResult.objects.filter(
        project=project,
        job_item__entity_type="contact",
        job_item__entity_id=contact.id,
    ).order_by("-created_at")
    return ContactDetailOut(
        **row.model_dump(),
        enrichment_results=[
            EnrichmentResultOut(
                id=str(result.id),
                source_url=result.source_url,
                status=result.status,
                candidate_data=dict(result.candidate_data),
                created_at=result.created_at,
            )
            for result in results
        ],
    )


@router.post(
    "/projects/{project_id}/contacts/tags/assign",
    response=dict[str, int],
    url_name="project_contact_tag_assign",
)
def contact_tag_assign(
    request: HttpRequest, project_id: str, payload: TagAssignIn
) -> dict[str, int]:
    membership = require_membership(request, "run_batches")
    project = _project_for(membership, project_id)
    tag = get_object_or_404(Tag, project=project, id=payload.tag_id)
    valid_ids = set(
        _project_contact_queryset(project)
        .filter(id__in=payload.contact_ids)
        .values_list("id", flat=True)
    )
    if not valid_ids:
        raise FormValidationError({"contact_ids": ["No valid project contacts selected."]})
    assigned = 0
    for contact_id in valid_ids:
        _, created = EntityTag.objects.get_or_create(
            organization=project.organization,
            tag=tag,
            entity_type="contact",
            entity_id=contact_id,
        )
        assigned += int(created)
    return {"assigned": assigned}


# --- enrichment --------------------------------------------------------------


@router.post(
    "/projects/{project_id}/enrichment/start", response=JobOut, url_name="project_enrichment_start"
)
def enrichment_start(request: HttpRequest, project_id: str, payload: EnrichmentStartIn) -> JobOut:
    membership = require_membership(request, "run_enrichment")
    project = _project_for(membership, project_id)
    if not payload.confirm_scope:
        raise FormValidationError(
            {"confirm_scope": ["Confirm the approved-domains scope before starting."]}
        )
    valid_ids = list(
        _project_contact_queryset(project)
        .filter(id__in=payload.contact_ids)
        .values_list("id", flat=True)
    )
    if not valid_ids:
        raise FormValidationError({"contact_ids": ["No valid project contacts selected."]})
    job = _create_job(
        request, project, BatchJob.Kind.ENRICH, "contacts", budget=payload.request_budget
    )
    BatchJobItem.objects.bulk_create(
        [
            BatchJobItem(
                organization=project.organization,
                job=job,
                entity_type="contact",
                entity_id=contact_id,
            )
            for contact_id in valid_ids
        ]
    )
    run_entity_enrichment.delay(str(job.id))
    return _job_out(job)


@router.post(
    "/projects/{project_id}/enrichment/{result_id}/review",
    response=EnrichmentResultOut,
    url_name="project_enrichment_review",
)
def enrichment_review(
    request: HttpRequest, project_id: str, result_id: str, payload: EnrichmentReviewIn
) -> EnrichmentResultOut:
    membership = require_membership(request, "review")
    project = _project_for(membership, project_id)
    result = get_object_or_404(EnrichmentResult, project=project, id=result_id)
    if payload.decision not in {"accepted", "rejected"}:
        raise FormValidationError({"decision": ["Choose accept or reject."]})
    result.status = payload.decision
    result.save(update_fields=["status", "updated_at"])
    record_event(
        request,
        project.organization,
        "enrichment.reviewed",
        object_type="enrichment_result",
        object_id=str(result.id),
        metadata={"decision": payload.decision},
    )
    return EnrichmentResultOut(
        id=str(result.id),
        source_url=result.source_url,
        status=result.status,
        candidate_data=dict(result.candidate_data),
        created_at=result.created_at,
    )


# --- tags & products ---------------------------------------------------------


@router.get("/projects/{project_id}/tags", response=list[TagOut], url_name="project_tags")
def tag_list(request: HttpRequest, project_id: str) -> list[TagOut]:
    membership = require_membership(request, "view")
    project = _project_for(membership, project_id)
    return [_tag_out(tag) for tag in project.tags.order_by("category", "name")]


@router.post("/projects/{project_id}/tags", response=TagOut, url_name="project_tag_create")
def tag_create(request: HttpRequest, project_id: str, payload: Body[dict[str, Any]]) -> TagOut:
    membership = require_membership(request, "run_batches")
    project = _project_for(membership, project_id)
    form = TagForm(payload)
    _validated(form)
    tag = cast(Tag, form.save(commit=False))
    tag.organization = project.organization
    tag.project = project
    tag.save()
    return _tag_out(tag)


@router.get("/projects/{project_id}/products", response=ProductPageOut, url_name="project_products")
def product_list(request: HttpRequest, project_id: str, page: int = 1) -> ProductPageOut:
    membership = require_membership(request, "view")
    project = _project_for(membership, project_id)
    ids = ProjectEntity.objects.filter(project=project, entity_type="product").values_list(
        "entity_id", flat=True
    )
    products = ProductConcept.objects.filter(
        organization=project.organization, id__in=ids
    ).order_by("canonical_name")
    objects, meta = paginate_queryset(products, page, per_page=24)
    return ProductPageOut(
        items=[
            ProductOut(
                id=str(product.id),
                canonical_name=product.canonical_name,
                aliases=[str(alias) for alias in product.aliases],
                product_group=product.product_group,
                description=product.description,
                status=product.status,
            )
            for product in objects
        ],
        **meta,
    )


@router.post(
    "/projects/{project_id}/products", response=ProductOut, url_name="project_product_create"
)
def product_create(
    request: HttpRequest, project_id: str, payload: Body[dict[str, Any]]
) -> ProductOut:
    membership = require_membership(request, "run_batches")
    project = _project_for(membership, project_id)
    form = ProductForm(payload)
    _validated(form)
    product = form.save(commit=False)
    product.organization = project.organization
    product.save()
    ProjectEntity.objects.get_or_create(
        organization=project.organization,
        project=project,
        entity_type="product",
        entity_id=product.id,
        defaults={"review_status": "accepted"},
    )
    return ProductOut(
        id=str(product.id),
        canonical_name=product.canonical_name,
        aliases=[str(alias) for alias in product.aliases],
        product_group=product.product_group,
        description=product.description,
        status=product.status,
    )
