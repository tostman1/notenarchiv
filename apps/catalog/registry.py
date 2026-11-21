"""Finite management screens; neither models nor fields are request-selected."""

from dataclasses import dataclass

from django.utils.translation import gettext_lazy as _

from apps.catalog import forms
from apps.members.forms import MemberForm


@dataclass(frozen=True)
class Screen:
    title: str
    form: type
    columns: tuple
    search: tuple
    related: tuple = ()

    @property
    def model(self):
        return self.form._meta.model


SCREENS = {
    "works": Screen(
        _("Werke"),
        forms.WorkForm,
        (("title", _("Titel")), ("composer", _("Komponist/in")), ("active", _("Status"))),
        ("title_key", "composer_key", "aliases__alias_key"),
    ),
    "arrangements": Screen(
        _("Arrangements"),
        forms.ArrangementForm,
        (
            ("work", _("Werk")),
            ("arranger", _("Arrangeur/in")),
            ("edition", _("Ausgabe")),
            ("expectations_defined", _("Erwartete Besetzung")),
            ("active", _("Status")),
        ),
        ("work__title_key", "arranger_key", "edition_key"),
        ("work",),
    ),
    "instruments": Screen(
        _("Instrumente und Varianten"),
        forms.InstrumentForm,
        (
            ("name", _("Instrument")),
            ("family", _("Familie")),
            ("transposition", _("Stimmung")),
            ("get_clef_display", _("Notation")),
            ("active", _("Status")),
        ),
        ("name_key", "family_key", "transposition_key"),
    ),
    "parts": Screen(
        _("Spielbare Stimmen"),
        forms.PartForm,
        (
            ("instrument", _("Instrumentenvariante")),
            ("code", _("Stimme")),
            ("label", _("Bezeichnung")),
            ("active", _("Status")),
        ),
        ("instrument__name_key", "code_key", "label_key"),
        ("instrument",),
    ),
    "work-aliases": Screen(
        _("Werkaliasse"),
        forms.WorkAliasForm,
        (("alias", _("Alias")), ("work", _("Werk")), ("active", _("Status"))),
        ("alias_key", "work__title_key"),
        ("work",),
    ),
    "instrument-aliases": Screen(
        _("Instrumenten- und Stimmenaliasse"),
        forms.InstrumentAliasForm,
        (
            ("alias", _("Alias")),
            ("instrument", _("Instrumentenvariante")),
            ("part", _("Stimme")),
            ("active", _("Status")),
        ),
        ("alias_key", "instrument__name_key", "part__code_key"),
        ("instrument", "part__instrument"),
    ),
    "expectations": Screen(
        _("Erwartete Stimmen"),
        forms.ExpectedPartForm,
        (("arrangement", _("Arrangement")), ("part", _("Stimme")), ("required", _("Erforderlich"))),
        ("arrangement__work__title_key", "part__instrument__name_key", "part__code_key"),
        ("arrangement__work", "part__instrument"),
    ),
    "templates": Screen(
        _("Besetzungsvorlagen"), forms.TemplateForm, (("name", _("Vorlage")), ("active", _("Status"))), ("name_key",)
    ),
    "template-parts": Screen(
        _("Vorlagenstimmen"),
        forms.TemplatePartForm,
        (("template", _("Vorlage")), ("part", _("Stimme")), ("required", _("Erforderlich"))),
        ("template__name_key", "part__instrument__name_key", "part__code_key"),
        ("template", "part__instrument"),
    ),
    "members": Screen(
        _("Mitglieder"),
        MemberForm,
        (
            ("name", _("Name")),
            ("membership_id", _("Mitgliedsnummer")),
            ("regular_part", _("Stammstimme")),
            ("active", _("Status")),
        ),
        ("name_key", "membership_key", "regular_part__instrument__name_key", "regular_part__code_key"),
        ("regular_part__instrument",),
    ),
}
