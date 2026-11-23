from django.urls import path

from apps.exports import selection_views, views

urlpatterns = [
    path("projects/<uuid:project_id>/contents/", selection_views.contents, name="project_contents_export"),
    path("projects/<uuid:project_id>/runs/", selection_views.project_runs, name="project_exports"),
    path("snapshots/<uuid:snapshot_id>/excerpt/", selection_views.historical, name="historical_excerpt"),
    path("runs/<uuid:run_id>/", views.detail, name="generation_detail"),
    path("artifacts/<uuid:artifact_id>/download/", views.download, name="generation_download"),
]
