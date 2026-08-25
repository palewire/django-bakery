"""Verify the generated documentation navigation contract."""

from __future__ import annotations

import argparse
import re
from html.parser import HTMLParser
from pathlib import Path
from typing import Final

EXPECTED_PAGE_LINKS: Final = {
    "gettingstarted.html": "Getting started",
    "buildableviews.html": "Buildable views",
}


class SidebarNavigationParser(HTMLParser):
    """Collect links rendered inside the desktop documentation navigation."""

    def __init__(self) -> None:
        super().__init__()
        self.in_navigation = False
        self.links: list[tuple[str, str]] = []
        self._link_href: str | None = None
        self._link_text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag == "nav" and "sphinxsidebar-navigation" in (
            attributes.get("class") or ""
        ):
            self.in_navigation = True
        elif self.in_navigation and tag == "a":
            self._link_href = attributes.get("href")
            self._link_text = []

    def handle_data(self, data: str) -> None:
        if self._link_href is not None:
            self._link_text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._link_href is not None:
            self.links.append((self._link_href, "".join(self._link_text).strip()))
            self._link_href = None
        elif tag == "nav" and self.in_navigation:
            self.in_navigation = False


def require(condition: bool, message: str) -> None:
    """Exit with a clear error if the generated output violates the contract."""
    if not condition:
        raise SystemExit(message)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("build_dir", type=Path)
    args = parser.parse_args()
    build_dir: Path = args.build_dir

    navigation = SidebarNavigationParser()
    navigation.feed((build_dir / "index.html").read_text())
    page_links = dict(navigation.links)

    for href, title in EXPECTED_PAGE_LINKS.items():
        require(
            page_links.get(href) == title,
            f"Desktop sidebar navigation is missing the {title!r} page link.",
        )
    require(
        not any(href.startswith("#") for href, _ in navigation.links),
        "Desktop sidebar navigation must not contain current-page section anchors.",
    )

    stylesheet = (build_dir / "_static" / "palewire.css").read_text()
    require(
        re.search(r"nav#rellinks\s*\{\s*display:\s*none;", stylesheet) is not None,
        "Desktop pagination must be hidden by default.",
    )
    require(
        re.search(
            r"@media\s+screen\s+and\s+\(max-width:\s*975px\)\s*\{\s*"
            r"nav#rellinks\s*\{\s*display:\s*block;",
            stylesheet,
        )
        is not None,
        "Pagination must be visible when the desktop sidebar is hidden.",
    )
    require(
        re.search(
            r"@media\s+screen\s+and\s+\(max-width:\s*975px\)\s*\{\s*"
            r"div\.document,\s*div\.document\.wide,\s*div\.document\.narrow\s*"
            r"\{\s*width:\s*100%;",
            stylesheet,
        )
        is not None,
        "The document must become fluid when the desktop sidebar is hidden.",
    )


if __name__ == "__main__":
    main()
