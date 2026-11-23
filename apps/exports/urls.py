from django.urls import path

from apps.exports import views

urlpatterns = [
    path("runs/<uuid:run_id>/", views.detail, name="generation_detail"),
    path("artifacts/<uuid:artifact_id>/download/", views.download, name="generation_download"),
]
