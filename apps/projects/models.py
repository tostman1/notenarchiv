"""Durable project graph; one shared position list, protected historical identities."""

import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from apps.catalog.models import normalized


class Record(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if kwargs.get("using"):
            self._state.db = kwargs["using"]
        self.full_clean()
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Project identities are retained; archive or remove explicitly through services.")


class Project(Record):
    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", _("Aktiv")
        ARCHIVED = "ARCHIVED", _("Archiviert")

    class Layout(models.TextChoices):
        REGULAR = "REGULAR", _("Normale Mappe")
        MARCHBOOK = "MARCHBOOK", _("Marschbuch")

    name = models.CharField(max_length=200, verbose_name=_("Projektname"))
    name_key = models.CharField(max_length=400, editable=False, db_index=True)
    status = models.CharField(max_length=16, choices=Status, default=Status.ACTIVE)
    revision = models.PositiveBigIntegerField(default=1, editable=False)
    layout = models.CharField(max_length=16, choices=Layout, default=Layout.REGULAR, verbose_name=_("Layout"))
    width_mm = models.PositiveIntegerField(
        default=170, validators=[MinValueValidator(50), MaxValueValidator(500)], verbose_name=_("Marschbuchbreite (mm)")
    )
    height_mm = models.PositiveIntegerField(
        default=120, validators=[MinValueValidator(50), MaxValueValidator(500)], verbose_name=_("Marschbuchhöhe (mm)")
    )
    cover_enabled = models.BooleanField(default=True, verbose_name=_("Persönliches Deckblatt"))
    cover_title = models.CharField(max_length=200, blank=True, verbose_name=_("Deckblatttitel (optional)"))
    updated_at = models.DateTimeField(auto_now=True)
    duplicated_from = models.ForeignKey(
        "self", on_delete=models.PROTECT, null=True, blank=True, related_name="duplicates"
    )

    def clean(self):
        self.name_key = normalized(self.name)
        if not self.name_key:
            raise ValidationError({"name": _("Geben Sie einen Projektnamen ein.")})
        if not self._state.adding and type(self).objects.get(pk=self.pk).duplicated_from_id != self.duplicated_from_id:
            raise ValidationError("Duplication provenance is immutable.")

    class Meta:
        ordering = ["name_key", "id"]
        constraints = [
            models.CheckConstraint(condition=Q(status__in=["ACTIVE", "ARCHIVED"]), name="projects_valid_status"),
            models.CheckConstraint(condition=Q(layout__in=["REGULAR", "MARCHBOOK"]), name="projects_valid_layout"),
            models.CheckConstraint(condition=Q(revision__gte=1), name="projects_positive_revision"),
            models.CheckConstraint(
                condition=Q(width_mm__gte=50, width_mm__lte=500, height_mm__gte=50, height_mm__lte=500),
                name="projects_bounded_dimensions",
            ),
        ]

    def __str__(self):
        return f"{self.name} · {str(self.pk)[:8]}"


class Scoped(Record):
    project = models.ForeignKey(Project, on_delete=models.PROTECT)

    class Meta:
        abstract = True

    def clean(self):
        if not self._state.adding:
            old = type(self).objects.using(self._state.db or "default").get(pk=self.pk)
            if self.project_id != old.project_id:
                raise ValidationError("Project scope is immutable.")
            immutable = {
                "PartOverride": ("participant_id", "position_id"),
                "ProjectEditionPreference": ("arrangement_id", "part_id"),
                "PositionEditionPreference": ("position_id", "part_id"),
                "EnsembleMapping": ("role_id", "instrument_id", "position_id"),
                "ReplacementRule": ("position_id", "desired_part_id"),
            }.get(type(self).__name__, ())
            if any(getattr(self, name) != getattr(old, name) for name in immutable):
                raise ValidationError("Associated scope identity is immutable.")
        for name in ("position", "participant", "role"):
            field = getattr(self, name + "_id", None)
            if field and getattr(self, name).project_id != self.project_id:
                raise ValidationError("Related identity belongs to another project.")


class ProjectPosition(Scoped):
    project = models.ForeignKey(Project, on_delete=models.PROTECT, related_name="positions")
    arrangement = models.ForeignKey("catalog.Arrangement", on_delete=models.PROTECT, null=True, blank=True)
    order = models.PositiveIntegerField(null=True, blank=True)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ["order", "id"]
        constraints = [
            models.UniqueConstraint(fields=["project", "order"], condition=Q(active=True), name="projects_unique_slot"),
            models.CheckConstraint(
                condition=Q(active=True, order__gte=1, order__isnull=False) | Q(active=False, order__isnull=True),
                name="projects_slot_order_state",
            ),
        ]


class ProjectRole(Scoped):
    project = models.ForeignKey(Project, on_delete=models.PROTECT, related_name="roles")
    code = models.CharField(max_length=40)
    code_key = models.CharField(max_length=80, editable=False)
    label = models.CharField(max_length=120, blank=True)
    active = models.BooleanField(default=True)

    def clean(self):
        super().clean()
        self.code_key = normalized(self.code)
        if not self.code_key:
            raise ValidationError("A non-empty role code is required.")

    class Meta:
        constraints = [models.UniqueConstraint(fields=["project", "code_key"], name="projects_unique_role")]

    def __str__(self):
        return f"{self.code} · {self.label or '—'} · {str(self.pk)[:8]}"


class ProjectParticipant(Scoped):
    project = models.ForeignKey(Project, on_delete=models.PROTECT, related_name="participants")
    member = models.ForeignKey("members.Member", on_delete=models.PROTECT, null=True, blank=True)
    guest_id = models.UUIDField(null=True, blank=True)
    display_name = models.CharField(max_length=160)
    default_part = models.ForeignKey("catalog.Part", on_delete=models.PROTECT, related_name="project_defaults")
    role = models.ForeignKey(ProjectRole, on_delete=models.PROTECT, null=True, blank=True)
    active = models.BooleanField(default=True)
    member_revision = models.PositiveBigIntegerField(null=True, blank=True)
    default_origin = models.CharField(
        max_length=16, choices=[("MEMBER", "MEMBER"), ("MANUAL", "MANUAL"), ("GUEST", "GUEST")], default="MANUAL"
    )

    def clean(self):
        super().clean()
        if not normalized(self.display_name):
            raise ValidationError("Participant display name is required.")
        if bool(self.member_id) == bool(self.guest_id):
            raise ValidationError("Exactly one member or guest identity is required.")
        if not self._state.adding:
            old = type(self).objects.get(pk=self.pk)
            if (old.member_id, old.guest_id) != (self.member_id, self.guest_id):
                raise ValidationError("Participant identity is immutable.")

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(default_origin__in=["MEMBER", "MANUAL", "GUEST"]), name="projects_valid_default_origin"
            ),
            models.CheckConstraint(
                condition=Q(member__isnull=False, guest_id__isnull=True)
                | Q(member__isnull=True, guest_id__isnull=False),
                name="projects_participant_identity",
            ),
            models.UniqueConstraint(
                fields=["project", "member"], condition=Q(member__isnull=False), name="projects_unique_member"
            ),
            models.UniqueConstraint(
                fields=["project", "guest_id"], condition=Q(guest_id__isnull=False), name="projects_unique_guest"
            ),
        ]


def validate_edition(instance, arrangement_id, part_id):
    if instance.edition_id:
        edition = instance.edition
        if edition.part_id != part_id or edition.archive_file.arrangement_id != arrangement_id:
            raise ValidationError("Edition must match the exact arrangement and playable part.")
        changed = instance._state.adding or type(instance).objects.get(pk=instance.pk).edition_id != instance.edition_id
        if changed:
            from apps.archive.models import ArchiveAssignment

            if not ArchiveAssignment.objects.usable().filter(pk=edition.pk).exists():
                raise ValidationError("New explicit editions must be confirmed and available.")


class PartOverride(Scoped):
    participant = models.ForeignKey(ProjectParticipant, on_delete=models.PROTECT, related_name="overrides")
    position = models.ForeignKey(ProjectPosition, on_delete=models.PROTECT, related_name="overrides")
    desired_part = models.ForeignKey("catalog.Part", on_delete=models.PROTECT, related_name="personal_overrides")
    edition = models.ForeignKey("archive.ArchiveAssignment", on_delete=models.PROTECT, null=True, blank=True)
    needs_revalidation = models.BooleanField(default=False)

    def clean(self):
        super().clean()
        if not self.needs_revalidation:
            if not self.position.active or not self.position.arrangement_id:
                raise ValidationError("Reserve/removed slots cannot have effective overrides.")
            validate_edition(self, self.position.arrangement_id, self.desired_part_id)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["participant", "position"], name="projects_unique_override")]


class ProjectEditionPreference(Scoped):
    arrangement = models.ForeignKey("catalog.Arrangement", on_delete=models.PROTECT)
    part = models.ForeignKey("catalog.Part", on_delete=models.PROTECT)
    edition = models.ForeignKey("archive.ArchiveAssignment", on_delete=models.PROTECT)

    def clean(self):
        super().clean()
        validate_edition(self, self.arrangement_id, self.part_id)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["project", "arrangement", "part"], name="projects_unique_edition")
        ]


class PositionEditionPreference(Scoped):
    position = models.ForeignKey(ProjectPosition, on_delete=models.PROTECT, related_name="edition_preferences")
    part = models.ForeignKey("catalog.Part", on_delete=models.PROTECT)
    edition = models.ForeignKey("archive.ArchiveAssignment", on_delete=models.PROTECT)
    needs_revalidation = models.BooleanField(default=False)

    def clean(self):
        super().clean()
        if not self.needs_revalidation:
            if not self.position.arrangement_id or not self.position.active:
                raise ValidationError("Reserve/removed slots cannot have effective edition preferences.")
            validate_edition(self, self.position.arrangement_id, self.part_id)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["position", "part"], name="projects_unique_position_edition")]


class EnsembleMapping(Scoped):
    role = models.ForeignKey(ProjectRole, on_delete=models.PROTECT, related_name="mappings")
    instrument = models.ForeignKey("catalog.InstrumentVariant", on_delete=models.PROTECT)
    position = models.ForeignKey(
        ProjectPosition, on_delete=models.PROTECT, null=True, blank=True, related_name="ensemble_mappings"
    )
    part = models.ForeignKey("catalog.Part", on_delete=models.PROTECT)
    active = models.BooleanField(default=True)

    def clean(self):
        super().clean()
        if self.part.instrument_id != self.instrument_id:
            raise ValidationError("Mapping requires this exact playable instrument/notation variant.")

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["project", "role", "instrument"],
                condition=Q(position__isnull=True),
                name="projects_unique_default_mapping",
            ),
            models.UniqueConstraint(
                fields=["project", "role", "instrument", "position"],
                condition=Q(position__isnull=False),
                name="projects_unique_position_mapping",
            ),
        ]


class ProjectRevision(Record):
    project = models.ForeignKey(Project, on_delete=models.PROTECT, related_name="history")
    revision = models.PositiveBigIntegerField()
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    event = models.CharField(max_length=40)
    data = models.JSONField(default=dict)

    def clean(self):
        if not self._state.adding:
            raise ValidationError("Project revision history is append-only.")
        from apps.archive.validation import bounded_json

        bounded_json(self.data)

    class Meta:
        ordering = ["revision"]
        constraints = [models.UniqueConstraint(fields=["project", "revision"], name="projects_unique_revision")]


class ReplacementRule(Scoped):
    position = models.ForeignKey(ProjectPosition, on_delete=models.PROTECT, null=True, blank=True)
    desired_part = models.ForeignKey("catalog.Part", on_delete=models.PROTECT, related_name="project_replacement_rules")
    replacement_part = models.ForeignKey(
        "catalog.Part", on_delete=models.PROTECT, related_name="project_replacement_targets"
    )

    def clean(self):
        super().clean()
        if self.desired_part_id == self.replacement_part_id:
            raise ValidationError("Replacement must target a different explicit playable part.")
        if self.desired_part.instrument_id != self.replacement_part.instrument_id:
            raise ValidationError("Baseline replacement requires the same explicit notation variant.")
        seen = {self.desired_part_id}
        current = self.replacement_part_id
        for _step in range(100):
            if current in seen:
                raise ValidationError("Cyclic replacement rule.")
            seen.add(current)
            rule = (
                type(self)
                .objects.filter(project_id=self.project_id, position_id=self.position_id, desired_part_id=current)
                .exclude(pk=self.pk)
                .first()
            )
            if rule is None:
                break
            current = rule.replacement_part_id
        else:
            raise ValidationError("Replacement rule graph limit exceeded.")

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=~Q(desired_part=models.F("replacement_part")), name="projects_different_replacement"
            ),
            models.UniqueConstraint(
                fields=["project", "desired_part"],
                condition=Q(position__isnull=True),
                name="projects_unique_default_replacement",
            ),
            models.UniqueConstraint(
                fields=["position", "desired_part"],
                condition=Q(position__isnull=False),
                name="projects_unique_slot_replacement",
            ),
        ]


class PositionChange(Record):
    project = models.ForeignKey(Project, on_delete=models.PROTECT, related_name="position_history")
    position = models.ForeignKey(ProjectPosition, on_delete=models.PROTECT, related_name="history")
    project_revision = models.PositiveBigIntegerField()
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    event = models.CharField(max_length=24)
    previous_arrangement = models.ForeignKey(
        "catalog.Arrangement", on_delete=models.PROTECT, null=True, blank=True, related_name="position_changes_from"
    )
    selected_arrangement = models.ForeignKey(
        "catalog.Arrangement", on_delete=models.PROTECT, null=True, blank=True, related_name="position_changes_to"
    )
    previous_order = models.PositiveIntegerField(null=True, blank=True)
    selected_order = models.PositiveIntegerField(null=True, blank=True)
    previous_active = models.BooleanField(null=True, blank=True)
    selected_active = models.BooleanField()

    def clean(self):
        if not self._state.adding:
            raise ValidationError("Position history is append-only.")
        if self.position.project_id != self.project_id:
            raise ValidationError("Position history belongs to another project.")

    class Meta:
        ordering = ["project_revision", "created_at", "id"]


class ParticipantChange(Record):
    project = models.ForeignKey(Project, on_delete=models.PROTECT, related_name="participant_history")
    participant = models.ForeignKey(ProjectParticipant, on_delete=models.PROTECT, related_name="history")
    project_revision = models.PositiveBigIntegerField()
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    event = models.CharField(max_length=32)
    previous_part = models.ForeignKey(
        "catalog.Part", on_delete=models.PROTECT, null=True, blank=True, related_name="participant_changes_from"
    )
    selected_part = models.ForeignKey("catalog.Part", on_delete=models.PROTECT, related_name="participant_changes_to")
    previous_name = models.CharField(max_length=160, blank=True)
    selected_name = models.CharField(max_length=160)
    previous_active = models.BooleanField(null=True, blank=True)
    selected_active = models.BooleanField()
    member_revision = models.PositiveBigIntegerField(null=True, blank=True)

    def clean(self):
        if not self._state.adding:
            raise ValidationError("Participant history is append-only.")
        if self.participant.project_id != self.project_id:
            raise ValidationError("Participant history belongs to another project.")

    class Meta:
        ordering = ["project_revision", "created_at", "id"]


class EnsembleChange(Record):
    """Append-only references for role, mapping and participant-role edits."""

    project = models.ForeignKey(Project, on_delete=models.PROTECT, related_name="ensemble_history")
    project_revision = models.PositiveBigIntegerField()
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    event = models.CharField(max_length=32)
    role = models.ForeignKey(ProjectRole, on_delete=models.PROTECT, null=True, blank=True)
    mapping = models.ForeignKey(EnsembleMapping, on_delete=models.PROTECT, null=True, blank=True)
    participant = models.ForeignKey(ProjectParticipant, on_delete=models.PROTECT, null=True, blank=True)
    previous_part = models.ForeignKey(
        "catalog.Part", on_delete=models.PROTECT, null=True, blank=True, related_name="ensemble_changes_from"
    )
    selected_part = models.ForeignKey(
        "catalog.Part", on_delete=models.PROTECT, null=True, blank=True, related_name="ensemble_changes_to"
    )
    previous_role = models.ForeignKey(
        ProjectRole, on_delete=models.PROTECT, null=True, blank=True, related_name="ensemble_changes_from"
    )
    selected_role = models.ForeignKey(
        ProjectRole, on_delete=models.PROTECT, null=True, blank=True, related_name="ensemble_changes_to"
    )
    before = models.JSONField(default=dict, blank=True)
    after = models.JSONField(default=dict, blank=True)

    def clean(self):
        if not self._state.adding:
            raise ValidationError("Ensemble history is append-only.")
        for name in ("role", "mapping", "participant", "previous_role", "selected_role"):
            if getattr(self, name + "_id") and getattr(self, name).project_id != self.project_id:
                raise ValidationError("Ensemble history must stay in its project.")
        from apps.archive.validation import bounded_json

        bounded_json(self.before)
        bounded_json(self.after)

    class Meta:
        ordering = ["project_revision", "created_at", "id"]
