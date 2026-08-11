from __future__ import annotations

import argparse

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from foundry.models import BatchJob, LeadProject, LeadSource, Membership, Organization
from foundry.operations import execute_analysis_job, execute_sync_job


class Command(BaseCommand):
    help = "Create a local synthetic workspace without real personal data."

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("--username", default="demo")

    def handle(self, *args: object, **options: object) -> None:
        organization, _ = Organization.objects.get_or_create(
            slug="midvex-demo",
            defaults={
                "name": "Midvex Demo",
                "retention_days": 30,
                "internal_addresses": ["sales@midvex.test"],
                "internal_domains": ["midvex.test"],
            },
        )
        user_model = get_user_model()
        user, created = user_model.objects.get_or_create(username=options["username"])
        if created:
            user.set_unusable_password()
            user.save(update_fields=["password"])
        Membership.objects.update_or_create(
            organization=organization,
            user=user,
            defaults={"role": Membership.Role.ADMIN, "is_active": True},
        )
        project, _ = LeadProject.objects.get_or_create(
            organization=organization,
            slug="archive-recovery-demo",
            defaults={
                "name": "Archive recovery demo",
                "purpose": (
                    "Evaluate evidence-linked opportunity recovery using synthetic messages only."
                ),
                "status": LeadProject.Status.ACTIVE,
                "languages": ["en", "tr"],
                "retention_days": 30,
                "monthly_request_budget": 100,
                "allowed_domains": ["example.test"],
            },
        )
        source, _ = LeadSource.objects.get_or_create(
            organization=organization,
            project=project,
            name="Synthetic mailbox",
            defaults={
                "source_type": LeadSource.SourceType.SYNTHETIC,
                "email_address": "sales@midvex.test",
                "status": LeadSource.Status.READY,
                "rate_limit_per_minute": 60,
                "max_messages_per_run": 50,
            },
        )
        sync_job = BatchJob.objects.create(
            organization=organization,
            project=project,
            source=source,
            kind=BatchJob.Kind.SYNC,
            target_key=str(source.id),
            created_by=user,
        )
        execute_sync_job(str(sync_job.id))
        analysis_job = BatchJob.objects.create(
            organization=organization,
            project=project,
            kind=BatchJob.Kind.ANALYZE,
            target_key="project",
            created_by=user,
        )
        execute_analysis_job(str(analysis_job.id))
        self.stdout.write(
            self.style.SUCCESS("Synthetic demo data created. Set the user's password separately.")
        )
