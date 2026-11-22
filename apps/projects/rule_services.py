"""Validated one-hop rule scopes and exact edition preferences for the resolver."""

from contextlib import contextmanager
from dataclasses import dataclass

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F
from django.utils.translation import gettext_lazy as _

from apps.archive import edition_services
from apps.catalog.models import Arrangement, Part
from apps.projects import models as m
from apps.projects.participant_services import playable
from apps.projects.services import ProjectConflict, edit, reviewer

MAX_RULES = 2000


@contextmanager
def scope_edit(project_id, expected_revision, actor, event):
    if project_id is not None:
        with edit(project_id, expected_revision, actor=actor, event=event) as project:
            yield project, {"project": project, "project_revision": project.revision}
    else:
        with transaction.atomic():
            if (
                type(expected_revision) is not int
                or expected_revision < 1
                or not m.GlobalRuleState.objects.filter(pk=1, revision=expected_revision).update(
                    revision=F("revision") + 1
                )
            ):
                raise ProjectConflict()
            reviewer(actor)
            yield None, {"global_revision": expected_revision + 1}


def _position(project, identifier):
    if identifier is None:
        return None
    if project is None:
        raise ValidationError(_("Globale Regeln dürfen keine Projektposition enthalten."))
    position = project.positions.filter(
        pk=identifier, active=True, arrangement__isnull=False, arrangement__active=True, arrangement__work__active=True
    ).first()
    if position is None:
        raise ValidationError(_("Wählen Sie ein aktives Stück dieses Projekts, keine Reserve."))
    return position


def _rules():
    globals_ = list(
        m.GlobalReplacementRule.objects.filter(active=True).select_related(
            "desired_part__instrument", "replacement_part__instrument"
        )[: MAX_RULES + 1]
    )
    locals_ = list(
        m.ReplacementRule.objects.filter(active=True).select_related(
            "desired_part__instrument", "replacement_part__instrument"
        )[:20_001]
    )
    if len(globals_) > MAX_RULES or len(locals_) > 20_000:
        raise ValidationError(_("Ersatzregelbestand überschreitet die sichere Prüfgrenze."))
    return globals_, locals_


def validate_cycles(candidate):
    """Check effective overlays in every affected context, not just equal scopes."""
    globals_, locals_ = _rules()
    global_candidate = isinstance(candidate, m.GlobalReplacementRule)
    globals_ = [r for r in globals_ if not (global_candidate and r.pk == candidate.pk)]
    locals_ = [r for r in locals_ if not (not global_candidate and r.pk == candidate.pk)]
    if candidate.active:
        (globals_ if global_candidate else locals_).append(candidate)
    contexts = (
        {(None, None)}
        | {(r.project_id, None) for r in locals_}
        | {(r.project_id, r.position_id) for r in locals_ if r.position_id}
    )
    if len(contexts) > 2000:
        raise ValidationError(_("Zu viele Regelkontexte für eine begrenzte sichere Zyklusprüfung."))
    base = {r.desired_part_id: r.replacement_part_id for r in globals_}
    for project_id, position_id in contexts:
        edges = dict(base)
        edges.update(
            {
                r.desired_part_id: r.replacement_part_id
                for r in locals_
                if r.project_id == project_id and r.position_id is None
            }
        )
        if position_id is not None:
            edges.update(
                {
                    r.desired_part_id: r.replacement_part_id
                    for r in locals_
                    if r.project_id == project_id and r.position_id == position_id
                }
            )
        done = set()
        for start in edges:
            current, visiting = start, set()
            while current in edges and current not in done:
                if current in visiting:
                    raise ValidationError(_("Zyklische Ersatzregeln über die Geltungsbereiche sind nicht erlaubt."))
                visiting.add(current)
                current = edges[current]
            done.update(visiting)


def save_replacement(
    *, project_id=None, position_id=None, desired_part_id, replacement_part_id, rule_id=None, actor, expected_revision
):
    with scope_edit(project_id, expected_revision, actor, "REPLACEMENT_SAVED") as (project, audit):
        position = _position(project, position_id)
        desired, target = playable(desired_part_id), playable(replacement_part_id)
        if desired.pk == target.pk or desired.instrument_id != target.instrument_id:
            raise ValidationError(_("Ersatz benötigt eine andere Stimme derselben exakten Stimmung und Notation."))
        model = m.ReplacementRule if project else m.GlobalReplacementRule
        query = model.objects.filter(project=project) if project else model.objects.all()
        if rule_id:
            rule = query.filter(pk=rule_id).first()
            if (
                rule is None
                or rule.desired_part_id != desired.pk
                or (project and rule.position_id != (position.pk if position else None))
            ):
                raise ValidationError(_("Regel-Geltungsbereich ist unveränderlich."))
        else:
            if query.count() >= MAX_RULES:
                raise ValidationError(_("Ersatzregelgrenze erreicht."))
            rule = (
                model(project=project, position=position, desired_part=desired)
                if project
                else model(desired_part=desired)
            )
        duplicate = query.filter(desired_part=desired).exclude(pk=rule.pk)
        if project:
            duplicate = duplicate.filter(position=position)
        if duplicate.exists():
            raise ValidationError(_("Ersatzregel existiert bereits; ausdrücklich bearbeiten."))
        previous = rule.replacement_part_id
        rule.replacement_part, rule.active = target, True
        validate_cycles(rule)
        rule.save()
        m.RuleChange.objects.create(
            **audit,
            actor=reviewer(actor),
            event="REPLACEMENT_SAVED",
            **{"rule" if project else "global_rule": rule},
            previous_part_id=previous,
            selected_part=target,
            active=True,
        )
        return rule


def clear_replacement(rule_id, *, project_id=None, actor, expected_revision):
    with scope_edit(project_id, expected_revision, actor, "REPLACEMENT_CLEARED") as (project, audit):
        query = m.ReplacementRule.objects.filter(project=project) if project else m.GlobalReplacementRule.objects.all()
        rule = query.filter(pk=rule_id).first()
        if rule is None:
            raise ValidationError(_("Regel gehört nicht zum gewählten Geltungsbereich."))
        rule.active = False
        # Removing a more-specific edge can expose a cyclic inherited overlay.
        validate_cycles(rule)
        # Preserve even obsolete/incompatible historical target references on clear.
        query.filter(pk=rule.pk).update(active=False)
        m.RuleChange.objects.create(
            **audit,
            actor=reviewer(actor),
            event="REPLACEMENT_CLEARED",
            **{"rule" if project else "global_rule": rule},
            previous_part=rule.replacement_part,
            active=False,
        )
        return rule


def set_edition(project_id, *, arrangement_id, part_id, edition_id, position_id=None, actor, expected_revision):
    selected = edition_services.compatible(arrangement_id, part_id).filter(pk=edition_id).first()
    if (
        selected is None
        or edition_services.resolve(arrangement_id, part_id, explicit_assignment_id=edition_id).status != "AVAILABLE"
    ):
        raise ValidationError(_("Nur genau passende bestätigte, hash-geprüfte Ausgabe wählen."))
    file_revision = selected.archive_file.revision
    with edit(project_id, expected_revision, actor=actor, event="EDITION_RULE_SAVED") as project:
        position = _position(project, position_id)
        arrangement = Arrangement.objects.filter(pk=arrangement_id, active=True, work__active=True).first()
        part = playable(part_id)
        if arrangement is None or (position and position.arrangement_id != arrangement.pk):
            raise ValidationError(_("Ausgabe und Position müssen dasselbe Arrangement betreffen."))
        if (
            not edition_services.compatible(arrangement_id, part_id)
            .filter(pk=selected.pk, archive_file__revision=file_revision)
            .exists()
        ):
            raise ProjectConflict()
        model = m.PositionEditionPreference if position else m.ProjectEditionPreference
        scope = {
            "project": project,
            "part": part,
            **({"position": position} if position else {"arrangement": arrangement}),
        }
        preference, _created = model.objects.get_or_create(**scope, defaults={"edition": selected})
        previous = None if _created else preference.edition_id
        preference.edition, preference.active = selected, True
        if position:
            preference.needs_revalidation = False
        preference.save()
        m.RuleChange.objects.create(
            project=project,
            project_revision=project.revision,
            actor=reviewer(actor),
            event="EDITION_SAVED",
            **{"position_preference" if position else "project_preference": preference},
            previous_edition_id=previous,
            selected_edition=selected,
            active=True,
        )
        return preference


def clear_edition(project_id, preference_id, *, position_scope=False, actor, expected_revision):
    with edit(project_id, expected_revision, actor=actor, event="EDITION_RULE_CLEARED") as project:
        model = m.PositionEditionPreference if position_scope else m.ProjectEditionPreference
        query = model.objects.filter(project=project)
        preference = query.filter(pk=preference_id).first()
        if preference is None:
            raise ValidationError(_("Ausgabenregel gehört nicht zu diesem Projekt."))
        query.filter(pk=preference.pk).update(active=False)
        preference.active = False
        m.RuleChange.objects.create(
            project=project,
            project_revision=project.revision,
            actor=reviewer(actor),
            event="EDITION_CLEARED",
            **{"position_preference" if position_scope else "project_preference": preference},
            previous_edition=preference.edition,
            active=False,
        )
        return preference


@dataclass(frozen=True)
class ReplacementChoice:
    status: str
    origin: str
    rule: m.ReplacementRule | m.GlobalReplacementRule | None = None
    part: Part | None = None


def replacement_choice(project_id, position_id, desired_part_id, *, local_rules=None, global_rules=None):
    local_rules = (
        local_rules
        if local_rules is not None
        else m.ReplacementRule.objects.filter(
            project_id=project_id, desired_part_id=desired_part_id, active=True
        ).select_related("desired_part__instrument", "replacement_part__instrument", "position")
    )
    global_rules = (
        global_rules
        if global_rules is not None
        else m.GlobalReplacementRule.objects.filter(desired_part_id=desired_part_id, active=True).select_related(
            "desired_part__instrument", "replacement_part__instrument"
        )
    )
    local = [r for r in local_rules if r.project_id == project_id and r.desired_part_id == desired_part_id and r.active]
    position = [r for r in local if r.position_id == position_id and position_id is not None]
    project = [r for r in local if r.position_id is None]
    global_ = [r for r in global_rules if r.desired_part_id == desired_part_id and r.active]
    candidates, origin = (
        (position, "POSITION") if position else (project, "PROJECT") if project else (global_, "GLOBAL")
    )
    if not candidates:
        return ReplacementChoice("NONE", "NONE")
    if len(candidates) != 1:
        return ReplacementChoice("INVALID", origin)
    rule = candidates[0]
    desired, target = rule.desired_part, rule.replacement_part
    if (
        desired.pk == target.pk
        or desired.instrument_id != target.instrument_id
        or not target.active
        or not target.instrument.active
        or not desired.active
    ):
        return ReplacementChoice("INVALID", origin)
    if origin == "POSITION" and (
        rule.position.project_id != project_id or not rule.position.active or not rule.position.arrangement_id
    ):
        return ReplacementChoice("INVALID", origin)
    if origin == "POSITION" and (not rule.position.arrangement.active or not rule.position.arrangement.work.active):
        return ReplacementChoice("INVALID", origin)
    return ReplacementChoice("REPLACEMENT", origin, rule, target)


def edition_preference(project_id, position_id, arrangement_id, part_id):
    """Select only the preference scope; WP-32 validates actual editions centrally."""
    position = (
        m.PositionEditionPreference.objects.filter(
            project_id=project_id, position_id=position_id, part_id=part_id, active=True
        ).first()
        if position_id
        else None
    )
    if position:
        return position, "POSITION"
    project = m.ProjectEditionPreference.objects.filter(
        project_id=project_id, arrangement_id=arrangement_id, part_id=part_id, active=True
    ).first()
    return (project, "PROJECT") if project else (None, "NONE")
