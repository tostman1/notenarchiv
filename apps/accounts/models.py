"""Accounts app: authentication baseline (WP-03).

Only archivists use the application (UI-01): individual authenticated
accounts with identical functional rights. There is no differentiated
business role model and no musician self-service.
"""

from django.db import models


class LoginAttempt(models.Model):
    """Persistent login attempt record used for login rate limiting (OP-03).

    Attempts are keyed by (username, client IP) and pruned after
    PRUNE_AFTER; only failures inside the lockout window count towards
    throttling.
    """

    username = models.CharField(max_length=150)
    ip = models.GenericIPAddressField()
    success = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        indexes = [
            models.Index(
                fields=["username", "ip", "created_at"],
                name="idx_login_attempt_user_ip_time",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.username}@{self.ip} ({'ok' if self.success else 'fail'})"
