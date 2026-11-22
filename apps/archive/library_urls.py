from django.urls import path

from apps.archive import download_views
from apps.archive import library_views as views
from apps.archive.edition_views import editions

urlpatterns = [
    path("library/", views.library, name="archive_library"),
    path("library/<uuid:arrangement_id>/", views.arrangement_detail, name="archive_library_arrangement"),
    path("library/<uuid:arrangement_id>/parts/<uuid:part_id>/editions/", editions, name="archive_editions"),
    path("notes/<uuid:file_id>/download/", download_views.note, name="archive_note_download"),
    path("notes/selection/", download_views.selection, name="archive_note_selection"),
    path("notes/selection/download/", download_views.download_selection, name="archive_note_selection_download"),
]
