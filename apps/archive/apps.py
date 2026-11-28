from django.apps import AppConfig


class ArchiveConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.archive"
    label = "archive"

    def ready(self):
        from apps.archive.publication import register

        register()
        from apps.archive.indexing import register as register_indexing

        register_indexing()
        from apps.archive.ocr_services import register as register_ocr

        register_ocr()
