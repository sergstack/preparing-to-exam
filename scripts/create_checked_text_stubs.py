from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path

from ocr_merge_review_pack import extract_ocr_text, parse_field


MERGED_RE = re.compile(r"^merged_page_(?P<page>\d{3})\.md$")


@dataclass
class MergedInput:
    page: int
    path: Path
    status: str
    text: str


def checked_dir(root: Path) -> Path:
    return root / "10_checked_text"


def merged_dir(root: Path) -> Path:
    return root / "08_ocr_merged"


def review_plan_path(root: Path) -> Path:
    return root / "09_review_reports" / "manual_review_plan.md"


def checked_path(root: Path, page: int) -> Path:
    return checked_dir(root) / f"checked_page_{page:03d}.md"


def parse_review_pages(text: str, heading: str) -> set[int]:
    match = re.search(rf"^## {re.escape(heading)}\s*\n(?P<body>.*?)(?=^## |\Z)", text, re.MULTILINE | re.DOTALL)
    if not match:
        return set()
    return {int(value) for value in re.findall(r"page_(\d{3})|\b(\d{3})\b", match.group("body")) for value in value if value}


def review_priorities(root: Path) -> dict[int, str]:
    path = review_plan_path(root)
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8")
    high = parse_review_pages(text, "High Priority Review")
    blocked = parse_review_pages(text, "Blocked")
    priorities = {page: "high" for page in high}
    priorities.update({page: "blocked" for page in blocked})
    return priorities


def read_merged_pages(root: Path) -> list[MergedInput]:
    pages = []
    folder = merged_dir(root)
    if not folder.exists():
        return pages
    for path in sorted(folder.glob("merged_page_*.md")):
        match = MERGED_RE.match(path.name)
        if not match:
            continue
        page = int(match.group("page"))
        raw = path.read_text(encoding="utf-8")
        pages.append(MergedInput(page, path, parse_field(raw, "Status").lower(), extract_ocr_text(raw)))
    return pages


def stub_text(root: Path, page: MergedInput, priority: str) -> str:
    status = "blocked" if priority == "blocked" or page.status == "manual_review_required" else "draft"
    return f"""# Checked Text Page {page.page:03d}

Source:
{page.path.relative_to(root).as_posix()}

Review priority:
{priority}

Status:
{status}

## Reviewer notes

## Checked text

```text
{page.text}
```
"""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default="exam_materials")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--only-high-priority", action="store_true")
    args = parser.parse_args()

    root = Path(args.root)
    priorities = review_priorities(root)
    pages = read_merged_pages(root)
    created = 0
    skipped = 0
    selected = 0
    for page in pages:
        priority = priorities.get(page.page, "normal")
        if args.only_high_priority and priority == "normal":
            continue
        selected += 1
        target = checked_path(root, page.page)
        if target.exists() and not args.force:
            skipped += 1
            continue
        if not args.dry_run:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(stub_text(root, page, priority), encoding="utf-8")
        created += 1

    print(f"merged pages found: {len(pages)}")
    print(f"selected pages: {selected}")
    print(f"created/updated: {created}")
    print(f"skipped existing: {skipped}")
    print(f"dry-run: {'yes' if args.dry_run else 'no'}")
    if not args.dry_run:
        print(f"output folder: {checked_dir(root)}")


if __name__ == "__main__":
    main()
