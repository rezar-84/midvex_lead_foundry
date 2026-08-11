from __future__ import annotations

import secrets
from typing import cast

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db import IntegrityError, transaction
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.text import slugify
from django.views.decorators.http import require_http_methods, require_POST

from .access import require_capability
from .audit import record_event
from .forms import (
    EnrichmentBatchForm,
    LeadProjectForm,
    LeadSourceForm,
    ProductForm,
    TagAssignmentForm,
    TagForm,
)
from .gmail import oauth_flow
from .models import (
    BatchJob,
    BatchJobItem,
    Contact,
    ContactMetric,
    EnrichmentResult,
    EntityRelationship,
    EntityTag,
    LeadProject,
    LeadSource,
    Organization,
    ProductConcept,
    ProjectEntity,
    Tag,
)
from .pagination import paginate
from .tasks import run_entity_analysis, run_entity_enrichment, run_source_sync


def _project(request: HttpRequest, project_id: str) -> LeadProject:
    membership = request.membership  # type: ignore[attr-defined]
    return get_object_or_404(LeadProject, id=project_id, organization=membership.organization)


def _unique_slug(organization: Organization, name: str) -> str:
    base = slugify(name)[:80] or "project"
    candidate = base
    index = 2
    while LeadProject.objects.filter(organization=organization, slug=candidate).exists():
        candidate = f"{base[:75]}-{index}"
        index += 1
    return candidate


@login_required
@require_capability("view")
def project_list(request: HttpRequest) -> HttpResponse:
    membership = request.membership  # type: ignore[attr-defined]
    projects = LeadProject.objects.filter(organization=membership.organization).order_by(
        "-updated_at"
    )
    return render(request, "foundry/projects/list.html", {"projects": projects})


@login_required
@require_capability("manage_projects")
@require_http_methods(["GET", "POST"])
def project_create(request: HttpRequest) -> HttpResponse:
    membership = request.membership  # type: ignore[attr-defined]
    form = LeadProjectForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
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
        return redirect("project_detail", project_id=project.id)
    return render(
        request, "foundry/projects/form.html", {"form": form, "heading": "Create project"}
    )


@login_required
@require_capability("view")
def project_detail(request: HttpRequest, project_id: str) -> HttpResponse:
    project = _project(request, project_id)
    entity_counts = {
        kind: ProjectEntity.objects.filter(project=project, entity_type=kind).count()
        for kind in ("contact", "company", "product", "opportunity")
    }
    return render(
        request,
        "foundry/projects/detail.html",
        {
            "project": project,
            "entity_counts": entity_counts,
            "sources": project.sources.order_by("name"),
            "jobs": project.jobs.order_by("-created_at")[:8],
            "external_sources_enabled": settings.SOURCE_NETWORK_ENABLED,
            "enrichment_enabled": settings.ENRICHMENT_NETWORK_ENABLED,
        },
    )


@login_required
@require_capability("manage_projects")
@require_http_methods(["GET", "POST"])
def project_settings(request: HttpRequest, project_id: str) -> HttpResponse:
    project = _project(request, project_id)
    form = LeadProjectForm(request.POST or None, instance=project)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Project settings saved.")
        return redirect("project_detail", project_id=project.id)
    return render(
        request,
        "foundry/projects/form.html",
        {"form": form, "heading": "Project settings", "project": project},
    )


@login_required
@require_capability("manage_sources")
@require_http_methods(["GET", "POST"])
def source_create(request: HttpRequest, project_id: str) -> HttpResponse:
    project = _project(request, project_id)
    membership = request.membership  # type: ignore[attr-defined]
    instance = LeadSource(project=project, organization=membership.organization)
    form = LeadSourceForm(request.POST or None, instance=instance)
    if request.method == "POST" and form.is_valid():
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
        should_start = source.source_type == LeadSource.SourceType.SYNTHETIC or (
            settings.SOURCE_NETWORK_ENABLED
            and project.network_execution_enabled
            and source.source_type in {LeadSource.SourceType.IMAP, LeadSource.SourceType.POP3}
        )
        if should_start:
            job = _create_job(
                request,
                project,
                BatchJob.Kind.SYNC,
                str(source.id),
                source=source,
            )
            if job:
                run_source_sync.delay(str(job.id))
                return redirect("project_job_detail", project_id=project.id, job_id=job.id)
        return redirect("project_source_detail", project_id=project.id, source_id=source.id)
    return render(request, "foundry/projects/source_form.html", {"form": form, "project": project})


@login_required
@require_capability("manage_sources")
@require_http_methods(["GET", "POST"])
def source_edit(request: HttpRequest, project_id: str, source_id: str) -> HttpResponse:
    project = _project(request, project_id)
    source = get_object_or_404(LeadSource, project=project, id=source_id)
    form = LeadSourceForm(request.POST or None, instance=source)
    if request.method == "POST" and form.is_valid():
        updated = form.save(commit=False)
        updated.full_clean()
        updated.save()
        messages.success(request, "Source configuration saved.")
        return redirect("project_source_detail", project_id=project.id, source_id=source.id)
    return render(
        request,
        "foundry/projects/source_form.html",
        {"form": form, "project": project, "source": source},
    )


@login_required
@require_capability("view")
def source_detail(request: HttpRequest, project_id: str, source_id: str) -> HttpResponse:
    project = _project(request, project_id)
    source = get_object_or_404(LeadSource, project=project, id=source_id)
    return render(
        request,
        "foundry/projects/source_detail.html",
        {
            "project": project,
            "source": source,
            "jobs": source.jobs.order_by("-created_at")[:10],
            "external_sources_enabled": settings.SOURCE_NETWORK_ENABLED,
            "gmail_enabled": settings.GMAIL_REAL_DATA_ENABLED,
        },
    )


def _create_job(
    request: HttpRequest,
    project: LeadProject,
    kind: str,
    target_key: str,
    *,
    source: LeadSource | None = None,
    budget: int = 0,
) -> BatchJob | None:
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
    except IntegrityError:
        messages.error(request, "An active job already exists for this operation.")
        return None


@login_required
@require_POST
@require_capability("manage_sources")
def source_sync(request: HttpRequest, project_id: str, source_id: str) -> HttpResponse:
    project = _project(request, project_id)
    source = get_object_or_404(LeadSource, project=project, id=source_id)
    job = _create_job(request, project, BatchJob.Kind.SYNC, str(source.id), source=source)
    if job:
        run_source_sync.delay(str(job.id))
        messages.success(request, "Sync job started.")
        return redirect("project_job_detail", project_id=project.id, job_id=job.id)
    return redirect("project_source_detail", project_id=project.id, source_id=source.id)


@login_required
@require_POST
@require_capability("manage_sources")
def source_gmail_connect(request: HttpRequest, project_id: str, source_id: str) -> HttpResponse:
    project = _project(request, project_id)
    source = get_object_or_404(
        LeadSource,
        project=project,
        id=source_id,
        source_type=LeadSource.SourceType.GMAIL,
    )
    if not settings.SOURCE_NETWORK_ENABLED or not project.network_execution_enabled:
        messages.error(request, "External source execution is disabled for this project.")
        return redirect("project_source_detail", project_id=project.id, source_id=source.id)
    state = secrets.token_urlsafe(32)
    request.session["gmail_oauth_state"] = state
    request.session["gmail_policy_confirmed"] = True
    request.session["gmail_lead_source_id"] = str(source.id)
    flow = oauth_flow(state=state)
    url, _ = flow.authorization_url(
        access_type="offline", include_granted_scopes="true", prompt="consent"
    )
    return redirect(url)


@login_required
@require_POST
@require_capability("run_batches")
def analysis_start(request: HttpRequest, project_id: str) -> HttpResponse:
    project = _project(request, project_id)
    job = _create_job(request, project, BatchJob.Kind.ANALYZE, "project")
    if job:
        run_entity_analysis.delay(str(job.id))
        messages.success(request, "Entity analysis started.")
        return redirect("project_job_detail", project_id=project.id, job_id=job.id)
    return redirect("project_detail", project_id=project.id)


@login_required
@require_capability("view")
def job_list(request: HttpRequest, project_id: str) -> HttpResponse:
    project = _project(request, project_id)
    page, querystring = paginate(request, project.jobs.order_by("-created_at"), per_page=25)
    return render(
        request,
        "foundry/projects/jobs.html",
        {
            "project": project,
            "jobs": page.object_list,
            "page_obj": page,
            "querystring": querystring,
        },
    )


@login_required
@require_capability("view")
def job_detail(request: HttpRequest, project_id: str, job_id: str) -> HttpResponse:
    project = _project(request, project_id)
    job = get_object_or_404(BatchJob, project=project, id=job_id)
    page, querystring = paginate(request, job.items.order_by("created_at"))
    return render(
        request,
        "foundry/projects/job_detail.html",
        {
            "project": project,
            "job": job,
            "items": page.object_list,
            "item_total": page.paginator.count,
            "page_obj": page,
            "querystring": querystring,
        },
    )


@login_required
@require_capability("view")
def job_status(request: HttpRequest, project_id: str, job_id: str) -> JsonResponse:
    project = _project(request, project_id)
    job = get_object_or_404(BatchJob, project=project, id=job_id)
    return JsonResponse(
        {
            "status": job.status,
            "status_display": job.get_status_display(),
            "processed": job.progress_processed,
            "total": job.progress_total,
            "percent": job.progress_percent,
            "error_count": job.error_count,
            "requests_used": job.requests_used,
            "request_budget": job.request_budget,
            "error_code": job.error_code,
            "terminal": job.is_terminal,
        }
    )


@login_required
@require_POST
@require_capability("run_batches")
def job_cancel(request: HttpRequest, project_id: str, job_id: str) -> HttpResponse:
    project = _project(request, project_id)
    job = get_object_or_404(BatchJob, project=project, id=job_id)
    cancelled = BatchJob.objects.filter(
        id=job.id, status__in=[BatchJob.Status.QUEUED, BatchJob.Status.RUNNING]
    ).update(status=BatchJob.Status.CANCELLED, finished_at=timezone.now())
    if cancelled:
        record_event(
            request,
            project.organization,
            "batch_job.cancelled",
            object_type="batch_job",
            object_id=str(job.id),
        )
        messages.success(request, "Job cancelled. A running worker stops at its next checkpoint.")
    else:
        messages.error(request, "Only queued or running jobs can be cancelled.")
    return redirect("project_job_detail", project_id=project.id, job_id=job.id)


def _project_contacts(project: LeadProject) -> list[Contact]:
    ids = ProjectEntity.objects.filter(project=project, entity_type="contact").values_list(
        "entity_id", flat=True
    )
    return list(
        Contact.objects.filter(organization=project.organization, id__in=ids)
        .select_related("company")
        .order_by("display_name", "primary_email")
    )


@login_required
@require_capability("view")
def project_contacts(request: HttpRequest, project_id: str) -> HttpResponse:
    project = _project(request, project_id)
    contacts = _project_contacts(project)
    metrics = {
        metric.contact_id: metric
        for metric in ContactMetric.objects.filter(project=project, contact__in=contacts)
    }
    relationships: dict[object, list[tuple[EntityRelationship, ProductConcept]]] = {}
    product_ids = EntityRelationship.objects.filter(
        project=project, source_type="contact", target_type="product"
    ).values_list("target_id", flat=True)
    products = {
        item.id: item
        for item in ProductConcept.objects.filter(
            organization=project.organization, id__in=product_ids
        )
    }
    for relation in EntityRelationship.objects.filter(
        project=project, source_type="contact", target_type="product"
    ):
        product = products.get(relation.target_id)
        if product:
            relationships.setdefault(relation.source_id, []).append((relation, product))
    entity_tags: dict[object, list[Tag]] = {}
    for assignment in EntityTag.objects.filter(
        tag__project=project,
        entity_type="contact",
        entity_id__in=[item.id for item in contacts],
    ).select_related("tag"):
        entity_tags.setdefault(assignment.entity_id, []).append(assignment.tag)
    rows = [
        {
            "contact": contact,
            "metric": metrics.get(contact.id),
            "relationships": relationships.get(contact.id, []),
            "tags": entity_tags.get(contact.id, []),
        }
        for contact in contacts
    ]
    form = EnrichmentBatchForm(
        contacts=[
            (str(contact.id), contact.display_name or contact.primary_email) for contact in contacts
        ]
    )
    tag_form = TagAssignmentForm(
        contacts=[
            (str(contact.id), contact.display_name or contact.primary_email) for contact in contacts
        ],
        tags=[
            (str(tag.id), f"{tag.category}: {tag.name}")
            for tag in project.tags.order_by("category", "name")
        ],
    )
    return render(
        request,
        "foundry/projects/contacts.html",
        {"project": project, "rows": rows, "form": form, "tag_form": tag_form},
    )


@login_required
@require_capability("view")
def contact_detail(request: HttpRequest, project_id: str, contact_id: str) -> HttpResponse:
    project = _project(request, project_id)
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
    product_ids = EntityRelationship.objects.filter(
        project=project,
        source_type="contact",
        source_id=contact.id,
        target_type="product",
    ).values_list("target_id", flat=True)
    products = ProductConcept.objects.filter(organization=project.organization, id__in=product_ids)
    results = EnrichmentResult.objects.filter(
        project=project,
        job_item__entity_type="contact",
        job_item__entity_id=contact.id,
    ).order_by("-created_at")
    tags = Tag.objects.filter(
        project=project,
        assignments__entity_type="contact",
        assignments__entity_id=contact.id,
    )
    return render(
        request,
        "foundry/projects/contact_detail.html",
        {
            "project": project,
            "contact": contact,
            "metric": metric,
            "products": products,
            "results": results,
            "tags": tags,
        },
    )


@login_required
@require_POST
@require_capability("review")
def enrichment_review(request: HttpRequest, project_id: str, result_id: str) -> HttpResponse:
    project = _project(request, project_id)
    result = get_object_or_404(EnrichmentResult, project=project, id=result_id)
    decision = request.POST.get("decision")
    if decision not in {"accepted", "rejected"}:
        messages.error(request, "Choose accept or reject.")
    else:
        result.status = decision
        result.save(update_fields=["status", "updated_at"])
        record_event(
            request,
            project.organization,
            "enrichment.reviewed",
            object_type="enrichment_result",
            object_id=str(result.id),
            metadata={"decision": decision},
        )
    return redirect(
        "project_contact_detail",
        project_id=project.id,
        contact_id=result.job_item.entity_id,
    )


@login_required
@require_POST
@require_capability("run_batches")
def contact_tag_assign(request: HttpRequest, project_id: str) -> HttpResponse:
    project = _project(request, project_id)
    contacts = _project_contacts(project)
    form = TagAssignmentForm(
        request.POST,
        contacts=[
            (str(contact.id), contact.display_name or contact.primary_email) for contact in contacts
        ],
        tags=[(str(tag.id), tag.name) for tag in project.tags.all()],
    )
    if not form.is_valid():
        messages.error(request, "Select contacts and a valid project tag.")
        return redirect("project_contacts", project_id=project.id)
    tag = get_object_or_404(Tag, project=project, id=form.cleaned_data["tag_id"])
    selected = set(form.cleaned_data["contact_ids"])
    for contact in contacts:
        if str(contact.id) in selected:
            EntityTag.objects.get_or_create(
                organization=project.organization,
                tag=tag,
                entity_type="contact",
                entity_id=contact.id,
            )
    messages.success(request, "Tag assigned to selected contacts.")
    return redirect("project_contacts", project_id=project.id)


@login_required
@require_capability("run_batches")
@require_http_methods(["GET", "POST"])
def project_tags(request: HttpRequest, project_id: str) -> HttpResponse:
    project = _project(request, project_id)
    form = TagForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        tag = cast(Tag, form.save(commit=False))
        tag.organization = project.organization
        tag.project = project
        tag.save()
        return redirect("project_tags", project_id=project.id)
    return render(
        request,
        "foundry/projects/tags.html",
        {
            "project": project,
            "tags": project.tags.order_by("category", "name"),
            "form": form,
        },
    )


@login_required
@require_POST
@require_capability("run_enrichment")
def enrichment_start(request: HttpRequest, project_id: str) -> HttpResponse:
    project = _project(request, project_id)
    contacts = _project_contacts(project)
    choices = [
        (str(contact.id), contact.display_name or contact.primary_email) for contact in contacts
    ]
    form = EnrichmentBatchForm(request.POST, contacts=choices)
    if not form.is_valid():
        messages.error(request, "Select valid contacts and an enrichment budget.")
        return redirect("project_contacts", project_id=project.id)
    selected = set(form.cleaned_data["contact_ids"])
    job = _create_job(
        request,
        project,
        BatchJob.Kind.ENRICH,
        "contacts",
        budget=form.cleaned_data["request_budget"],
    )
    if not job:
        return redirect("project_contacts", project_id=project.id)
    BatchJobItem.objects.bulk_create(
        [
            BatchJobItem(
                organization=project.organization,
                job=job,
                entity_type="contact",
                entity_id=contact.id,
            )
            for contact in contacts
            if str(contact.id) in selected
        ]
    )
    run_entity_enrichment.delay(str(job.id))
    return redirect("project_job_detail", project_id=project.id, job_id=job.id)


@login_required
@require_capability("view")
def project_products(request: HttpRequest, project_id: str) -> HttpResponse:
    project = _project(request, project_id)
    ids = ProjectEntity.objects.filter(project=project, entity_type="product").values_list(
        "entity_id", flat=True
    )
    products = ProductConcept.objects.filter(
        organization=project.organization, id__in=ids
    ).order_by("canonical_name")
    return render(
        request, "foundry/projects/products.html", {"project": project, "products": products}
    )


@login_required
@require_capability("run_batches")
@require_http_methods(["GET", "POST"])
def product_create(request: HttpRequest, project_id: str) -> HttpResponse:
    project = _project(request, project_id)
    form = ProductForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
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
        return redirect("project_products", project_id=project.id)
    return render(request, "foundry/projects/product_form.html", {"project": project, "form": form})
