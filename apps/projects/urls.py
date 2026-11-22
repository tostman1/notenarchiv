from django.urls import path

from apps.projects import views

urlpatterns = [
    path("", views.project_list, name="project_list"),
    path("new/", views.project_edit, name="project_create"),
    path("<uuid:project_id>/", views.project_detail, name="project_detail"),
    path("<uuid:project_id>/edit/", views.project_edit, name="project_edit"),
    path("<uuid:project_id>/duplicate/", views.project_duplicate, name="project_duplicate"),
    path("<uuid:project_id>/archive/", views.project_archive, name="project_archive"),
]
