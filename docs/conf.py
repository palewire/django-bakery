"""Configuration file for the Sphinx documentation builder."""

import sys
from datetime import UTC, datetime
from importlib.metadata import metadata
from importlib.metadata import version as distribution_version
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

distribution = metadata("django-bakery")
project = distribution["Name"]
author = distribution.get("Author") or distribution.get("Author-email", "")
version = distribution_version("django-bakery")
release = version
if version.startswith("0.1.dev"):
    msg = (
        "django-bakery documentation received a setuptools-scm fallback version. "
        "Build from a checkout with Git tags and history."
    )
    raise RuntimeError(msg)
year = datetime.now(UTC).year
copyright = f"{year}, {author}"

language = "en"
templates_path = ["_templates"]
html_static_path = ["_static"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]
pygments_style = "sphinx"

extensions = [
    "myst_parser",
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.intersphinx",
    "sphinx.ext.napoleon",
]

source_suffix = {".md": "markdown", ".rst": "restructuredtext"}
master_doc = "index"
autodoc_member_order = "bysource"
autodoc_typehints = "description"
autodoc_default_options = {
    "members": True,
    "member-order": "bysource",
    "special-members": "__init__",
    "undoc-members": True,
    "show-inheritance": True,
}
autosummary_generate = True

nitpicky = True
intersphinx_mapping = {
    "django": ("https://docs.djangoproject.com/en/stable/", None),
    "python": ("https://docs.python.org/3", None),
}

linkcheck_timeout = 10
linkcheck_retries = 2

html_theme = "palewire"
html_theme_options = {
    "canonical_url": "https://palewi.re/docs/django-bakery/",
}
html_sidebars = {"**": ["navigation.html", "searchbox.html"]}
