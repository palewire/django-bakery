from django.apps import AppConfig


class BakeryTestsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"  # Or your preferred field
    name = "bakery.tests"
    label = "bakery_tests"  # Optional: a unique label if 'bakery.tests' is too long or conflicts
