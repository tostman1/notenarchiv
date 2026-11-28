"""Explicit revision-bound attestations, separate from opening a preview."""

from django import forms
from django.utils.translation import gettext_lazy as _


class ContentInspectionForm(forms.Form):
    fingerprint = forms.RegexField(regex=r"^[0-9a-f]{64}$", widget=forms.HiddenInput)
    visually_reviewed = forms.BooleanField(
        label=_("Ich habe jedes Vorkommen dieser gespeicherten Folge einschließlich Fortsetzungen visuell geprüft."),
        required=True,
    )


class ContentConfirmationForm(forms.Form):
    inspection_id = forms.UUIDField(widget=forms.HiddenInput)
    confirm = forms.BooleanField(
        label=_("Ich gebe genau diese geprüfte Inhaltsrevision für neue musikalische Verwendung frei."),
        required=True,
    )
