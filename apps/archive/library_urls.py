from django.urls import path

from apps.archive import library_views as views

urlpatterns = [
    path("library/", views.library, name="archive_library"),
    path("library/<uuid:arrangement_id>/", views.arrangement_detail, name="archive_library_arrangement"),
]
