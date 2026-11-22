"""Presentation choices only; existing central assignment integrity is authoritative."""

import time

from django.core.exceptions import ValidationError

from apps.projects.matrix_edit_services import choice_token
from apps.projects.matrix_forms import CellEditForm
from apps.projects.participant_forms import DefaultForm

MAX_CHOICES_PER_ARRANGEMENT = 200
MAX_ALTERNATIVE_BYTES = 512 * 1024**2


def add_edit_forms(context, actor):
    project, session = context["project"], context["session"]
    if project.status != "ACTIVE":
        return context
    page_values = {"rows": context["row_page"].number, "people": context["column_page"].number}
    grouped = {}
    for assignment in session.assignments.values():
        grouped.setdefault(assignment.archive_file.arrangement_id, []).append(assignment)
    alternatives = {}
    verified_files, total_bytes = set(), 0
    deadline = time.monotonic() + 60
    for arrangement_id, assignments in grouped.items():
        if len(assignments) > MAX_CHOICES_PER_ARRANGEMENT:
            raise ValidationError("Too many matrix alternatives; narrow archive edition inventory first.")
        options, tokens = [], {}
        for assignment in sorted(assignments, key=lambda item: (str(item.part), str(item.pk))):
            file = assignment.archive_file
            if file.pk not in verified_files:
                total_bytes += file.byte_size
                verified_files.add(file.pk)
            if total_bytes > MAX_ALTERNATIVE_BYTES or time.monotonic() > deadline:
                raise ValidationError("Matrix alternative integrity budget exceeded; select a smaller page.")
            if session.assignment_state(assignment.pk) != "VERIFIED":
                continue
            token = choice_token(assignment, actor)
            label = f"{assignment.part} · {assignment.archive_file.pk}"
            options.append((token, label))
            tokens[assignment.pk] = token
        alternatives[arrangement_id] = options, tokens
    for row in context["rows"]:
        position = row["position"]
        if position.arrangement_id is None:
            continue
        options, tokens = alternatives.get(position.arrangement_id, ([], {}))
        for cell in row["cells"]:
            result = cell["resolution"]
            cell["edit_form"] = CellEditForm(
                choices=options,
                prefix=f"cell-{position.pk}-{result.participant_id}",
                initial={
                    "expected_revision": project.revision,
                    "choice": tokens.get(result.assignment_id, ""),
                    **page_values,
                },
            )
            cell["has_choices"] = bool(options)
    for person in context["participants"]:
        person.matrix_default_form = DefaultForm(
            prefix=f"default-{person.pk}",
            initial={"expected_revision": project.revision, "part": person.default_part_id},
        )
    context["page_values"] = page_values
    return context
