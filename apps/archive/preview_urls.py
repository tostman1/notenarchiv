"""WP-18-only URL namespace for future library/review integrations."""

from django.urls import path

from apps.archive import preview_views as views

app_name = "archive_preview"
urlpatterns = [
    path("<uuid:file_id>/content/<uuid:revision_id>/", views.content_proposal_viewer, name="content_proposal_viewer"),
    path(
        "<uuid:file_id>/content/<uuid:revision_id>/document/",
        views.content_proposal_document,
        name="content_proposal_document",
    ),
    path("<uuid:file_id>/regions/", views.region_sequence_viewer, name="region_sequence_viewer"),
    path("<uuid:file_id>/regions/document/", views.region_sequence_document, name="region_sequence_document"),
    path("<uuid:file_id>/", views.viewer, name="viewer"),
    path("<uuid:file_id>/document/", views.document, name="document"),
    path("<uuid:file_id>/thumbnail/<int:page>/", views.thumbnail, name="thumbnail"),
    path("<uuid:file_id>/ocr/<uuid:evidence_id>/", views.ocr_excerpt, name="ocr_excerpt"),
    path("<uuid:file_id>/region/<uuid:revision_id>/", views.region_excerpt, name="region_excerpt"),
]
