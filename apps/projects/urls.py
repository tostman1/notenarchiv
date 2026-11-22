from django.urls import path

from apps.projects import list_views, views

urlpatterns = [
    path("", views.project_list, name="project_list"),
    path("new/", views.project_edit, name="project_create"),
    path("<uuid:project_id>/", views.project_detail, name="project_detail"),
    path("<uuid:project_id>/edit/", views.project_edit, name="project_edit"),
    path("<uuid:project_id>/duplicate/", views.project_duplicate, name="project_duplicate"),
    path("<uuid:project_id>/archive/", views.project_archive, name="project_archive"),
    path("<uuid:project_id>/pieces/", list_views.piece_list, name="project_piece_list"),
    path("<uuid:project_id>/pieces/library/", list_views.library_selection, name="project_library_selection"),
    path("<uuid:project_id>/pieces/change/", list_views.mutate, name="project_piece_change"),
]
