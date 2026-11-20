"""Exactly one controlled regular assignment; equal names remain separate."""

from apps.catalog.forms import RecordForm
from apps.members.models import Member


class MemberForm(RecordForm):
    class Meta:
        model = Member
        fields = ["name", "membership_id", "regular_part", "active"]
