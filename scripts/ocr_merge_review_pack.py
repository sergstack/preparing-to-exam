from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path


PRIMARY_RE = re.compile(r"^page_(?P<page>\d{3})\.md$")
RECOVERY_RE = re.compile(r"^recovery_page_(?P<page>\d{3})\.md$")
UNREADABLE_MARK = "[неразборчиво]"
SERVICE_HEADING_PATTERNS = (
    re.compile(r"^#+\s*Расшифровка текста:?\s*$", re.IGNORECASE),
    re.compile(r"^#+\s*Примечания:?\s*$", re.IGNORECASE),
    re.compile(r"^Вот расшифровка:?\s*$", re.IGNORECASE),
    re.compile(r"^Ниже представлен текст:?\s*$", re.IGNORECASE),
)


@dataclass
class SourcePage:
    page: int
    path: Path
    status: str
    text: str


@dataclass
class MergedPage:
    page: int
    source: str
    status: str
    text: str
    primary_file: Path | None
    recovery_file: Path | None


def output_dir(root: Path) -> Path:
    return root / "08_ocr_merged"


def primary_dir(root: Path) -> Path:
    return root / "05_ocr_pages"


def recovery_dir(root: Path) -> Path:
    return root / "07_ocr_recovery"


def parse_field(text: str, field: str) -> str:
    pattern = re.compile(rf"^{re.escape(field)}:\s*\n(?P<value>.+?)\n(?:\n|$)", re.MULTILINE | re.DOTALL)
    match = pattern.search(text)
    return match.group("value").strip() if match else ""


def extract_ocr_text(text: str) -> str:
    marker = "## OCR text"
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


def read_source_page(path: Path, page: int) -> SourcePage:
    text = path.read_text(encoding="utf-8")
    return SourcePage(page=page, path=path, status=parse_field(text, "Status").lower(), text=extract_ocr_text(text))


def collect_primary_pages(root: Path) -> dict[int, SourcePage]:
    pages = {}
    folder = primary_dir(root)
    if not folder.exists():
        return pages
    for path in sorted(folder.glob("page_*.md")):
        match = PRIMARY_RE.match(path.name)
        if match:
            page = int(match.group("page"))
            pages[page] = read_source_page(path, page)
    return pages


def collect_recovery_pages(root: Path) -> dict[int, SourcePage]:
    pages = {}
    folder = recovery_dir(root)
    if not folder.exists():
        return pages
    for path in sorted(folder.glob("recovery_page_*.md")):
        match = RECOVERY_RE.match(path.name)
        if match:
            page = int(match.group("page"))
            pages[page] = read_source_page(path, page)
    return pages


def page_range(primary: dict[int, SourcePage], recovery: dict[int, SourcePage]) -> list[int]:
    seen = sorted(set(primary) | set(recovery))
    if not seen:
        return []
    return list(range(1, max(seen) + 1))


def strip_service_headings(text: str) -> str:
    lines = text.splitlines()
    cleaned: list[str] = []
    in_trailing_notes = False
    for line in lines:
        stripped = line.strip()
        if any(pattern.match(stripped) for pattern in SERVICE_HEADING_PATTERNS):
            in_trailing_notes = bool(re.match(r"^#+\s*Примечания:?\s*$", stripped, re.IGNORECASE))
            continue
        if in_trailing_notes and re.match(r"^\d+\.\s+", stripped):
            continue
        in_trailing_notes = False
        cleaned.append(line)
    return "\n".join(cleaned).strip()


def merge_pages(primary: dict[int, SourcePage], recovery: dict[int, SourcePage], strip_headings: bool) -> list[MergedPage]:
    merged = []
    for page in page_range(primary, recovery):
        primary_page = primary.get(page)
        recovery_page = recovery.get(page)
        selected: SourcePage | None = None
        source = "manual_review"
        if recovery_page and recovery_page.status == "success":
            selected = recovery_page
            source = "recovery"
        elif primary_page and primary_page.status == "success":
            selected = primary_page
            source = "primary"

        if selected:
            text = strip_service_headings(selected.text) if strip_headings else selected.text
            status = "selected"
        else:
            text = ""
            status = "manual_review_required"

        merged.append(
            MergedPage(
                page=page,
                source=source,
                status=status,
                text=text,
                primary_file=primary_page.path if primary_page else None,
                recovery_file=recovery_page.path if recovery_page else None,
            )
        )
    return merged


def rel(root: Path, path: Path | None) -> str:
    return path.relative_to(root).as_posix() if path else "missing"


def fenced_text(text: str) -> str:
    fence = "````" if "```" in text else "```"
    return f"{fence}text\n{text}\n{fence}"


def write_merged_page(root: Path, page: MergedPage) -> None:
    content = f"""# Merged OCR Page {page.page:03d}

Source:
{page.source}

Primary file:
{rel(root, page.primary_file)}

Recovery file:
{rel(root, page.recovery_file)}

Status:
{page.status}

## OCR text

{fenced_text(page.text)}
"""
    (output_dir(root) / f"merged_page_{page.page:03d}.md").write_text(content, encoding="utf-8")


def write_full_text(root: Path, pages: list[MergedPage]) -> None:
    parts = [
        "# Merged OCR Full Text",
        "",
        "Transcription mode:",
        "near-verbatim / light cleanup only",
        "",
    ]
    for page in pages:
        parts.extend([f"## Page {page.page:03d}", "", page.text if page.text else "[manual review required]", ""])
    (output_dir(root) / "merged_full_text.md").write_text("\n".join(parts), encoding="utf-8")


def write_manual_review(root: Path, pages: list[MergedPage]) -> None:
    manual = [page for page in pages if page.status == "manual_review_required"]
    lines = [
        f"- page_{page.page:03d}: primary={rel(root, page.primary_file)}, recovery={rel(root, page.recovery_file)}"
        for page in manual
    ]
    content = "# OCR Manual Review List\n\n" + ("\n".join(lines) if lines else "- none") + "\n"
    (output_dir(root) / "manual_review_list.md").write_text(content, encoding="utf-8")


def write_summary(root: Path, pages: list[MergedPage], strip_headings: bool) -> None:
    primary_used = [page for page in pages if page.source == "primary"]
    recovery_used = [page for page in pages if page.source == "recovery"]
    manual = [page for page in pages if page.status == "manual_review_required"]
    short = [page for page in pages if page.status == "selected" and len(page.text) < 300]
    unreadable = [page for page in pages if UNREADABLE_MARK in page.text]
    content = f"""# OCR Merge Review Summary

## Counts

- total pages found: {len(pages)}
- primary pages used: {len(primary_used)}
- recovery pages used: {len(recovery_used)}
- pages requiring manual review: {len(manual)}
- pages with short text: {len(short)}
- pages containing {UNREADABLE_MARK}: {len(unreadable)}
- service headings stripped: {'yes' if strip_headings else 'no'}

## Pages

- primary used: {', '.join(f'{page.page:03d}' for page in primary_used) if primary_used else 'none'}
- recovery used: {', '.join(f'{page.page:03d}' for page in recovery_used) if recovery_used else 'none'}
- manual review: {', '.join(f'{page.page:03d}' for page in manual) if manual else 'none'}
- short text: {', '.join(f'{page.page:03d}' for page in short) if short else 'none'}
- unreadable markers: {', '.join(f'{page.page:03d}' for page in unreadable) if unreadable else 'none'}

## Recommendation

- manual review merged text
- then create checked text stubs
- then generate tickets
"""
    (output_dir(root) / "ocr_merge_review_summary.md").write_text(content, encoding="utf-8")


def ensure_can_write(root: Path, force: bool) -> None:
    folder = output_dir(root)
    if folder.exists() and any(folder.iterdir()) and not force:
        raise RuntimeError(f"output folder already has files: {folder}. Re-run with --force to overwrite generated merge artifacts.")


def write_outputs(root: Path, pages: list[MergedPage], strip_headings: bool, force: bool) -> None:
    ensure_can_write(root, force)
    output_dir(root).mkdir(parents=True, exist_ok=True)
    for page in pages:
        write_merged_page(root, page)
    write_full_text(root, pages)
    write_manual_review(root, pages)
    write_summary(root, pages, strip_headings)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default="exam_materials")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--strip-service-headings", action="store_true")
    args = parser.parse_args()

    root = Path(args.root)
    primary = collect_primary_pages(root)
    recovery = collect_recovery_pages(root)
    pages = merge_pages(primary, recovery, args.strip_service_headings)
    if not args.dry_run:
        try:
            write_outputs(root, pages, args.strip_service_headings, args.force)
        except RuntimeError as exc:
            print(f"Blocker: {exc}")
            raise SystemExit(1)

    primary_used = sum(1 for page in pages if page.source == "primary")
    recovery_used = sum(1 for page in pages if page.source == "recovery")
    manual = sum(1 for page in pages if page.status == "manual_review_required")
    print(f"pages merged: {len(pages)}")
    print(f"primary pages used: {primary_used}")
    print(f"recovery pages used: {recovery_used}")
    print(f"manual review pages: {manual}")
    print(f"dry-run: {'yes' if args.dry_run else 'no'}")
    if not args.dry_run:
        print(f"output folder: {output_dir(root)}")


if __name__ == "__main__":
    main()
