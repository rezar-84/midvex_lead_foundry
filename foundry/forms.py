from __future__ import annotations

from django import forms

from .models import OpportunityCandidate


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
