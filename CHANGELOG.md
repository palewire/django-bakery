# Changelog

All notable changes to django-bakery are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow
[Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

- Add optional rooted Amazon S3 build output with
  `BAKERY_FILESYSTEM="s3://bucket[/prefix]"`.
- Add a uv-based development container and worktree-aware bootstrap command.
- Add contributor, agent, release, and security guidance.

### Changed

- Modernize repository quality checks, editor settings, and documentation
  tooling.
- Replace PyFilesystem2 with fsspec for documented local and memory output
  backends.

### Fixed

- Keep filesystem output paths rooted when using Windows drive roots and empty
  build-directory settings.
- Reject unrooted filesystem root operations and unsupported legacy filesystem
  plugin URLs.

### Removed

- Remove the unmaintained PyFilesystem2 (`fs`) dependency, which imported the
  `pkg_resources` module removed in setuptools 81. Uninstall `fs` and any
  PyFilesystem backend, such as `fs-s3fs`, when upgrading.

### Security

[Unreleased]: https://github.com/palewire/django-bakery/compare/v0.12.7...HEAD
[v0.12.7]: https://github.com/palewire/django-bakery/releases/tag/v0.12.7
