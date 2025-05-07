# C:/dev/git_clones/django-bakery/bakery/tests/run_django_tests.py
import os
import sys

import django
from django.core.management import call_command

# --- CRITICAL: Set DJANGO_SETTINGS_MODULE at the very top ---
os.environ["DJANGO_SETTINGS_MODULE"] = "bakery.tests.test_settings"

# --- Adjust Python Path correctly ---
this_script_dir = os.path.dirname(os.path.abspath(__file__))
actual_project_root = os.path.abspath(os.path.join(this_script_dir, "..", ".."))

if actual_project_root not in sys.path:
    sys.path.insert(0, actual_project_root)


def main():
    """
    Configures Django settings for testing and runs the test suite
    using Django's native test runner.
    """
    try:
        print(f"Attempting Django setup with settings: {os.environ['DJANGO_SETTINGS_MODULE']}")
        # print(f"Current sys.path: {sys.path}") # Uncomment for debugging sys.path
        django.setup()
        print("Django setup successful.")
    except Exception as e:
        print(f"Error during django.setup(): {e}")
        settings_module = os.environ.get("DJANGO_SETTINGS_MODULE")
        if settings_module:
            print(f"DJANGO_SETTINGS_MODULE was: {settings_module}")
        # It's useful to print sys.path here to confirm the environment
        print(f"sys.path for debugging: {sys.path}")
        print("This error (AppRegistryNotReady or similar) often indicates that Django models")
        print("are being imported at the module level in your application or test files")
        print("before Django's app loading mechanism is fully initialized.")
        print("Consider delaying model imports (e.g., into setUpClass or test methods).")
        sys.exit(1)

    print("Running Django tests for 'bakery.tests'...")
    try:
        call_command("test", "bakery.tests", verbosity=3)
    except Exception as e:
        print(f"Error during call_command('test', ...): {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
