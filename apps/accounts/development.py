"""Dedicated launcher capability; never arbitrary-user impersonation."""

import secrets

from django.conf import settings
from django.contrib.auth import get_user_model, login
from django.http import Http404
from django.shortcuts import redirect
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET


@never_cache
@require_GET
def development_login(request):
    if (
        not settings.DEVELOPMENT_PROFILE
        or not settings.DEV_LOGIN_TOKEN
        or request.META.get("REMOTE_ADDR") != "127.0.0.1"
        or request.get_host().split(":")[0] != "127.0.0.1"
        or request.META.get("HTTP_X_FORWARDED_FOR")
        or not secrets.compare_digest(request.GET.get("token", ""), settings.DEV_LOGIN_TOKEN)
    ):
        raise Http404
    user, created = get_user_model().objects.get_or_create(
        username="synthetic-local-developer", defaults={"first_name": "Synthetic developer"}
    )
    if created:
        user.set_unusable_password()
        user.save()
    if not user.is_active or user.has_usable_password():
        raise Http404  # Do not alter an existing manually provisioned account.
    login(request, user, backend="django.contrib.auth.backends.ModelBackend")
    response = redirect("home")
    response["Referrer-Policy"] = "no-referrer"
    return response
