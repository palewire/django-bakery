"""Build docs."""
import os
import sys
from datetime import datetime
from pathlib import Path

THIS_DIR = Path(__file__).parent.absolute()

sys.path.insert(0, os.path.abspath(".."))
sys.path.insert(0, str(THIS_DIR.parent))

extensions = [
    "myst_parser",
]

source_suffix = ".md"
master_doc = "index"

project = "django-bakery"
year = datetime.now().year
copyright = f"{year} palewi.re"

exclude_patterns = ["_build"]

html_theme = "palewire"
html_sidebars = {
    "**": [
        "about.html",
        "navigation.html",
    ]
}
html_theme_options = {
    "canonical_url": "https://palewi.re/docs/django-bakery/",
}

html_static_path = ["_static"]
pygments_style = "sphinx"