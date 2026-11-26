from django.urls import path

from apps.exports import archive_views, content_preference_views, content_views, library_views, selection_views, views

urlpatterns = [
    path("content/<uuid:edition_id>/preference/", content_preference_views.edit, name="content_preference"),
    path("content/generate/", content_views.generate, name="content_generated_export"),
    path("", library_views.library, name="export_library"),
    path("batch-download/", library_views.batch_download, name="export_batch_download"),
    path("artifacts/<uuid:artifact_id>/regenerate/", library_views.regenerate, name="export_regenerate"),
    path("archive/generate/", archive_views.generate, {"variant": "READING"}, name="archive_generated_export"),
    path("archive/print/", archive_views.generate, name="archive_print_export"),
    path("runs/<uuid:run_id>/print/", views.print_run, name="generation_print"),
    path("artifacts/<uuid:artifact_id>/preview/", views.viewer, name="generation_preview"),
    path("projects/<uuid:project_id>/contents/", selection_views.contents, name="project_contents_export"),
    path("projects/<uuid:project_id>/runs/", selection_views.project_runs, name="project_exports"),
    path("snapshots/<uuid:snapshot_id>/excerpt/", selection_views.historical, name="historical_excerpt"),
    path("runs/<uuid:run_id>/", views.detail, name="generation_detail"),
    path("artifacts/<uuid:artifact_id>/download/", views.download, name="generation_download"),
]
