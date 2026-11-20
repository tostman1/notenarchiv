"""A test-only URL configuration whose views always fail, used to verify
that 500 responses are sanitized (no traceback) with DEBUG=False."""

from __future__ import annotations

from django.http import HttpResponse
from django.urls import path


def boom(_request) -> HttpResponse:
    raise RuntimeError("intentional test failure")


urlpatterns = [
    path("boom", boom, name="boom"),
]
