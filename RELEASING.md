# Releasing

django-bakery uses Semantic Versioning and
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/). The package version
is derived from Git tags by `setuptools-scm`; do not edit a version file.

## Release checklist

- [ ] Review the user-facing changes in `CHANGELOG.md`.
- [ ] Move the release entries from `Unreleased` into a dated version section.
- [ ] Choose a major, minor, or patch version according to Semantic Versioning.
- [ ] Run `make check`, `make test`, `make docs-check`, and `make verify`.
- [ ] Build and inspect the distributions with `make build`.
- [ ] Obtain explicit human approval for the version and release.
- [ ] Merge the approved release pull request.
- [ ] With explicit human approval, create the exact version tag on the merge
      commit to trigger the package publication workflow.
- [ ] Confirm the expected release appears on PyPI.
- [ ] Create the GitHub Release from the existing tag, with concise notes from
      the matching changelog section.
- [ ] Confirm the documentation workflow deployed the matching site.

Agents may prepare release notes and run validation, but must not create tags,
GitHub releases, documentation deployments, or package publications without
explicit human approval.

## Verify a tag and GitHub Release

After the release pull request merges, verify that the tag points to its merge
commit before publishing:

```sh
VERSION=0.13.0
EXPECTED_COMMIT=<release-commit>
git fetch origin --tags
test "$(git rev-parse "${VERSION}^{commit}")" = "$EXPECTED_COMMIT"
```

With approval and after the package publication succeeds, create a release
from that existing tag:

```sh
gh release create "$VERSION" \
  --verify-tag \
  --title "$VERSION" \
  --notes-file release-notes.md
```

Verify that it is public and uses the expected tag:

```sh
test "$(gh release view "$VERSION" --json tagName --jq .tagName)" = "$VERSION"
test "$(gh release view "$VERSION" --json isDraft,isPrerelease \
  --jq '(.isDraft == false and .isPrerelease == false)')" = "true"
test "$(git rev-parse "${VERSION}^{commit}")" = "$EXPECTED_COMMIT"
```

Use the repository's GitHub Actions configuration for the authoritative
publication and documentation deployment steps. Never bypass its approval
requirements with a local upload.
