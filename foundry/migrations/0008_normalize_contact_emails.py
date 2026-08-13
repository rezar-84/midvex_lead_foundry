"""MVX-035 data cleaning: normalize legacy contact emails and names.

Rows whose lowercased email would collide with an existing contact in the same
organization are left unchanged — the dedup job's exact pass merges those.
"""

from django.db import migrations


def normalize_contacts(apps, schema_editor):
    Contact = apps.get_model("foundry", "Contact")
    for contact in Contact.objects.exclude(primary_email=""):
        email = contact.primary_email.strip().lower()
        name = " ".join(contact.display_name.split())
        updates = []
        if email != contact.primary_email:
            collision = (
                Contact.objects.filter(
                    organization_id=contact.organization_id, primary_email=email
                )
                .exclude(pk=contact.pk)
                .exists()
            )
            if not collision:
                contact.primary_email = email
                updates.append("primary_email")
        if name != contact.display_name:
            contact.display_name = name
            updates.append("display_name")
        if updates:
            contact.save(update_fields=updates)


class Migration(migrations.Migration):
    dependencies = [
        ("foundry", "0007_alter_batchjob_kind_mergesuggestion"),
    ]

    operations = [
        migrations.RunPython(normalize_contacts, migrations.RunPython.noop),
    ]
