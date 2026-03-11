from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = "secret"

DEBUG = True


INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "tests",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "tests.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}


USE_TZ = True


STATIC_URL = "static/"

LANGUAGE_CODE = "en"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Library settings

# Suomi.fi test credentials
SUOMIFI_USERNAME = "suomifi_username"
SUOMIFI_PASSWORD = "suomifi_password"
SUOMIFI_SERVICE_ID = "suomifi_service_id"

# Posti test credentials
SUOMIFI_POSTI_EMAIL = "suomifi_posti_email"
SUOMIFI_POSTI_USERNAME = "suomifi_posti_username"
SUOMIFI_POSTI_PASSWORD = "suomifi_posti_password"
