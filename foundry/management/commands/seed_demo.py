from __future__ import annotations

import argparse

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from foundry.models import MailboxConnection, Membership, Organization
from foundry.pipeline import ingest_rfc822

DEMO_MESSAGES = [
    b"From: Aylin Kaya <aylin@example.test>\r\n"
    b"To: sales@midvex.test\r\nDate: Mon, 7 Apr 2025 09:10:00 +0300\r\n"
    b"Message-ID: <demo-quote@example.test>\r\nSubject: Request for a quotation\r\n\r\n"
    b"Could you send pricing for the sample product? We would like to follow up next week.\r\n",
    b"From: newsletter@example.test\r\nTo: sales@midvex.test\r\n"
    b"Date: Tue, 8 Apr 2025 09:10:00 +0300\r\nMessage-ID: <demo-spam@example.test>\r\n"
    b"Subject: Newsletter\r\nX-Spam-Flag: YES\r\n\r\nThis message must be quarantined.\r\n",
]


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
        mailbox, _ = MailboxConnection.objects.get_or_create(
            organization=organization,
            provider="synthetic",
            email_address="sales@midvex.test",
            defaults={"status": MailboxConnection.Status.PAUSED, "scopes": []},
        )
        for index, raw in enumerate(DEMO_MESSAGES, start=1):
            ingest_rfc822(mailbox, f"demo-{index}", raw, provider_thread_id=f"demo-thread-{index}")
        self.stdout.write(
            self.style.SUCCESS("Synthetic demo data created. Set the user's password separately.")
        )
