"""Historical schema-3 cell reader; never consult current edition preferences."""

from django.core.exceptions import ValidationError

from apps.exports.content_inputs import load_content


def load_project_content_pins(snapshot, *, checkpoint=lambda: None):
    from apps.projects.preflight_services import fingerprint

    snapshot.full_clean()
    if snapshot.sha256 != fingerprint(snapshot.payload) or snapshot.preflight_sha256 != snapshot.sha256:
        raise ValidationError("Project content snapshot fingerprint mismatch.")
    if snapshot.payload.get("schema") != 3 or snapshot.kind not in {"FULL", "EXCERPT"}:
        raise ValidationError("Unsupported project content snapshot schema.")
    expected = {}
    for cell in snapshot.payload.get("cells", []):
        if "content" not in cell:
            continue
        key = (cell["position_id"], cell["participant_id"])
        if key in expected:
            raise ValidationError("Duplicate project content cell.")
        expected[key] = cell
    pins = list(
        snapshot.project_content_inputs.select_related("confirmation__inspection__revision", "position", "participant")
    )
    if len(pins) != len(expected) or len(pins) > 5000:
        raise ValidationError("Project content pin inventory mismatch.")
    resolved = {}
    for pin in pins:
        checkpoint()
        key = (str(pin.position_id), str(pin.participant_id))
        if key not in expected or key in resolved:
            raise ValidationError("Unexpected project content cell pin.")
        pin.full_clean()
        resolved[key] = load_content(pin.payload)
        checkpoint()
    return resolved
