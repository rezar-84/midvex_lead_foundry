from __future__ import annotations

import hashlib
import os
import sys
from pathlib import Path
from urllib.parse import urlparse

BASE_DIR = Path(__file__).resolve().parent.parent

TESTING = any("pytest" in argument for argument in sys.argv)
DEBUG = os.getenv("DJANGO_DEBUG", "true").lower() == "true"
DEVELOPMENT_SECRET = hashlib.sha256(f"lead-foundry:{BASE_DIR}".encode()).hexdigest()
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", DEVELOPMENT_SECRET)
if not DEBUG and SECRET_KEY == DEVELOPMENT_SECRET:
    raise RuntimeError("DJANGO_SECRET_KEY is required when DJANGO_DEBUG is false")

ALLOWED_HOSTS = [
    host for host in os.getenv("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if host
]
CSRF_TRUSTED_ORIGINS = [
    origin for origin in os.getenv("DJANGO_CSRF_TRUSTED_ORIGINS", "").split(",") if origin
]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "foundry",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "foundry.middleware.MFARequiredMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]
if not TESTING:
    MIDDLEWARE.insert(1, "whitenoise.middleware.WhiteNoiseMiddleware")

ROOT_URLCONF = "lead_foundry.urls"
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "foundry.context_processors.active_membership",
            ],
        },
    }
]
WSGI_APPLICATION = "lead_foundry.wsgi.application"


def database_config() -> dict[str, object]:
    url = os.getenv("DATABASE_URL")
    if not url:
        if not DEBUG and not TESTING:
            raise RuntimeError("DATABASE_URL is required outside development/tests")
        return {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "db.sqlite3"}
    parsed = urlparse(url)
    if parsed.scheme not in {"postgres", "postgresql"}:
        raise RuntimeError("DATABASE_URL must use PostgreSQL")
    return {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": parsed.path.lstrip("/"),
        "USER": parsed.username,
        "PASSWORD": parsed.password,
        "HOST": parsed.hostname,
        "PORT": parsed.port or 5432,
        "CONN_MAX_AGE": 60,
        "OPTIONS": {"sslmode": os.getenv("DATABASE_SSLMODE", "prefer")},
    }


DATABASES = {"default": database_config()}
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 12},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
]


def _languages_from_env() -> list[tuple[str, str]]:
    raw = os.getenv("DJANGO_LANGUAGES", "en=English,tr=Türkçe")
    pairs = []
    for entry in raw.split(","):
        code, _, label = entry.strip().partition("=")
        if code:
            pairs.append((code, label or code))
    return pairs


LANGUAGE_CODE = os.getenv("DJANGO_LANGUAGE_CODE", "en")
LANGUAGES = _languages_from_env()
TIME_ZONE = os.getenv("DJANGO_TIME_ZONE", "Europe/Istanbul")
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
# Vite emits the SPA bundle here; collectstatic picks it up so WhiteNoise serves it.
_FRONTEND_DIST = BASE_DIR / "frontend" / "dist"
STATICFILES_DIRS = [_FRONTEND_DIST] if _FRONTEND_DIST.exists() else []
STORAGES = {
    "staticfiles": {
        "BACKEND": (
            "django.contrib.staticfiles.storage.StaticFilesStorage"
            if TESTING
            else "whitenoise.storage.CompressedManifestStaticFilesStorage"
        )
    }
}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "login"
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_AGE = 60 * 60 * 12
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = not DEBUG
SECURE_HSTS_SECONDS = int(os.getenv("SECURE_HSTS_SECONDS", "31536000" if not DEBUG else "0"))
SECURE_HSTS_INCLUDE_SUBDOMAINS = not DEBUG
SECURE_HSTS_PRELOAD = False
SILENCED_SYSTEM_CHECKS = ["security.W008"] if DEBUG or TESTING else []

CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60
CELERY_TASK_SOFT_TIME_LIMIT = 25 * 60
CELERY_TASK_ALWAYS_EAGER = (
    os.getenv("CELERY_TASK_ALWAYS_EAGER", "true" if DEBUG else "false").lower() == "true"
)

TOKEN_ENCRYPTION_KEY = os.getenv("TOKEN_ENCRYPTION_KEY", "")
RAW_STORAGE_BACKEND = os.getenv("RAW_STORAGE_BACKEND", "filesystem" if DEBUG else "s3")
RAW_STORAGE_ROOT = Path(os.getenv("RAW_STORAGE_ROOT", BASE_DIR / ".raw-evidence"))
S3_ENDPOINT_URL = os.getenv("S3_ENDPOINT_URL", "")
S3_BUCKET = os.getenv("S3_BUCKET", "")
S3_ACCESS_KEY_ID = os.getenv("S3_ACCESS_KEY_ID", "")
S3_SECRET_ACCESS_KEY = os.getenv("S3_SECRET_ACCESS_KEY", "")

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
FOUNDRY_BRAND_NAME = os.getenv("FOUNDRY_BRAND_NAME", "Lead Foundry")
FOUNDRY_USER_AGENT = os.getenv(
    "FOUNDRY_USER_AGENT",
    "LeadFoundry/0.1 (+self-hosted research; contact instance operator)",
)

GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "")
GMAIL_REAL_DATA_ENABLED = os.getenv("GMAIL_REAL_DATA_ENABLED", "false").lower() == "true"
SOURCE_NETWORK_ENABLED = os.getenv("SOURCE_NETWORK_ENABLED", "false").lower() == "true"
ENRICHMENT_NETWORK_ENABLED = os.getenv("ENRICHMENT_NETWORK_ENABLED", "false").lower() == "true"
ENRICHMENT_EGRESS_PROXY = os.getenv("ENRICHMENT_EGRESS_PROXY", "")
ENRICHMENT_MAX_RESPONSE_BYTES = int(os.getenv("ENRICHMENT_MAX_RESPONSE_BYTES", "2000000"))
ENRICHMENT_REQUEST_TIMEOUT = float(os.getenv("ENRICHMENT_REQUEST_TIMEOUT", "15"))

# Rspamd/ClamAV endpoints and AI-provider settings were removed: nothing read
# them. MVX-004 (scanning) and MVX-006 (AI-assisted ranking) reintroduce them
# together with real consumers.
MAX_MESSAGE_BYTES = int(os.getenv("MAX_MESSAGE_BYTES", str(25 * 1024 * 1024)))
