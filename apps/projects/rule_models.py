"""Global rule revision and protected audit refs; project scope models are reused."""

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Q

from apps.projects.models import Record


class GlobalRuleState(models.Model):
    id = models.PositiveSmallIntegerField(primary_key=True, default=1)
    revision = models.PositiveBigIntegerField(default=1)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=Q(id=1), name="projects_global_rule_singleton"),
            models.CheckConstraint(condition=Q(revision__gte=1), name="projects_global_rule_revision"),
        ]


class GlobalReplacementRule(Record):
    desired_part = models.OneToOneField(
        "catalog.Part", on_delete=models.PROTECT, related_name="global_replacement_rule"
    )
    replacement_part = models.ForeignKey(
        "catalog.Part", on_delete=models.PROTECT, related_name="global_replacement_targets"
    )
    active = models.BooleanField(default=True)

    def clean(self):
        if (
            self.desired_part_id == self.replacement_part_id
            or self.desired_part.instrument_id != self.replacement_part.instrument_id
        ):
            raise ValidationError("Explicit replacement must be a different part of the same notation variant.")
        if not self._state.adding and type(self).objects.get(pk=self.pk).desired_part_id != self.desired_part_id:
            raise ValidationError("Global replacement scope is immutable.")

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=~Q(desired_part=F("replacement_part")), name="projects_global_replacement_distinct"
            )
        ]


class RuleChange(Record):
    project = models.ForeignKey(
        "projects.Project", on_delete=models.PROTECT, null=True, blank=True, related_name="rule_history"
    )
    project_revision = models.PositiveBigIntegerField(null=True, blank=True)
    global_revision = models.PositiveBigIntegerField(null=True, blank=True)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    event = models.CharField(max_length=32)
    rule = models.ForeignKey("projects.ReplacementRule", on_delete=models.PROTECT, null=True, blank=True)
    global_rule = models.ForeignKey(GlobalReplacementRule, on_delete=models.PROTECT, null=True, blank=True)
    project_preference = models.ForeignKey(
        "projects.ProjectEditionPreference", on_delete=models.PROTECT, null=True, blank=True
    )
    position_preference = models.ForeignKey(
        "projects.PositionEditionPreference", on_delete=models.PROTECT, null=True, blank=True
    )
    previous_part = models.ForeignKey(
        "catalog.Part", on_delete=models.PROTECT, null=True, blank=True, related_name="rule_changes_from"
    )
    selected_part = models.ForeignKey(
        "catalog.Part", on_delete=models.PROTECT, null=True, blank=True, related_name="rule_changes_to"
    )
    previous_edition = models.ForeignKey(
        "archive.ArchiveAssignment",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="project_rule_changes_from",
    )
    selected_edition = models.ForeignKey(
        "archive.ArchiveAssignment",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="project_rule_changes_to",
    )
    active = models.BooleanField()

    def clean(self):
        if not self._state.adding:
            raise ValidationError("Rule change evidence is append-only.")
        for field in ("rule", "project_preference", "position_preference"):
            if getattr(self, field + "_id") and getattr(self, field).project_id != self.project_id:
                raise ValidationError("Rule evidence must match project scope.")

    class Meta:
        ordering = ["created_at", "id"]
        constraints = [
            models.CheckConstraint(
                condition=Q(project__isnull=True, project_revision__isnull=True, global_revision__isnull=False)
                | Q(project__isnull=False, project_revision__isnull=False, global_revision__isnull=True),
                name="projects_rule_audit_revision_scope",
            )
        ]
