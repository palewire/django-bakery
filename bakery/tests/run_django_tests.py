# C:/dev/git_clones/django-bakery/bakery/tests/run_django_tests.py
import os
import sys

import django
from django.core.management import call_command

# --- CRITICAL: Set DJANGO_SETTINGS_MODULE at the very top ---
os.environ["DJANGO_SETTINGS_MODULE"] = "bakery.tests.test_settings"

# --- Adjust Python Path correctly ---
# Get the directory containing this script (e.g., .../django-bakery/bakery/tests/)
this_script_dir = os.path.dirname(os.path.abspath(__file__))

# Navigate two levels up to get the actual project root (e.g., .../django-bakery/)
# This directory contains the 'bakery' package.
actual_project_root = os.path.abspath(os.path.join(this_script_dir, "..", ".."))

# Add the actual project root to sys.path if it's not already there
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
        print(f"DJANGO_SETTINGS_MODULE is currently: {os.environ.get('DJANGO_SETTINGS_MODULE')}")
        print(f"sys.path for debugging: {sys.path}")
        print("Please ensure 'bakery.tests.test_settings' is correctly configured and accessible,")
        print("and that the 'bakery' package can be imported from the locations in sys.path.")
        sys.exit(1)

    print("Running Django tests for 'bakery.tests'...")
    try:
        call_command("test", "bakery.tests", verbosity=2)
    except Exception as e:
        print(f"Error during call_command('test', ...): {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
