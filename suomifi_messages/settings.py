from django.conf import settings as django_settings

# Suomi.fi credentials
SUOMIFI_USERNAME = getattr(django_settings, "SUOMIFI_USERNAME", "")
SUOMIFI_PASSWORD = getattr(django_settings, "SUOMIFI_PASSWORD", "")
SUOMIFI_SERVICE_ID = getattr(django_settings, "SUOMIFI_SERVICE_ID", "")

# Posti Messaging Oy credentials for TKJ service.
# Organizations receive these during paper mail deployment. See:
# https://kehittajille.suomi.fi/services/messages/deployment/deployment-of-the-printing-enveloping-and-distribution-service
SUOMIFI_POSTI_EMAIL = getattr(django_settings, "SUOMIFI_POSTI_EMAIL", "")
SUOMIFI_POSTI_USERNAME = getattr(django_settings, "SUOMIFI_POSTI_USERNAME", "")
SUOMIFI_POSTI_PASSWORD = getattr(django_settings, "SUOMIFI_POSTI_PASSWORD", "")
