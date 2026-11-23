from django.apps import AppConfig


class ExportsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.exports"
    label = "exports"

    def ready(self):
        from apps.exports.snapshot_services import register

        register()
