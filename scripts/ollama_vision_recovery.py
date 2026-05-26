from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path

from ollama_vision_batch_ocr import check_ollama_model, run_ocr
from ollama_vision_model_compare import image_for_page, parse_pages


PAGE_RE = re.compile(r"^page_(?P<page>\d{3})\.md$")
UNREADABLE_MARK = "[неразборчиво]"


@dataclass
class OcrPage:
    page: int
    path: Path
    status: str
    text_length: int
    unreadable_count: int


@dataclass
class RecoveryResult:
    page: int
    status: str
    before_length: int
    after_length: int
    note: str = ""


def recovery_dir(root: Path) -> Path:
    return root / "07_ocr_recovery"


def ocr_pages_dir(root: Path) -> Path:
    return root / "05_ocr_pages"


def recovery_path(root: Path, page: int) -> Path:
    return recovery_dir(root) / f"recovery_page_{page:03d}.md"


def parse_field(text: str, field: str) -> str:
    pattern = re.compile(rf"^{re.escape(field)}:\s*\n(?P<value>.+?)\n(?:\n|$)", re.MULTILINE | re.DOTALL)
    match = pattern.search(text)
    return match.group("value").strip() if match else ""


def read_ocr_page(path: Path) -> OcrPage:
    match = PAGE_RE.match(path.name)
    if not match:
        raise ValueError(f"unexpected OCR page filename: {path.name}")
    text = path.read_text(encoding="utf-8")
    length_text = parse_field(text, "Text length")
    try:
        text_length = int(length_text)
    except ValueError:
        text_length = 0
    return OcrPage(
        page=int(match.group("page")),
        path=path,
        status=parse_field(text, "Status").lower(),
        text_length=text_length,
        unreadable_count=text.count(UNREADABLE_MARK),
    )


def read_ocr_pages(root: Path) -> list[OcrPage]:
    folder = ocr_pages_dir(root)
    if not folder.exists():
        return []
    return [read_ocr_page(path) for path in sorted(folder.glob("page_*.md")) if PAGE_RE.match(path.name)]


def problem_reasons(page: OcrPage, min_length: int, max_unreadable: int) -> list[str]:
    reasons = []
    if page.status == "error":
        reasons.append("status=error")
    if page.status == "empty":
        reasons.append("status=empty")
    if page.text_length < min_length:
        reasons.append(f"text length < {min_length}")
    if page.unreadable_count > max_unreadable:
        reasons.append(f"{UNREADABLE_MARK} count > {max_unreadable}")
    return reasons


def retry_candidates(root: Path, min_length: int, max_unreadable: int, pages_override: list[int] | None) -> tuple[list[int], dict[int, OcrPage], dict[int, list[str]]]:
    pages = read_ocr_pages(root)
    by_page = {page.page: page for page in pages}
    if pages_override is not None:
        reasons = {page: ["manual page override"] for page in pages_override}
        return pages_override, by_page, reasons

    selected: list[int] = []
    reasons: dict[int, list[str]] = {}
    for page in pages:
        page_reasons = problem_reasons(page, min_length, max_unreadable)
        if page_reasons:
            selected.append(page.page)
            reasons[page.page] = page_reasons
    return selected, by_page, reasons


def write_recovery_page(root: Path, page: int, source: Path, model: str, status: str, text: str, before_length: int, note: str = "") -> None:
    content = f"""# OCR Recovery Page {page:03d}

Source image:
`{source.relative_to(root).as_posix()}`

Model:
`{model}`

Status:
{status}

Text length before:
{before_length}

Text length after:
{len(text)}

## OCR text

```text
{text}
```
"""
    if note:
        content += f"\n## Notes\n\n{note}\n"
    recovery_path(root, page).write_text(content, encoding="utf-8")


def write_retry_list(root: Path, pages: list[int], reasons: dict[int, list[str]]) -> None:
    lines = [f"- page_{page:03d}: {'; '.join(reasons.get(page, ['manual page override']))}" for page in pages]
    content = "# OCR Recovery Retry List\n\n" + ("\n".join(lines) if lines else "- none") + "\n"
    (recovery_dir(root) / "retry_list.md").write_text(content, encoding="utf-8")


def write_summary(
    root: Path,
    primary_model: str,
    recovery_model: str,
    min_length: int,
    max_unreadable: int,
    pages: list[int],
    results: list[RecoveryResult],
    dry_run: bool,
) -> None:
    lines = [
        f"- page_{result.page:03d}: {result.status}, before={result.before_length}, after={result.after_length}, note={result.note or 'none'}"
        for result in results
    ]
    content = f"""# OCR Recovery Summary

## Metadata

- primary model: {primary_model}
- recovery model: {recovery_model}
- min length: {min_length}
- max unreadable markers: {max_unreadable}
- dry-run: {'yes' if dry_run else 'no'}

## Retry Candidates

{', '.join(f'{page:03d}' for page in pages) if pages else 'none'}

## Recovery Results

{chr(10).join(lines) if lines else '- none'}

## Recommendation Options

- accept recovery
- manual review
- retry with stronger model
- inspect source image
"""
    (recovery_dir(root) / "ocr_recovery_summary.md").write_text(content, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default="exam_materials")
    parser.add_argument("--ollama-url", default="http://127.0.0.1:11434")
    parser.add_argument("--primary-model", default="qwen2.5vl:7b")
    parser.add_argument("--recovery-model", default="qwen2.5vl:32b")
    parser.add_argument("--min-length", type=int, default=300)
    parser.add_argument("--max-unreadable", type=int, default=3)
    parser.add_argument("--pages")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    root = Path(args.root)
    out_dir = recovery_dir(root)
    out_dir.mkdir(parents=True, exist_ok=True)
    pages_override = parse_pages(args.pages) if args.pages else None
    pages, by_page, reasons = retry_candidates(root, args.min_length, args.max_unreadable, pages_override)
    write_retry_list(root, pages, reasons)

    if not args.dry_run:
        try:
            check_ollama_model(args.ollama_url, args.recovery_model)
        except RuntimeError as exc:
            print(f"Blocker: {exc}")
            raise SystemExit(1)

    results: list[RecoveryResult] = []
    for page in pages:
        source_page = by_page.get(page)
        before_length = source_page.text_length if source_page else 0
        target = recovery_path(root, page)
        if target.exists() and not args.force:
            results.append(RecoveryResult(page, "skipped_existing", before_length, 0, "target exists"))
            continue
        if args.dry_run:
            results.append(RecoveryResult(page, "dry_run", before_length, 0, "; ".join(reasons.get(page, []))))
            continue
        try:
            source = image_for_page(root, page)
            text = run_ocr(source, args.ollama_url, args.recovery_model)
            status = "success" if text else "empty"
            write_recovery_page(root, page, source, args.recovery_model, status, text, before_length)
            results.append(RecoveryResult(page, status, before_length, len(text)))
        except Exception as exc:
            try:
                source = image_for_page(root, page)
            except Exception:
                source = root / "00_scans" / "_preprocessed" / f"page_{page:03d}_ocr.png"
            note = str(exc)
            write_recovery_page(root, page, source, args.recovery_model, "error", "", before_length, note)
            results.append(RecoveryResult(page, "error", before_length, 0, note))

    write_summary(root, args.primary_model, args.recovery_model, args.min_length, args.max_unreadable, pages, results, args.dry_run)
    print(f"retry candidates: {len(pages)}")
    print(f"recovery attempted: {0 if args.dry_run else len(pages)}")
    print(f"output folder: {out_dir}")
    print(f"summary: {out_dir / 'ocr_recovery_summary.md'}")


if __name__ == "__main__":
    main()
