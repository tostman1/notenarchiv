"""Schema-3 personal content assembly from historical relational pins only.

This service does not enable project authorization or replace schema-1 generation.
"""

from django.core.exceptions import ValidationError

from apps.exports.content_generation import render_editions
from apps.exports.project_content_inputs import load_project_content_pins


def personal_content_pieces(snapshot, participant_id, processor):
    participant = str(participant_id)
    payload = snapshot.payload
    if participant not in {person["id"] for person in payload.get("participants", [])}:
        raise ValidationError("Participant is outside the pinned project snapshot")
    resolved = load_project_content_pins(snapshot, checkpoint=processor.checkpoint)
    positions = payload.get("positions", [])
    if len(positions) > 1000 or len({position["id"] for position in positions}) != len(positions):
        raise ValidationError("Invalid project content position inventory")
    cells = [cell for cell in payload.get("cells", []) if cell["participant_id"] == participant]
    by_position = {cell["position_id"]: cell for cell in cells}
    if len(cells) != len(by_position) or set(by_position) != {position["id"] for position in positions}:
        raise ValidationError("Project content cell inventory mismatch")
    editions, titles, music_positions = [], [], []
    result = []
    acknowledged = set(snapshot.acknowledgements)
    for position in positions:
        cell = by_position[position["id"]]
        key = (position["id"], participant)
        state = cell["status"]
        if state in {"AVAILABLE", "SUBSTITUTED"}:
            if key not in resolved:
                raise ValidationError("Usable content cell has no historical pin")
            editions.append(resolved[key])
            titles.append(position["title"])
            music_positions.append(len(result))
            result.append(None)
        elif state in {"MISSING", "RESERVE"}:
            if key in resolved or (state == "RESERVE") != (position["arrangement"] == "None"):
                raise ValidationError("Invalid pinned placeholder identity")
            if state == "MISSING" and f"{key[0]}:{key[1]}" not in acknowledged:
                raise ValidationError("Missing project content requires acknowledgement")
            result.append({"number": position["order"], "title": position["title"], "state": state, "data": None})
        else:
            raise ValidationError("Unavailable project content cannot be generated")
    rendered = render_editions(editions, titles, processor)
    for index, piece in zip(music_positions, rendered, strict=True):
        piece["number"] = positions[index]["order"]
        result[index] = piece
    return result
