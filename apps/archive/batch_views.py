"""POST-only explicit batch approval, using individually inspected signed versions."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.shortcuts import redirect
from django.utils.translation import gettext as _
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST

from apps.archive.batch_review import approve_batch


@never_cache
@login_required
@require_POST
def approve(request):
    try:
        jobs = approve_batch(
            request.POST.getlist("versions"), actor=request.user, explicit=request.POST.get("confirm") == "on"
        )
    except (ValueError, ValidationError, OSError):
        messages.error(
            request,
            _(
                "Stapel nicht freigegeben: Auswahl veraltet, ungeprüft, geändert oder widersprüchlich. "
                "Neu laden und jede Version einzeln prüfen. Es wurde kein Teilstapel beauftragt."
            ),
        )
    else:
        messages.success(
            request,
            _("Freigabeaufträge erstellt: %(count)s. Nutzbar erst nach erfolgreicher Publikation.")
            % {"count": len(jobs)},
        )
    return redirect("archive_review_queue")
