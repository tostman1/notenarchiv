"""German typed master-data forms; assignments always select real references."""

from django import forms
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from apps.catalog import models


class RecordForm(forms.ModelForm):
    expected_revision = forms.IntegerField(min_value=0, widget=forms.HiddenInput)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["expected_revision"].initial = 0 if self.instance._state.adding else self.instance.revision
        for name, field in self.fields.items():
            if isinstance(field, forms.ModelChoiceField):
                choices = field.queryset
                if choices.model is models.Part:
                    choices = choices.select_related("instrument").order_by(
                        "instrument__name_key", "instrument__transposition_key", "instrument__clef", "code_key", "pk"
                    )
                elif choices.model is models.Arrangement:
                    choices = choices.select_related("work").order_by(
                        "work__title_key", "arranger_key", "edition_key", "pk"
                    )
                else:
                    keys = list(getattr(choices.model, "normalized_fields", {}))
                    choices = choices.order_by(*(keys[:1] + ["pk"]))
                if hasattr(choices.model, "active"):
                    available = Q(active=True)
                    if choices.model is models.Part:
                        available &= Q(instrument__active=True)
                    current = getattr(self.instance, name + "_id", None)
                    if current and not self.instance._state.adding:
                        available |= Q(pk=current)
                    choices = choices.filter(available)
                field.queryset = choices
                field.empty_label = _("Bitte wählen")


class WorkForm(RecordForm):
    class Meta:
        model = models.Work
        fields = ["title", "composer", "active"]


class ArrangementForm(RecordForm):
    class Meta:
        model = models.Arrangement
        fields = ["work", "arranger", "edition", "expectations_defined", "active"]


class InstrumentForm(RecordForm):
    class Meta:
        model = models.InstrumentVariant
        fields = ["name", "family", "transposition", "clef", "active"]


class PartForm(RecordForm):
    class Meta:
        model = models.Part
        fields = ["instrument", "code", "label", "active"]


class WorkAliasForm(RecordForm):
    class Meta:
        model = models.WorkAlias
        fields = ["work", "alias", "active"]


class InstrumentAliasForm(RecordForm):
    class Meta:
        model = models.InstrumentAlias
        fields = ["alias", "instrument", "part", "active"]


class ExpectedPartForm(RecordForm):
    class Meta:
        model = models.ExpectedPart
        fields = ["arrangement", "part", "required"]


class TemplateForm(RecordForm):
    class Meta:
        model = models.InstrumentationTemplate
        fields = ["name", "active"]


class TemplatePartForm(RecordForm):
    class Meta:
        model = models.TemplatePart
        fields = ["template", "part", "required"]


class TemplateApplyForm(forms.Form):
    template = forms.ModelChoiceField(
        label=_("Besetzungsvorlage"), queryset=models.InstrumentationTemplate.objects.none()
    )
    expected_revision = forms.IntegerField(min_value=1, widget=forms.HiddenInput)
    replace = forms.BooleanField(label=_("Bestehende Erwartungsliste ausdrücklich ersetzen"), required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["template"].queryset = models.InstrumentationTemplate.objects.filter(active=True).order_by(
            "name_key", "id"
        )


class DeleteForm(forms.Form):
    expected_revision = forms.IntegerField(min_value=1, widget=forms.HiddenInput)
    confirm = forms.BooleanField(label=_("Unbenutzten Datensatz endgültig löschen"))


class SearchForm(forms.Form):
    q = forms.CharField(label=_("Suchen"), max_length=200, required=False)
    active = forms.ChoiceField(
        label=_("Status"),
        choices=[("1", _("Aktive")), ("0", _("Inaktive")), ("all", _("Alle"))],
        required=False,
        initial="1",
    )
