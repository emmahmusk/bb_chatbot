import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "local-risk-website-key")
DEBUG = os.getenv("DEBUG", "false").lower() == "true"
ALLOWED_HOSTS = [host.strip() for host in os.getenv("ALLOWED_HOSTS", "*").split(",") if host.strip()]

INSTALLED_APPS = ["django.contrib.staticfiles", "risk_site"]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
]
ROOT_URLCONF = "config.urls"
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {"context_processors": ["django.template.context_processors.static"]},
    }
]
WSGI_APPLICATION = "config.wsgi.application"

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "dist" / "static"
STATICFILES_DIRS = [BASE_DIR / "static"]
# WhiteNoise allows the standalone service to serve source assets locally even
# before a build has populated dist/static. Production still serves the
# collected dist/static directory and CloudFront artifact.
WHITENOISE_USE_FINDERS = os.getenv("WHITENOISE_USE_FINDERS", "true").lower() == "true"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

CONTACT_EMAIL = os.getenv("CONTACT_EMAIL", "risk@bbbprediction.com")
