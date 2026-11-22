from django.urls import path

from apps.projects import ensemble_views, list_views, participant_views, views

urlpatterns = [
    path("<uuid:project_id>/ensemble/", ensemble_views.overview, name="project_ensemble"),
    path("<uuid:project_id>/ensemble/roles/new/", ensemble_views.role_edit, name="ensemble_role_create"),
    path("<uuid:project_id>/ensemble/roles/<uuid:role_id>/", ensemble_views.role_edit, name="ensemble_role_edit"),
    path("<uuid:project_id>/ensemble/mappings/new/", ensemble_views.mapping_edit, name="ensemble_mapping_create"),
    path(
        "<uuid:project_id>/ensemble/mappings/<uuid:mapping_id>/",
        ensemble_views.mapping_edit,
        name="ensemble_mapping_edit",
    ),
    path(
        "<uuid:project_id>/ensemble/people/<uuid:participant_id>/",
        ensemble_views.participant_role,
        name="ensemble_participant_role",
    ),
    path(
        "<uuid:project_id>/ensemble/roles/<uuid:record_id>/state/",
        ensemble_views.state,
        {"kind": "role"},
        name="ensemble_role_state",
    ),
    path(
        "<uuid:project_id>/ensemble/mappings/<uuid:record_id>/clear/",
        ensemble_views.state,
        {"kind": "mapping"},
        name="ensemble_mapping_clear",
    ),
    path("", views.project_list, name="project_list"),
    path("new/", views.project_edit, name="project_create"),
    path("<uuid:project_id>/", views.project_detail, name="project_detail"),
    path("<uuid:project_id>/edit/", views.project_edit, name="project_edit"),
    path("<uuid:project_id>/duplicate/", views.project_duplicate, name="project_duplicate"),
    path("<uuid:project_id>/archive/", views.project_archive, name="project_archive"),
    path("<uuid:project_id>/pieces/", list_views.piece_list, name="project_piece_list"),
    path("<uuid:project_id>/pieces/library/", list_views.library_selection, name="project_library_selection"),
    path("<uuid:project_id>/pieces/change/", list_views.mutate, name="project_piece_change"),
    path("<uuid:project_id>/participants/", participant_views.participants, name="project_participants"),
    path("<uuid:project_id>/participants/select/", participant_views.select, name="project_participant_select"),
    path("<uuid:project_id>/participants/guest/", participant_views.guest, name="project_guest_add"),
    path(
        "<uuid:project_id>/participants/<uuid:participant_id>/default/",
        participant_views.default,
        name="project_participant_default",
    ),
    path(
        "<uuid:project_id>/participants/<uuid:participant_id>/change/",
        participant_views.change,
        name="project_participant_change",
    ),
]
