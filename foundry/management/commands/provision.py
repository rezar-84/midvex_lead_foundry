from __future__ import annotations

import argparse
import getpass
import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.utils.text import slugify

from foundry.models import Membership, Organization


class Command(BaseCommand):
    help = (
        "Provision an organisation and its first admin account. Idempotent: "
        "re-running updates the membership but never resets an existing password. "
        "The password comes from FOUNDRY_ADMIN_PASSWORD or an interactive prompt "
        "and is never echoed."
    )

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("--org-name", required=True)
        parser.add_argument("--org-slug", default="", help="Defaults to a slug of --org-name.")
        parser.add_argument("--username", required=True)
        parser.add_argument("--email", default="")
        parser.add_argument("--retention-days", type=int, default=30)

    def handle(self, *args: object, **options: object) -> None:
        org_name = str(options["org_name"])
        org_slug = str(options["org_slug"]) or slugify(org_name)
        if not org_slug:
            raise CommandError("Provide --org-slug when --org-name has no slug characters.")
        organization, org_created = Organization.objects.get_or_create(
            slug=org_slug,
            defaults={
                "name": org_name,
                "retention_days": int(options["retention_days"]),  # type: ignore[call-overload]
            },
        )
        user_model = get_user_model()
        user, user_created = user_model.objects.get_or_create(
            username=str(options["username"]),
            defaults={"email": str(options["email"])},
        )
        if user_created or not user.has_usable_password():
            password = os.getenv("FOUNDRY_ADMIN_PASSWORD", "")
            if not password:
                password = getpass.getpass("Admin password (input hidden): ")
            if not password:
                raise CommandError(
                    "A password is required: set FOUNDRY_ADMIN_PASSWORD or enter one at the prompt."
                )
            user.set_password(password)
            user.save(update_fields=["password"])
        Membership.objects.update_or_create(
            organization=organization,
            user=user,
            defaults={"role": Membership.Role.ADMIN, "is_active": True},
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Organisation '{organization.slug}' "
                f"{'created' if org_created else 'already existed'}; "
                f"admin '{user.get_username()}' "
                f"{'created' if user_created else 'updated'}. "
                "Sign in and complete MFA enrolment next."
            )
        )
