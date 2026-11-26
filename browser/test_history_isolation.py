"""Browser-directory transaction isolation does not require Node or real data."""

import pytest
from django.db import IntegrityError, connection, transaction

from apps.archive.models import LogicalPage


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("occurrence", [1, 2])
def test_browser_history_guards_and_transaction_flush(occurrence):
    assert LogicalPage.objects.count() == 0
    page = LogicalPage.objects.create()
    with (
        pytest.raises(IntegrityError, match="immutable content history"),
        transaction.atomic(),
        connection.cursor() as cursor,
    ):
        cursor.execute("DELETE FROM archive_logicalpage WHERE id = %s", [page.pk.hex])
    assert LogicalPage.objects.filter(pk=page.pk).exists()
