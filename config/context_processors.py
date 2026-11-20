"""Expose the shared diagnostic mode in authenticated application navigation."""

from django.conf import settings


def diagnostics(_request):
    return {"diagnostics_enabled": settings.DEBUG_MODE, "release_version": settings.RELEASE_VERSION}
