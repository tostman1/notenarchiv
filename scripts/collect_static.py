"""Build-time static collection without secrets, databases or deployment roots."""

import django
from django.conf import settings
from django.core.management import call_command

settings.configure(
    DEBUG=False,
    INSTALLED_APPS=["django.contrib.staticfiles"],
    STATIC_URL="/static/",
    STATIC_ROOT="/opt/staticfiles",
    STATICFILES_DIRS=["/build/static"],
)
django.setup()
call_command("collectstatic", interactive=False, verbosity=0)
