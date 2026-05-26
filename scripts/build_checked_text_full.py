from __future__ import annotations

import argparse
from pathlib import Path

from ocr_merge_review_pack import parse_field
from validate_checked_text import CHECKED_RE, checked_dir, extract_checked_text, read_checked_pages


def checked_pages(root: Path) -> list[tuple[int, Path]]:
    folder = checked_dir(root)
    if not folder.exists():
        return []
    pages = []
    for path in sorted(folder.glob("checked_page_*.md")):
        match = CHECKED_RE.match(path.name)
        if match:
            pages.append((int(match.group("page")), path))
    return pages


def build_full_text(root: Path) -> str:
    parts = [
        "# Checked Full Text",
        "",
        "Transcription mode:",
        "near-verbatim / manually checked text",
        "",
    ]
    warnings = []
    for page, path in checked_pages(root):
        raw = path.read_text(encoding="utf-8")
        status = parse_field(raw, "Status").lower()
        if status != "checked":
            warnings.append(page)
        parts.extend([f"## Page {page:03d}", "", extract_checked_text(raw), ""])
    if warnings:
        parts.extend(["## Warning", "", f"Some pages are not checked: {', '.join(f'{page:03d}' for page in warnings)}", ""])
    return "\n".join(parts)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default="exam_materials")
    args = parser.parse_args()

    root = Path(args.root)
    checked_dir(root).mkdir(parents=True, exist_ok=True)
    content = build_full_text(root)
    target = checked_dir(root) / "checked_full_text.md"
    target.write_text(content, encoding="utf-8")
    pages = read_checked_pages(root)
    unchecked = [page.page for page in pages.values() if page.status != "checked"]
    print(f"checked pages included: {len(pages)}")
    print(f"not checked pages: {len(unchecked)}")
    print(f"output: {target}")


if __name__ == "__main__":
    main()
