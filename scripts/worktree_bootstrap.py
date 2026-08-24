"""Prepare a Git worktree for local development."""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from collections.abc import Sequence

WORKTREE_ID_VARIABLE = "WORKTREE_ID"


class Runner(Protocol):
    """Run commands needed by the bootstrap."""

    def capture(self, command: Sequence[str], cwd: Path) -> str:
        """Run a command and return its standard output."""

    def execute(self, command: Sequence[str], cwd: Path) -> None:
        """Run a command with output attached to the terminal."""


class SubprocessRunner:
    """Run bootstrap commands in subprocesses."""

    def capture(self, command: Sequence[str], cwd: Path) -> str:
        """Run a command and return its standard output."""
        result = subprocess.run(  # noqa: S603 - Commands are never shell strings.
            command,
            cwd=cwd,
            check=True,
            stdout=subprocess.PIPE,
            text=True,
        )
        return result.stdout

    def execute(self, command: Sequence[str], cwd: Path) -> None:
        """Run a command with output attached to the terminal."""
        subprocess.run(  # noqa: S603 - Commands are never shell strings.
            command,
            cwd=cwd,
            check=True,
        )


@dataclass(frozen=True)
class GitCheckout:
    """Paths Git reports for the current and primary checkouts."""

    current: Path
    primary: Path

    @classmethod
    def discover(cls, runner: Runner, cwd: Path) -> GitCheckout:
        """Discover checkout paths from Git metadata."""
        current_output = runner.capture(
            ("git", "rev-parse", "--show-toplevel"),
            cwd,
        )
        current = Path(current_output.strip()).resolve()
        worktree_output = runner.capture(
            ("git", "worktree", "list", "--porcelain"),
            current,
        )
        primary = parse_primary_checkout(worktree_output)
        return cls(current=current, primary=primary)

    @property
    def is_linked_worktree(self) -> bool:
        """Return whether the current checkout is not the primary checkout."""
        return self.current != self.primary


def parse_primary_checkout(output: str) -> Path:
    """Return the primary checkout from Git's porcelain worktree listing."""
    for line in output.splitlines():
        if line.startswith("worktree "):
            return Path(line.removeprefix("worktree ")).resolve()
    msg = "Git did not report a primary checkout."
    raise ValueError(msg)


def worktree_identifier(checkout: Path) -> str:
    """Build a stable, environment-safe identifier for a checkout."""
    resolved = checkout.resolve()
    slug = re.sub(r"[^a-z0-9]+", "-", resolved.name.lower()).strip("-")
    safe_slug = slug or "worktree"
    path_hash = hashlib.sha256(os.fsencode(resolved)).hexdigest()[:8]
    return f"{safe_slug}-{path_hash}"


def ensure_shared_env(checkout: GitCheckout) -> None:
    """Link the primary .env into a linked worktree without overwriting files."""
    if not checkout.is_linked_worktree:
        return

    source = checkout.primary / ".env"
    destination = checkout.current / ".env"
    if not source.exists():
        return

    if destination.is_symlink() and destination.resolve() == source.resolve():
        return
    if destination.exists() or destination.is_symlink():
        msg = f"Refusing to replace existing {destination}."
        raise FileExistsError(msg)

    destination.symlink_to(source)


def ensure_worktree_override(checkout: Path, identifier: str) -> None:
    """Create or update the managed identifier while preserving local settings."""
    override = checkout / ".env.worktree"
    assignment = f"{WORKTREE_ID_VARIABLE}={identifier}"
    if not override.exists():
        override.write_text(
            "# Worktree-local overrides. Load this after .env when supported.\n"
            f"{assignment}\n",
            encoding="utf-8",
        )
        return

    original = override.read_text(encoding="utf-8")
    lines = original.splitlines()
    matching_indexes = [
        index
        for index, line in enumerate(lines)
        if line.startswith(f"{WORKTREE_ID_VARIABLE}=")
    ]
    if len(matching_indexes) > 1:
        msg = f"{override} contains multiple {WORKTREE_ID_VARIABLE} assignments."
        raise ValueError(msg)
    if matching_indexes:
        index = matching_indexes[0]
        if lines[index] == assignment:
            return
        lines[index] = assignment
    else:
        if lines and lines[-1]:
            lines.append("")
        lines.append(assignment)

    override.write_text("\n".join(lines) + "\n", encoding="utf-8")


def bootstrap(cwd: Path, uv: str, runner: Runner) -> GitCheckout:
    """Prepare local environment files and install locked dependencies."""
    checkout = GitCheckout.discover(runner, cwd)
    ensure_shared_env(checkout)
    ensure_worktree_override(
        checkout.current,
        worktree_identifier(checkout.current),
    )
    runner.execute(
        (uv, "sync", "--all-groups", "--locked"),
        checkout.current,
    )
    return checkout


def main() -> None:
    """Run the worktree bootstrap."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--uv", default=os.environ.get("UV", "uv"))
    args = parser.parse_args()

    checkout = bootstrap(Path.cwd(), args.uv, SubprocessRunner())
    location = "linked worktree" if checkout.is_linked_worktree else "primary checkout"
    print(f"Bootstrap complete for {location}.")


if __name__ == "__main__":
    main()
