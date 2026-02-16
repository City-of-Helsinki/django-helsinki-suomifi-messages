from django.conf import settings as django_settings

SUOMIFI_USERNAME = getattr(django_settings, "SUOMIFI_USERNAME", "")
SUOMIFI_PASSWORD = getattr(django_settings, "SUOMIFI_PASSWORD", "")
SUOMIFI_SERVICE_ID = getattr(django_settings, "SUOMIFI_SERVICE_ID", "")
SUOMIFI_TEST_USER_SSN = getattr(django_settings, "SUOMIFI_TEST_USER_SSN", "")
