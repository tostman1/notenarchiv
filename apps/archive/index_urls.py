from django.urls import path

from apps.archive import index_views as views

urlpatterns = [
    path("index/", views.overview, name="archive_index"),
    path("index/start/", views.start, name="archive_index_start"),
    path("index/folders/<uuid:folder_id>/", views.folder_detail, name="archive_index_folder"),
    path("review/", views.review_queue, name="archive_review_queue"),
]
