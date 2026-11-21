"""Bounded archive metadata validation; never log business data."""

import json
import math

from django.core.exceptions import ObjectDoesNotExist, ValidationError

from core.paths import relative_path


def path_value(value, *, allow_root=False):
    try:
        return relative_path(value, allow_root=allow_root)
    except ValueError:
        raise ValidationError("A canonical relative path is required.") from None


def bounded_json(value, *, maximum=16_384):
    try:
        size = len(json.dumps(value, allow_nan=False).encode("utf-8"))
    except (ValueError, TypeError, RecursionError):
        raise ValidationError("Invalid bounded archive metadata.") from None
    if size > maximum:
        raise ValidationError("Archive metadata exceeds its limit.")


def page_metadata(value):
    if not isinstance(value, list) or len(value) > 1000:
        raise ValidationError("Invalid bounded page metadata.")
    bounded_json(value, maximum=524_288)
    keys = {"media_box", "crop_box", "user_unit", "rotation", "width_points", "height_points"}
    for page in value:
        if not isinstance(page, dict) or set(page) != keys:
            raise ValidationError("Invalid page geometry.")
        for name in ("media_box", "crop_box"):
            box = page[name]
            if (
                not isinstance(box, (list, tuple))
                or len(box) != 4
                or any(type(n) not in (int, float) or not math.isfinite(n) for n in box)
                or box[2] <= box[0]
                or box[3] <= box[1]
            ):
                raise ValidationError("Invalid page geometry.")
        for name, maximum in (("user_unit", 75000), ("width_points", 14400), ("height_points", 14400)):
            number = page[name]
            if type(number) not in (int, float) or not math.isfinite(number) or not 0 < number <= maximum:
                raise ValidationError("Invalid page geometry.")
        if type(page["rotation"]) is not int or page["rotation"] not in (0, 90, 180, 270):
            raise ValidationError("Invalid page rotation.")


def reference(instance, field):
    try:
        return getattr(instance, field)
    except ObjectDoesNotExist:
        raise ValidationError({field: "Invalid protected reference."}) from None


def region_metadata(value):
    if not isinstance(value, dict):
        raise ValidationError("Invalid recognition region.")
    bounded_json(value, maximum=1024)
    if not value:
        return
    if set(value) != {"page", "box", "unit"} or value["unit"] not in {"POINTS", "PIXELS", "NORMALIZED"}:
        raise ValidationError("Invalid recognition region.")
    box = value["box"]
    if (
        type(value["page"]) is not int
        or not 0 <= value["page"] < 1000
        or not isinstance(box, list)
        or len(box) != 4
        or any(type(n) not in (int, float) or not math.isfinite(n) or n < 0 for n in box)
        or box[2] <= box[0]
        or box[3] <= box[1]
        or (value["unit"] == "NORMALIZED" and max(box) > 1)
    ):
        raise ValidationError("Invalid recognition region.")
