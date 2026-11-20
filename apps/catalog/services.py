"""Short write-first SQLite catalog transactions and protected references."""

from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import IntegrityError, transaction
from django.db.models import F
from django.db.models.deletion import PROTECT, ProtectedError
from django.utils.translation import gettext as _

from apps.catalog.models import Arrangement, ExpectedPart, InstrumentVariant, Part, TemplatePart


class EditConflict(ValidationError):
    def __init__(self):
        super().__init__(_("Der Datensatz wurde inzwischen geändert. Bitte laden Sie die Seite neu."))


def _has_protected_references(instance):
    return any(
        relation.related_model._base_manager.filter(**{relation.field.attname: instance.pk}).exists()
        for relation in instance._meta.related_objects
        if getattr(relation, "on_delete", None) is PROTECT
    )


def _validate_references(instance, previous):
    if previous is not None and isinstance(instance, (Part, InstrumentVariant)):
        identity_fields = (
            ("instrument_id", "code_key")
            if isinstance(instance, Part)
            else (
                "name_key",
                "family_key",
                "transposition_key",
                "clef",
            )
        )
        if any(
            getattr(instance, field) != getattr(previous, field) for field in identity_fields
        ) and _has_protected_references(instance):
            raise ValidationError(
                _("Diese musikalische Zuordnung wird verwendet. Legen Sie eine neue Variante oder Stimme an.")
            )
    for field in instance._meta.fields:
        if field.many_to_one:
            related_id = getattr(instance, field.attname)
            if related_id is None:
                continue
            try:
                related = field.related_model.objects.get(pk=related_id)
            except ObjectDoesNotExist:
                raise ValidationError({field.name: _("Der gewählte Datensatz ist nicht mehr vorhanden.")}) from None
            changed = previous is None or related_id != getattr(previous, field.attname)
            if changed and hasattr(related, "active") and not related.active:
                raise ValidationError({field.name: _("Wählen Sie einen aktiven Datensatz.")})
            if changed and isinstance(related, Part) and not related.instrument.active:
                raise ValidationError({field.name: _("Die Instrumentenvariante dieser Stimme ist inaktiv.")})
    if isinstance(instance, (Part, InstrumentVariant)) and not instance.active:
        referenced = (
            instance.regular_members.filter(active=True).exists()
            if isinstance(instance, Part)
            else instance.parts.filter(regular_members__active=True).exists()
        )
        if referenced:
            raise ValidationError(
                _("Aktive Mitglieder verwenden diese Stimme oder Variante. Ändern Sie zuerst deren Stammstimme.")
            )
    if isinstance(instance, Arrangement) and not instance.expectations_defined and instance.expected_parts.exists():
        raise ValidationError({"expectations_defined": _("Entfernen Sie zuerst die vorhandene Erwartungsliste.")})


def _touch_parent(instance):
    if isinstance(instance, ExpectedPart):
        Arrangement.objects.filter(pk=instance.arrangement_id).update(
            expectations_defined=True, revision=F("revision") + 1
        )
    elif isinstance(instance, TemplatePart):
        type(instance.template).objects.filter(pk=instance.template_id).update(revision=F("revision") + 1)


def save_record(instance, *, expected_revision=0):
    """Validate before and after taking the write lock, excluding stale FK caches."""
    instance.full_clean()
    creating = instance._state.adding
    try:
        with transaction.atomic():
            if creating:
                if expected_revision != 0:
                    raise EditConflict()
                instance.save(force_insert=True)  # First transactional statement takes SQLite's write lock.
                previous = None
            else:
                changed = (
                    type(instance)
                    .objects.filter(pk=instance.pk, revision=expected_revision)
                    .update(revision=F("revision") + 1)
                )
                if not changed:
                    raise EditConflict()
                previous = type(instance).objects.get(pk=instance.pk)
                instance.revision = expected_revision + 1
            _validate_references(instance, previous)
            instance.full_clean()
            if not creating:
                instance.save()
            if (
                previous is not None
                and isinstance(instance, ExpectedPart)
                and previous.arrangement_id != instance.arrangement_id
            ):
                _touch_parent(previous)
            if (
                previous is not None
                and isinstance(instance, TemplatePart)
                and previous.template_id != instance.template_id
            ):
                _touch_parent(previous)
            _touch_parent(instance)
    except IntegrityError:
        raise ValidationError(
            _("Speichern nicht möglich. Prüfen Sie doppelte Einträge und gültige Referenzen.")
        ) from None
    return instance


def delete_record(instance, *, expected_revision):
    try:
        with transaction.atomic():
            if (
                not type(instance)
                .objects.filter(pk=instance.pk, revision=expected_revision)
                .update(revision=F("revision") + 1)
            ):
                raise EditConflict()
            _touch_parent(instance)
            instance.delete()
    except ProtectedError:
        raise ValidationError(
            _("Dieser Datensatz wird verwendet. Deaktivieren Sie ihn, statt ihn zu löschen.")
        ) from None


def apply_template(arrangement_id, template, *, expected_revision, replace=False):
    """Copy current expectations; no live relation to subsequent template edits."""
    try:
        with transaction.atomic():
            if not Arrangement.objects.filter(pk=arrangement_id, revision=expected_revision).update(
                revision=F("revision") + 1
            ):
                raise EditConflict()
            arrangement = Arrangement.objects.get(pk=arrangement_id)
            template.refresh_from_db()
            if not arrangement.active or not template.active:
                raise ValidationError(_("Arrangement und Vorlage müssen aktiv sein."))
            if (arrangement.expectations_defined or arrangement.expected_parts.exists()) and not replace:
                raise ValidationError(_("Bestätigen Sie ausdrücklich das Ersetzen der bestehenden Erwartungsliste."))
            entries = list(template.entries.select_related("part__instrument")[:1001])
            if len(entries) > 1000:
                raise ValidationError(_("Eine Vorlage darf höchstens 1000 Stimmen enthalten."))
            if any(not entry.part.active or not entry.part.instrument.active for entry in entries):
                raise ValidationError(_("Die Vorlage enthält inaktive Stimmen. Bitte korrigieren Sie sie zuerst."))
            arrangement.expected_parts.all().delete()
            ExpectedPart.objects.bulk_create(
                [ExpectedPart(arrangement=arrangement, part=entry.part, required=entry.required) for entry in entries]
            )
            Arrangement.objects.filter(pk=arrangement_id).update(expectations_defined=True)
            arrangement.expectations_defined = True
            return arrangement
    except IntegrityError:
        raise ValidationError(_("Die Erwartungsliste konnte nicht sicher übernommen werden.")) from None
    except ObjectDoesNotExist:
        raise ValidationError(_("Die gewählte Vorlage ist nicht mehr vorhanden.")) from None
