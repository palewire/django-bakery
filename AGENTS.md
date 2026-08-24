# Agent Guide

django-bakery is a Django package that renders database-backed views, feeds,
and model pages to static files. It can publish those files to Amazon S3 and
optionally integrates with Celery.

## Repository structure

- `bakery/`: the package and its Django management commands.
- `bakery/tests/`: the pytest suite and test fixtures.
- `example/`: a small Django project demonstrating the package.
- `docs/`: the Sphinx/MyST documentation site.
- `scripts/`: maintainer and checkout tooling.
- `pyproject.toml`: package metadata and tool configuration.
- `Makefile`: common development and verification commands.

The package supports Python 3.11 and newer and Django 5.2 through 6.1.
Keep public behavior, documentation, and tests aligned when making changes.

## Development workflow

Use the existing project environment or prepare a checkout with:

```sh
make bootstrap
```

The bootstrap uses Git metadata to identify the primary checkout. In a linked
worktree it links the primary checkout's ignored `.env` when one exists and
creates `.env.worktree` with a stable `WORKTREE_ID`, preserving any local
settings. Applications should load `.env` first and `.env.worktree` second when
dotenv support is used.

Useful checks are:

```sh
make check       # lint, formatting, typing, dependency, and workflow checks
make test        # pytest suite
make docs-check  # strict Sphinx build
make verify      # complete local verification
make hooks       # all pre-commit hooks
```

Use `make fix` or `make format` only when source changes are intended.
Do not commit build output, virtual environments, environment files, or
credentials. Do not edit generated lockfiles by hand.

## Worktrees and parallel agents

Edit only the current checkout. Do not modify the primary checkout or sibling
worktrees, and avoid broad reset or clean operations. Coordinate changes to
shared configuration and lockfiles. Tests that use external resources must
use worktree-specific databases, ports, caches, or containers.

## Documentation

Document user-facing behavior in `docs/` and run `make docs-check`. The
documentation is Markdown rendered by Sphinx with the Palewire theme. Keep
project-specific deployment details and examples intact; use host-specific
linkcheck exclusions only for reproducibly unstable URLs.

## Changelog and releases

Add user-facing changes to the appropriate `Unreleased` section in
`CHANGELOG.md`. Follow `RELEASING.md` for versioning, package builds, and
publishing. Agents may prepare release notes and run checks, but must not
create tags, GitHub releases, documentation deployments, or package
publications without explicit human approval.
