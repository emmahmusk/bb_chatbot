import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "unsafe-local-development-key")
DEBUG = os.getenv("DEBUG", "false").lower() == "true"
ALLOWED_HOSTS = [h.strip() for h in os.getenv("ALLOWED_HOSTS", "*").split(",") if h.strip()]

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.staticfiles",
    "corsheaders",
    "rest_framework",
    "chatbot",
]
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {"context_processors": ["django.template.context_processors.static"]},
    }
]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
]
ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": os.getenv("SQLITE_PATH", str(BASE_DIR / "db.sqlite3")),
    }
}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
# Keep local `runserver` and an already-built static directory resilient when
# a new asset has not yet been collected. Production still runs collectstatic
# in entrypoint.sh; this finder fallback is harmless for the small standalone service.
WHITENOISE_USE_FINDERS = os.getenv("WHITENOISE_USE_FINDERS", "true").lower() == "true"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.AllowAny"],
    "UNAUTHENTICATED_USER": None,
}
CORS_ALLOW_ALL_ORIGINS = os.getenv("CORS_ALLOW_ALL_ORIGINS", "true").lower() == "true"
if not CORS_ALLOW_ALL_ORIGINS:
    CORS_ALLOWED_ORIGINS = [
        origin.strip()
        for origin in os.getenv("CORS_ALLOWED_ORIGINS", "").split(",")
        if origin.strip()
    ]

MARKET_API_BASE_URL = os.getenv("MARKET_API_BASE_URL", "http://localhost:8000").rstrip("/")
MARKET_API_PATH = os.getenv("MARKET_API_PATH", "/bet/markets/")
MARKET_SYNC_PAGE_SIZE = int(os.getenv("MARKET_SYNC_PAGE_SIZE", "100"))
MARKET_SYNC_MAX_PAGES = int(os.getenv("MARKET_SYNC_MAX_PAGES", "100"))
MARKET_API_TIMEOUT_SECONDS = int(os.getenv("MARKET_API_TIMEOUT_SECONDS", "20"))
RAG_TOP_K = int(os.getenv("RAG_TOP_K", "10"))
OPENAI_CHAT_MODEL = os.getenv("OPENAI_CHAT_MODEL", "gpt-5-mini")
OPENAI_EMBEDDING_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
OPENAI_TIMEOUT_SECONDS = int(os.getenv("OPENAI_TIMEOUT_SECONDS", "60"))
OPENAI_MAX_RETRIES = int(os.getenv("OPENAI_MAX_RETRIES", "2"))
AUTO_SYNC_EMPTY_INDEX = os.getenv("AUTO_SYNC_EMPTY_INDEX", "true").lower() == "true"
CONVERSATION_HISTORY_LIMIT = int(os.getenv("CONVERSATION_HISTORY_LIMIT", "12"))
OPTIC_ODDS_BASE_URL = os.getenv("OPTIC_ODDS_BASE_URL", "https://api.opticodds.com/api/v3").rstrip("/")
OPTIC_ODDS_API_KEY = os.getenv("OPTIC_ODDS_API_KEY", "")
OPTIC_ODDS_TIMEOUT_SECONDS = int(os.getenv("OPTIC_ODDS_TIMEOUT_SECONDS", "12"))
OPTIC_ODDS_CATALOG_CACHE_SECONDS = int(os.getenv("OPTIC_ODDS_CATALOG_CACHE_SECONDS", "60"))
