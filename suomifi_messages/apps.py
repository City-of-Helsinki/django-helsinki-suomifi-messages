from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class HelsinkiSuomifiMessagesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "suomifi_messages"
    verbose_name = _("Suomi.fi messages")
