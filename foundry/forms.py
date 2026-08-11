from __future__ import annotations

from typing import Any, cast

from django import forms
from django.conf import settings

from .crypto import encrypt
from .models import LeadProject, LeadSource, OpportunityCandidate, ProductConcept, Tag


class MFAForm(forms.Form):
    code = forms.RegexField(regex=r"^\d{6}$", max_length=6, label="Authentication code")


class ReviewDecisionForm(forms.Form):
    decision = forms.ChoiceField(
        choices=[
            (OpportunityCandidate.Status.ACCEPTED, "Accept"),
            (OpportunityCandidate.Status.REJECTED, "Reject"),
            (OpportunityCandidate.Status.DEFERRED, "Defer"),
        ]
    )
    note = forms.CharField(widget=forms.Textarea, required=False, max_length=2000)


class SourceConnectForm(forms.Form):
    confirm_authority = forms.BooleanField(label="I am authorised to process this mailbox")
    confirm_retention = forms.BooleanField(label="The organisation retention policy applies")


class LeadProjectForm(forms.ModelForm):  # type: ignore[type-arg]
    languages = forms.MultipleChoiceField(
        choices=settings.LANGUAGES,
        widget=forms.CheckboxSelectMultiple,
        initial=[code for code, _ in settings.LANGUAGES],
    )
    allowed_domains_text = forms.CharField(
        required=False,
        label="Approved enrichment domains",
        help_text="One public domain per line. Network enrichment remains disabled by policy.",
        widget=forms.Textarea(attrs={"rows": 4, "placeholder": "example.com"}),
    )

    class Meta:
        model = LeadProject
        fields = [
            "name",
            "purpose",
            "status",
            "languages",
            "retention_days",
            "monthly_request_budget",
            "allowed_domains_text",
            "network_execution_enabled",
        ]
        widgets = {"purpose": forms.Textarea(attrs={"rows": 4})}

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        network_field = self.fields["network_execution_enabled"]
        network_field.disabled = not (
            settings.SOURCE_NETWORK_ENABLED or settings.ENRICHMENT_NETWORK_ENABLED
        )
        network_field.help_text = (
            "Requires approved deployment feature flags. Keep disabled for synthetic testing."
        )
        if self.instance.pk:
            self.fields["allowed_domains_text"].initial = "\n".join(self.instance.allowed_domains)

    def clean_allowed_domains_text(self) -> str:
        value = str(self.cleaned_data["allowed_domains_text"])
        domains = []
        for line in value.splitlines():
            domain = line.strip().lower().rstrip(".")
            if not domain:
                continue
            if "://" in domain or "/" in domain or " " in domain or "." not in domain:
                raise forms.ValidationError("Enter domains only, one per line.")
            domains.append(domain)
        self.cleaned_data["allowed_domains"] = sorted(set(domains))
        return value

    def save(self, commit: bool = True) -> LeadProject:
        instance = cast(LeadProject, super().save(commit=False))
        instance.allowed_domains = self.cleaned_data.get("allowed_domains", [])
        if commit:
            instance.save()
        return instance


class LeadSourceForm(forms.ModelForm):  # type: ignore[type-arg]
    password = forms.CharField(
        required=False,
        widget=forms.PasswordInput(render_value=False),
        help_text="Encrypted at rest and never shown again. Not used for Gmail OAuth.",
    )
    confirm_authority = forms.BooleanField(
        label="I am authorised to configure and process this source"
    )

    class Meta:
        model = LeadSource
        fields = [
            "source_type",
            "name",
            "email_address",
            "host",
            "port",
            "username",
            "password",
            "use_tls",
            "rate_limit_per_minute",
            "max_messages_per_run",
            "confirm_authority",
        ]
        widgets = {
            "source_type": forms.Select(attrs={"data-source-type": "true"}),
            "host": forms.TextInput(attrs={"data-protocol-field": "true"}),
            "port": forms.NumberInput(attrs={"data-protocol-field": "true"}),
            "username": forms.TextInput(attrs={"data-protocol-field": "true"}),
        }

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        if not self.instance._state.adding:
            self.fields["source_type"].disabled = True

    def clean(self) -> dict[str, object]:
        cleaned = super().clean() or {}
        source_type = cleaned.get("source_type")
        if not cleaned.get("email_address"):
            self.add_error("email_address", "The mailbox address is required.")
        if source_type in {LeadSource.SourceType.IMAP, LeadSource.SourceType.POP3}:
            if not cleaned.get("password") and not self.instance.encrypted_password:
                self.add_error("password", "A password or application password is required.")
            if not cleaned.get("use_tls"):
                self.add_error("use_tls", "TLS is mandatory for IMAP and POP3.")
        return cleaned

    def save(self, commit: bool = True) -> LeadSource:
        instance = cast(LeadSource, super().save(commit=False))
        password = self.cleaned_data.get("password")
        if password:
            instance.encrypted_password = encrypt(str(password))
        if commit:
            instance.full_clean(exclude=["organization", "project"])
            instance.save()
        return instance


class ProductForm(forms.ModelForm):  # type: ignore[type-arg]
    aliases_text = forms.CharField(required=False, label="Aliases", help_text="One per line")

    class Meta:
        model = ProductConcept
        fields = ["canonical_name", "aliases_text", "product_group", "description", "status"]

    def save(self, commit: bool = True) -> ProductConcept:
        instance = cast(ProductConcept, super().save(commit=False))
        instance.aliases = [
            line.strip() for line in self.cleaned_data["aliases_text"].splitlines() if line.strip()
        ]
        if commit:
            instance.save()
        return instance


class TagForm(forms.ModelForm):  # type: ignore[type-arg]
    color = forms.RegexField(regex=r"^#[0-9A-Fa-f]{6}$", initial="#466653")

    class Meta:
        model = Tag
        fields = ["name", "category", "color"]
        widgets = {"color": forms.TextInput(attrs={"type": "color"})}


class TagAssignmentForm(forms.Form):
    contact_ids = forms.MultipleChoiceField()
    tag_id = forms.ChoiceField()

    def __init__(
        self,
        *args: Any,
        contacts: list[tuple[str, str]],
        tags: list[tuple[str, str]],
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        cast(forms.MultipleChoiceField, self.fields["contact_ids"]).choices = contacts
        cast(forms.ChoiceField, self.fields["tag_id"]).choices = tags


class EnrichmentBatchForm(forms.Form):
    contact_ids = forms.MultipleChoiceField(widget=forms.CheckboxSelectMultiple)
    request_budget = forms.IntegerField(min_value=1, max_value=1000, initial=25)
    confirm_scope = forms.BooleanField(
        label="Use only the approved project domains and public pages"
    )

    def __init__(self, *args: Any, contacts: list[tuple[str, str]], **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        cast(forms.MultipleChoiceField, self.fields["contact_ids"]).choices = contacts
