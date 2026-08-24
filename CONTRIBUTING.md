# Contributing

Thank you for helping improve django-bakery. Please open an issue for a
substantial change before starting work, then use a focused branch or linked
worktree for the implementation.

## Set up a checkout

The repository uses `uv` and the dependency groups in `pyproject.toml`.
Bootstrap the current checkout with:

```sh
make bootstrap
```

This installs the locked development, test, and documentation dependencies.
It is safe to run in the primary checkout or a linked Git worktree. In a
linked worktree, the bootstrap links the primary checkout's ignored `.env`
without replacing an existing local file and writes `.env.worktree` with a
stable `WORKTREE_ID`.

Install the Git hooks after bootstrapping:

```sh
uv run pre-commit install --install-hooks
```

## Checks

Run focused tests while developing, then run the complete checks before
opening a pull request:

```sh
make test
make check
make verify
```

`make check` runs Ruff, ty, dependency, workflow, formatting, and diff checks.
`make verify` additionally runs the pytest suite, manifest and package checks,
and the Sphinx documentation build with warnings treated as errors. Run
`make hooks` to execute every pre-commit hook against the repository.

## Documentation

Documentation lives in `docs/` as Markdown processed by Sphinx and MyST.
Build it locally with:

```sh
make docs
make docs-check
make serve-docs
```

Preserve the package's Django and S3 deployment guidance when editing the
documentation. Update the docs for user-facing behavior changes.

## Pull requests

- Keep changes focused and include tests for changed behavior.
- Update documentation and `CHANGELOG.md` for user-facing changes.
- Do not commit `.env`, `.env.worktree`, credentials, build output, or virtual
  environments.
- Explain compatibility or migration considerations in the pull request.
- Confirm the relevant checks pass before requesting review.

For release work, follow [RELEASING.md](RELEASING.md).
