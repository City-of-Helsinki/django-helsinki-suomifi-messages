# ruff: noqa: N802 - uppercase property names match Django setting conventions
from typing import TYPE_CHECKING

from django.conf import settings as django_settings

if TYPE_CHECKING:
    USERNAME: str
    PASSWORD: str
    SERVICE_ID: str
    POSTI_EMAIL: str
    POSTI_USERNAME: str
    POSTI_PASSWORD: str


class SuomiFiSettings:
    prefix = "SUOMIFI_"

    def _setting(self, name: str, default):
        return getattr(django_settings, self.prefix + name, default)

    # Suomi.fi credentials

    @property
    def USERNAME(self) -> str:
        return self._setting("USERNAME", "")

    @property
    def PASSWORD(self) -> str:
        return self._setting("PASSWORD", "")

    @property
    def SERVICE_ID(self) -> str:
        return self._setting("SERVICE_ID", "")

    # Posti Messaging Oy credentials for TKJ service.
    # Organizations receive these during paper mail deployment. See:
    # https://kehittajille.suomi.fi/services/messages/deployment/deployment-of-the-printing-enveloping-and-distribution-service

    @property
    def POSTI_EMAIL(self) -> str:
        return self._setting("POSTI_EMAIL", "")

    @property
    def POSTI_USERNAME(self) -> str:
        return self._setting("POSTI_USERNAME", "")

    @property
    def POSTI_PASSWORD(self) -> str:
        return self._setting("POSTI_PASSWORD", "")


_settings = SuomiFiSettings()


def __getattr__(name: str):
    # See https://peps.python.org/pep-0562/
    return getattr(_settings, name)
