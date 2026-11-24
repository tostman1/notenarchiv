from django.urls import path

from apps.exports import archive_views, selection_views, views

urlpatterns = [
    path("archive/print/", archive_views.generate, name="archive_print_export"),
    path("runs/<uuid:run_id>/print/", views.print_run, name="generation_print"),
    path("artifacts/<uuid:artifact_id>/preview/", views.viewer, name="generation_preview"),
    path("projects/<uuid:project_id>/contents/", selection_views.contents, name="project_contents_export"),
    path("projects/<uuid:project_id>/runs/", selection_views.project_runs, name="project_exports"),
    path("snapshots/<uuid:snapshot_id>/excerpt/", selection_views.historical, name="historical_excerpt"),
    path("runs/<uuid:run_id>/", views.detail, name="generation_detail"),
    path("artifacts/<uuid:artifact_id>/download/", views.download, name="generation_download"),
]
