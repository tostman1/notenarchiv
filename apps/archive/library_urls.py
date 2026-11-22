from django.urls import path

from apps.archive import library_views as views
from apps.archive.edition_views import editions

urlpatterns = [
    path("library/", views.library, name="archive_library"),
    path("library/<uuid:arrangement_id>/", views.arrangement_detail, name="archive_library_arrangement"),
    path("library/<uuid:arrangement_id>/parts/<uuid:part_id>/editions/", editions, name="archive_editions"),
]
