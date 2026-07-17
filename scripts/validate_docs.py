#!/usr/bin/env python3
"""Validate local links and DOM references in the GitHub Pages site."""

from __future__ import annotations

import re
import sys
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[1]
DOCS_DIR = ROOT / "docs"
INDEX_PATH = DOCS_DIR / "index.html"
REQUIRED_IDS = {"main-content", "quickstart", "workflow", "providers", "usage", "operations"}
REFERENCE_ATTRIBUTES = {"aria-controls", "aria-labelledby", "data-copy-target"}
MARKDOWN_LINK_PATTERN = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")
MARKDOWN_REFERENCE_PATTERN = re.compile(r"^\[[^\]]+\]:\s+(\S+)", re.MULTILINE)


class DocumentParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.ids: list[str] = []
        self.fragments: list[str] = []
        self.local_assets: list[str] = []
        self.dom_references: list[tuple[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {name: value for name, value in attrs if value is not None}
        element_id = values.get("id")
        if element_id:
            self.ids.append(element_id)

        for attribute in ("href", "src"):
            target = values.get(attribute)
            if target:
                self._record_url(target)

        for attribute in REFERENCE_ATTRIBUTES:
            target = values.get(attribute)
            if target:
                for reference in target.split():
                    self.dom_references.append((attribute, reference))

    def _record_url(self, target: str) -> None:
        parsed = urlsplit(target)
        if parsed.scheme or parsed.netloc:
            return
        if parsed.fragment:
            self.fragments.append(unquote(parsed.fragment))
        if parsed.path:
            self.local_assets.append(unquote(parsed.path))


def validate() -> list[str]:
    parser = DocumentParser()
    parser.feed(INDEX_PATH.read_text(encoding="utf-8"))
    errors: list[str] = []
    ids = set(parser.ids)

    duplicates = sorted(name for name, count in Counter(parser.ids).items() if count > 1)
    if duplicates:
        errors.append(f"duplicate HTML ids: {', '.join(duplicates)}")

    missing_required = sorted(REQUIRED_IDS - ids)
    if missing_required:
        errors.append(f"missing required ids: {', '.join(missing_required)}")

    for fragment in sorted(set(parser.fragments)):
        if fragment not in ids:
            errors.append(f"fragment target does not exist: #{fragment}")

    for attribute, reference in sorted(set(parser.dom_references)):
        if reference not in ids:
            errors.append(f"{attribute} target does not exist: {reference}")

    for asset in sorted(set(parser.local_assets)):
        if asset.startswith("/"):
            errors.append(f"root-absolute asset breaks project Pages: {asset}")
            continue
        resolved = (DOCS_DIR / asset).resolve()
        if DOCS_DIR.resolve() not in resolved.parents:
            errors.append(f"asset escapes docs directory: {asset}")
        elif not resolved.is_file():
            errors.append(f"local asset does not exist: {asset}")

    errors.extend(validate_markdown_links())
    return errors


def validate_markdown_links() -> list[str]:
    errors: list[str] = []
    markdown_paths = [ROOT / "README.md", ROOT / "README-EN.md", ROOT / "CHANGELOG.md"]
    markdown_paths.extend(sorted((ROOT / "docs").rglob("*.md")))

    for markdown_path in markdown_paths:
        text = markdown_path.read_text(encoding="utf-8")
        targets = MARKDOWN_LINK_PATTERN.findall(text)
        targets.extend(MARKDOWN_REFERENCE_PATTERN.findall(text))
        for raw_target in targets:
            target = raw_target.strip().strip("<>")
            parsed = urlsplit(target)
            if parsed.scheme or parsed.netloc or not parsed.path:
                continue
            if parsed.path.startswith("/"):
                errors.append(
                    f"root-absolute Markdown link is not portable: {markdown_path.relative_to(ROOT)} -> {target}"
                )
                continue
            resolved = (markdown_path.parent / unquote(parsed.path)).resolve()
            if ROOT.resolve() != resolved and ROOT.resolve() not in resolved.parents:
                errors.append(
                    f"Markdown link escapes repository: {markdown_path.relative_to(ROOT)} -> {target}"
                )
            elif not resolved.exists():
                errors.append(
                    f"Markdown link target does not exist: {markdown_path.relative_to(ROOT)} -> {target}"
                )
    return errors


def main() -> int:
    errors = validate()
    if errors:
        for error in errors:
            print(f"docs validation failed: {error}", file=sys.stderr)
        return 1
    print(f"documentation validation passed: {INDEX_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
