"""
Test Settings for the test suite
"""

import tempfile
from pathlib import Path

# Define a base directory for the tests module
# This helps in constructing paths relative to the 'tests' directory
TESTS_DIR = Path(__file__).resolve().parent

DATABASES = {
    "default": {
        "NAME": TESTS_DIR / "test.db",  # Store test.db inside the tests directory
        "TEST_NAME": TESTS_DIR / "test.db",
        "ENGINE": "django.db.backends.sqlite3",
    },
}

INSTALLED_APPS = (
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.staticfiles",
    "bakery",
    "bakery.tests",  # Add this if you have an apps.py in bakery/tests for
    # app-specific test templates/models
)

MIDDLEWARE_CLASSES = ()  # Kept for compatibility if any old code references it
MIDDLEWARE = []  # Modern Django uses MIDDLEWARE

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [
            TESTS_DIR / "templates",  # Path to your test templates
        ],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                # Add necessary context processors if your test templates need them
                # e.g., 'django.template.context_processors.request',
            ],
        },
    },
]

# Important: For tests that write to BUILD_DIR, it's best practice for each test
# or test class to use its own unique temporary directory.
# Pytest's `tmp_path` fixture is ideal for this.
# Setting a global temp dir here can lead to issues with parallel tests
# or tests not cleaning up after themselves properly.
# Consider removing this global BUILD_DIR and refactoring tests to use tmp_path.
# If you must have a default, ensure it's clearly understood to be a shared temporary space.
BUILD_DIR = tempfile.mkdtemp(prefix="django_bakery_test_build_")

STATIC_ROOT = TESTS_DIR / "static_root_for_tests"  # A dedicated static root for test collection
STATIC_URL = "/static/"

MEDIA_ROOT = TESTS_DIR / "media_root_for_tests"  # A dedicated media root for tests
MEDIA_URL = "/media/"

# Ensure these directories exist if collectstatic or file uploads are tested
STATIC_ROOT.mkdir(parents=True, exist_ok=True)
MEDIA_ROOT.mkdir(parents=True, exist_ok=True)


BAKERY_VIEWS = ("bakery.tests.MockDetailView",)  # As in your original command

# AWS settings for Moto mocking
AWS_ACCESS_KEY_ID = "MOCK_ACCESS_KEY_ID"
AWS_SECRET_ACCESS_KEY = "MOCK_SECRET_ACCESS_KEY"
AWS_S3_BUCKET_NAME = "mock_bucket"  # Renamed from AWS_BUCKET_NAME for consistency
AWS_REGION = "us-west-1"
# For moto, sometimes setting AWS_DEFAULT_REGION via os.environ is also helpful
# os.environ['AWS_DEFAULT_REGION'] = AWS_REGION

# Celery configuration for tests (if celery tasks are tested)
# Using a synchronous backend for tests is often simpler
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
BROKER_URL = (
    "memory://"  # In-memory broker for tests, or 'django://' if using django-celery-results
)
CELERY_BROKER_URL = "memory://"
CELERY_RESULT_BACKEND = "rpc://"  # Or 'django-db' if using django-celery-results

# Minimal required settings for Django to run
SECRET_KEY = "dummy_secret_key_for_testing"
ROOT_URLCONF = "bakery.tests.urls"  # Assuming you have a urls.py in bakery/tests for test views
USE_TZ = True  # Good practice to set this explicitly
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# If 'bakery.tests' is in INSTALLED_APPS, you might need a minimal apps.py:
# bakery/tests/apps.py
# from django.apps import AppConfig
# class BakeryTestsConfig(AppConfig):
#     name = 'bakery.tests'
#     default_auto_field = 'django.db.models.BigAutoField'
