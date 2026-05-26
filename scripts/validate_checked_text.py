from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path

from create_checked_text_stubs import checked_dir
from ocr_merge_review_pack import UNREADABLE_MARK, parse_field


CHECKED_RE = re.compile(r"^checked_page_(?P<page>\d{3})\.md$")
VALID_STATUSES = {"draft", "checked", "needs_manual_fix", "blocked"}
REQUIRED_SECTIONS = ("Source:", "Review priority:", "Status:", "## Reviewer notes", "## Checked text")


def extract_checked_text(text: str) -> str:
    marker = "## Checked text"
    if marker not in text:
        return ""
    body = text.split(marker, 1)[1]
    fence = re.search(r"```(?:text)?\n", body)
    if not fence:
        return body.strip()
    end = body.rfind("\n```")
    if end <= fence.end():
        return body[fence.end() :].strip()
    return body[fence.end() : end].strip()


@dataclass
class CheckedPage:
    page: int
    path: Path
    priority: str
    status: str
    text: str
    issues: list[str]


def read_checked_pages(root: Path) -> dict[int, CheckedPage]:
    pages = {}
    folder = checked_dir(root)
    if not folder.exists():
        return pages
    for path in sorted(folder.glob("checked_page_*.md")):
        match = CHECKED_RE.match(path.name)
        if not match:
            continue
        raw = path.read_text(encoding="utf-8")
        page = int(match.group("page"))
        issues = [f"missing section: {section}" for section in REQUIRED_SECTIONS if section not in raw]
        status = parse_field(raw, "Status").lower()
        priority = parse_field(raw, "Review priority").lower()
        text = extract_checked_text(raw)
        if status not in VALID_STATUSES:
            issues.append(f"invalid status: {status or 'missing'}")
        if not text.strip():
            issues.append("empty checked text")
        if UNREADABLE_MARK in text and status == "checked":
            issues.append("checked page still contains unreadable marker")
        if priority == "high" and status == "checked":
            issues.append("high priority page requires explicit manual review before checked status")
        pages[page] = CheckedPage(page, path, priority, status, text, issues)
    return pages


def expected_pages(root: Path) -> list[int]:
    merged = root / "08_ocr_merged"
    pages = []
    for path in sorted(merged.glob("merged_page_*.md")) if merged.exists() else []:
        match = re.match(r"^merged_page_(\d{3})\.md$", path.name)
        if match:
            pages.append(int(match.group(1)))
    return pages


def write_dashboard(root: Path, pages: dict[int, CheckedPage], expected: list[int], missing: list[int]) -> None:
    checked = [page.page for page in pages.values() if page.status == "checked" and not page.issues]
    draft = [page.page for page in pages.values() if page.status == "draft"]
    needs_fix = [page.page for page in pages.values() if page.status == "needs_manual_fix"]
    blocked = [page.page for page in pages.values() if page.status == "blocked"]
    high = [page.page for page in pages.values() if page.priority in {"high", "blocked"}]
    unreadable = [page.page for page in pages.values() if UNREADABLE_MARK in page.text]
    content = f"""# Checked Text Review Dashboard

- total pages: {len(expected)}
- checked pages: {len(checked)}
- draft pages: {len(draft)}
- needs_manual_fix pages: {len(needs_fix)}
- blocked pages: {len(blocked)}
- high-priority pages: {len(high)}
- pages with {UNREADABLE_MARK}: {len(unreadable)}
- missing checked files: {len(missing)}

## Next Recommended Manual Review Order

1. Blocked pages: {format_pages(blocked)}
2. Pages with {UNREADABLE_MARK}: {format_pages(unreadable)}
3. High-priority pages: {format_pages(high)}
4. Draft pages: {format_pages(draft)}
"""
    (checked_dir(root) / "review_dashboard.md").write_text(content, encoding="utf-8")


def format_pages(pages: list[int]) -> str:
    return ", ".join(f"{page:03d}" for page in sorted(pages)) if pages else "none"


def write_summary(root: Path, pages: dict[int, CheckedPage], expected: list[int], missing: list[int]) -> None:
    issue_pages = [page for page in pages.values() if page.issues]
    ready = [page.page for page in pages.values() if page.status == "checked" and not page.issues]
    non_ready = sorted(set(expected) - set(ready))
    lines = []
    for page in sorted(issue_pages, key=lambda item: item.page):
        lines.append(f"- page_{page.page:03d}: {'; '.join(page.issues)}")
    content = f"""# Checked Text Validation Summary

## Counts

- expected pages: {len(expected)}
- checked files found: {len(pages)}
- missing checked files: {len(missing)}
- ready checked pages: {len(ready)}
- non-ready pages: {len(non_ready)}
- pages with issues: {len(issue_pages)}

## Missing Pages

{format_pages(missing)}

## Non-Ready Pages

{format_pages(non_ready)}

## Issues

{chr(10).join(lines) if lines else '- none'}

## Recommendation

Review high-priority, unreadable, blocked, and draft pages before using checked text for ticket generation.
"""
    (checked_dir(root) / "checked_text_validation_summary.md").write_text(content, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default="exam_materials")
    args = parser.parse_args()

    root = Path(args.root)
    checked_dir(root).mkdir(parents=True, exist_ok=True)
    pages = read_checked_pages(root)
    expected = expected_pages(root)
    missing = [page for page in expected if page not in pages]
    write_summary(root, pages, expected, missing)
    write_dashboard(root, pages, expected, missing)
    ready = [page for page in pages.values() if page.status == "checked" and not page.issues]
    print(f"expected pages: {len(expected)}")
    print(f"checked files found: {len(pages)}")
    print(f"ready checked pages: {len(ready)}")
    print(f"missing checked files: {len(missing)}")
    print(f"summary: {checked_dir(root) / 'checked_text_validation_summary.md'}")
    print(f"dashboard: {checked_dir(root) / 'review_dashboard.md'}")


if __name__ == "__main__":
    main()
