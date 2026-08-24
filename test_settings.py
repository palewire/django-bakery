"""Django settings for the test suite."""

from pathlib import Path

TESTS_DIR = Path(__file__).parent / "bakery" / "tests"

SECRET_KEY = "django-bakery-tests"  # noqa: S105
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}
INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.staticfiles",
    "bakery",
]
MIDDLEWARE = []
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [TESTS_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {"context_processors": []},
    }
]
DEFAULT_AUTO_FIELD = "django.db.models.AutoField"
BUILD_DIR = str(TESTS_DIR / "_dist")
STATIC_ROOT = TESTS_DIR / "static"
STATIC_URL = "/static/"
MEDIA_ROOT = TESTS_DIR / "media"
MEDIA_URL = "/media/"
BAKERY_VIEWS = ("bakery.tests.MockDetailView",)
AWS_ACCESS_KEY_ID = "MOCK_ACCESS_KEY_ID"
AWS_SECRET_ACCESS_KEY = "MOCK_SECRET_ACCESS_KEY"  # noqa: S105
AWS_BUCKET_NAME = "mock_bucket"
AWS_REGION = "us-west-1"
CELERY_BROKER_URL = "memory://"
