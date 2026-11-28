"""WP-18-only URL namespace for future library/review integrations."""

from django.urls import path

from apps.archive import preview_views as views

app_name = "archive_preview"
urlpatterns = [
    path("<uuid:file_id>/", views.viewer, name="viewer"),
    path("<uuid:file_id>/document/", views.document, name="document"),
    path("<uuid:file_id>/thumbnail/<int:page>/", views.thumbnail, name="thumbnail"),
    path("<uuid:file_id>/ocr/<uuid:evidence_id>/", views.ocr_excerpt, name="ocr_excerpt"),
]
