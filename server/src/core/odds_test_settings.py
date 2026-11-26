"""Isolated odds integration tests: in-memory DB, no .env or live credentials."""
SECRET_KEY = "odds-integration-tests-only-local-in-memory-key"
INSTALLED_APPS = [
    "django.contrib.auth", "django.contrib.contenttypes", "django.contrib.sessions",
    "taggit", "django_q", "user", "mkt", "betengine", "admin_panel",
]
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
ROOT_URLCONF = "core.odds_test_urls"
USE_TZ = True
MIDDLEWARE = []
ALLOWED_HOSTS = ["testserver"]
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
REST_FRAMEWORK = {"DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework_simplejwt.authentication.JWTAuthentication"]}
OPTIC_ODDS_BASE_URL = "https://example.invalid"
OPTIC_ODDS_API_KEY = ""
OPTIC_ODDS_TIMEOUT_SECONDS = 1
OPTIC_ODDS_PRIMARY_SPORTSBOOK = "draftkings"
OPTIC_ODDS_PRIMARY_SPORTSBOOK_LABEL = "DraftKings"
OPTIC_ODDS_COMPARISON_SPORTSBOOKS = ["draftkings", "fanduel", "pinnacle", "bet365"]
OPTIC_ODDS_AUDIT_MIN_DECIMAL_GAP = .2
OPTIC_ODDS_AUDIT_MIN_RELATIVE_GAP = .1
ADMIN_SERVER_API_KEY = ""
SPORTSBOOK_MODE = "demo"
Q_CLUSTER = {"sync": True, "orm": "default", "timeout": 30, "retry": 60}
