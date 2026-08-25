DEFAULT_GOAL := help

UV ?= uv
UV_PYTHON ?=
PYTHON ?= python3
PACKAGE ?= bakery
COVERAGE_FAIL_UNDER ?= 80
DJANGO ?=
TEST_ARGS ?=
PACKAGE_CHECK_DIR ?= .package-check
CHECK_MANIFEST_IGNORE ?= .codespell-ignore-words.txt,.devcontainer/**,.editorconfig,.pre-commit-config.yaml,.python-version,AGENTS.md,CHANGELOG.md,CONTRIBUTING.md,Makefile,RELEASING.md,SECURITY.md,docs/**,example/**,scripts/**,test_settings.py,uv.lock,zizmor.yml
CHECK_WHEEL_IGNORE ?= W002
RUN = $(if $(UV_PYTHON),UV_PYTHON=$(UV_PYTHON)) $(UV) run --no-env-file
TEST_RUN = $(RUN) $(if $(DJANGO),--with "$(DJANGO)")

.PHONY: all help bootstrap install install-all install-dev install-test install-docs check verify diff-check lint format-check format fix type-check dependency-check workflow-check manifest-check test coverage build package-check package-verify docs docs-check docs-navigation-check linkcheck serve-docs hooks clean

help: ## Show available commands
	@awk 'BEGIN {FS = ":.*## "}; /^[a-zA-Z0-9_-]+:.*## / {printf "%-18s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

bootstrap: ## Prepare this checkout and install locked dependencies
	$(PYTHON) scripts/worktree_bootstrap.py --uv "$(UV)"

install: install-all ## Install all development dependencies

install-all: ## Install every dependency group
	$(UV) sync --all-groups --locked

install-dev: ## Install dependencies for static checks
	$(UV) sync --group dev --locked

install-test: ## Install dependencies for tests
	$(UV) sync --group test --locked $(if $(UV_PYTHON),--python $(UV_PYTHON))

install-docs: ## Install dependencies for documentation
	$(UV) sync --group docs --locked

all: verify ## Run the complete verification suite

check: diff-check lint format-check type-check dependency-check workflow-check ## Run fast, non-mutating checks

verify: check test coverage manifest-check build docs-check package-check ## Run all local CI checks

diff-check: ## Check the diff for whitespace errors
	git diff --check

lint: ## Check code with Ruff
	$(RUN) ruff check

format-check: ## Check formatting with Ruff
	$(RUN) ruff format --check

format: ## Format code with Ruff
	$(RUN) ruff format

fix: ## Apply Ruff fixes and formatting
	$(RUN) ruff check --fix
	$(RUN) ruff format

type-check: ## Check static types with ty
	$(RUN) ty check

dependency-check: ## Check dependency declarations with Deptry
	$(RUN) deptry .

workflow-check: ## Audit GitHub Actions workflows with Zizmor
	$(RUN) zizmor .github/workflows

manifest-check: ## Check source distribution contents
	$(RUN) check-manifest --ignore "$(CHECK_MANIFEST_IGNORE)"

test: ## Run tests
	$(TEST_RUN) pytest $(TEST_ARGS)

coverage: ## Enforce test coverage
	$(TEST_RUN) pytest $(TEST_ARGS) --cov="$(PACKAGE)" --cov-branch --cov-report=term-missing:skip-covered --cov-fail-under="$(COVERAGE_FAIL_UNDER)"

build: ## Build source and wheel distributions
	rm -rf dist
	$(UV) build --sdist --wheel
	$(RUN) twine check dist/*

package-check: ## Build, inspect, install, and import the wheel
	@package_check_dir="$(abspath $(PACKAGE_CHECK_DIR))"; \
	rm -rf "$$package_check_dir"; \
	trap 'rm -rf "$$package_check_dir"' EXIT; \
	mkdir -p "$$package_check_dir/dist"; \
	$(UV) build --wheel --out-dir "$$package_check_dir/dist"; \
	$(RUN) check-wheel-contents --ignore "$(CHECK_WHEEL_IGNORE)" "$$package_check_dir"/dist/*.whl; \
	$(UV) venv --no-project "$$package_check_dir/venv"; \
	$(UV) pip install --python "$$package_check_dir/venv/bin/python" "$$package_check_dir"/dist/*.whl; \
	cd "$$package_check_dir" && "$$package_check_dir/venv/bin/python" -c 'from django.conf import settings; settings.configure(INSTALLED_APPS=["$(PACKAGE)"]); import django; django.setup(); import $(PACKAGE).views'

package-verify: package-check coverage ## Verify package and coverage

docs: ## Build HTML documentation
	$(RUN) sphinx-build -M html docs docs/_build

docs-check: ## Build documentation and fail on warnings
	$(RUN) sphinx-build -M html docs docs/_build -W --keep-going
	$(MAKE) docs-navigation-check

docs-navigation-check: ## Check generated documentation navigation
	$(RUN) python scripts/check_docs_navigation.py docs/_build/html

linkcheck: ## Check documentation links
	$(RUN) sphinx-build -M linkcheck docs docs/_build -W --keep-going

serve-docs: ## Serve documentation with live reload
	$(RUN) sphinx-autobuild -b html docs docs/_build/html

hooks: ## Run all pre-commit hooks
	$(RUN) pre-commit run --all-files

clean: ## Remove generated files and caches
	rm -rf build dist $(PACKAGE_CHECK_DIR) docs/_build .coverage htmlcov .pytest_cache .ruff_cache .ty
	find . -maxdepth 1 -type d -name "*.egg-info" -prune -exec rm -rf {} +
	find . -path ./.venv -prune -o -type d -name __pycache__ -prune -exec rm -rf {} +
