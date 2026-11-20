"""Login rate limiting service (OP-03).

Constant threshold: after MAX_FAILURES failed logins for the same
(username, IP) pair inside LOCKOUT_WINDOW, further attempts are rejected
before any password check happens. A successful login clears recent
failures for that pair. Old rows are pruned opportunistically.
"""

from __future__ import annotations

from datetime import timedelta

from django.utils import timezone

from apps.accounts.models import LoginAttempt

MAX_FAILURES = 10
LOCKOUT_WINDOW = timedelta(minutes=15)
PRUNE_AFTER = timedelta(hours=24)


def login_throttled(username: str, ip: str) -> bool:
    """True when the (username, IP) pair has too many recent failures."""
    if not username:
        return False
    now = timezone.now()
    return (
        LoginAttempt.objects.filter(
            username__iexact=username,
            ip=ip,
            success=False,
            created_at__gte=now - LOCKOUT_WINDOW,
        ).count()
        >= MAX_FAILURES
    )


def record_login_failure(username: str, ip: str) -> None:
    if not username:
        return
    _prune_old_attempts()
    LoginAttempt.objects.create(username=username[:150], ip=ip, success=False)


def record_login_success(username: str, ip: str) -> None:
    """A successful login clears recent attempts for the pair."""
    if not username:
        return
    now = timezone.now()
    LoginAttempt.objects.filter(
        username__iexact=username,
        ip=ip,
        created_at__gte=now - LOCKOUT_WINDOW,
    ).delete()


def _prune_old_attempts() -> None:
    LoginAttempt.objects.filter(created_at__lt=timezone.now() - PRUNE_AFTER).delete()
