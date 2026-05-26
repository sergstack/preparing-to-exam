from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from ocr_merge_review_pack import collect_primary_pages, collect_recovery_pages, merge_pages, UNREADABLE_MARK
from ollama_vision_recovery import read_ocr_pages


SHORT_TEXT_LENGTH = 300


@dataclass
class StepResult:
    name: str
    returncode: int
    stdout: str
    stderr: str


def report_dir(root: Path) -> Path:
    return root / "09_review_reports"


def page_chunks(start: int, end: int, chunk_size: int) -> list[tuple[int, int]]:
    if end < start:
        return []
    size = max(chunk_size, 1)
    chunks = []
    current = start
    while current <= end:
        chunk_end = min(current + size - 1, end)
        chunks.append((current, chunk_end))
        current = chunk_end + 1
    return chunks


def run_command(args: list[str], cwd: Path) -> StepResult:
    result = subprocess.run(args, cwd=cwd, text=True, capture_output=True, check=False)
    return StepResult(args[1] if len(args) > 1 else args[0], result.returncode, result.stdout, result.stderr)


def page_label(page: int) -> str:
    return f"{page:03d}"


def pages_csv(pages: list[int]) -> str:
    return ", ".join(page_label(page) for page in pages) if pages else "none"


def primary_counts(root: Path, selected_pages: list[int]) -> tuple[int, int, list[int]]:
    pages = {page.page: page for page in read_ocr_pages(root)}
    success = 0
    errors: list[int] = []
    for page in selected_pages:
        item = pages.get(page)
        if item and item.status == "success":
            success += 1
        else:
            errors.append(page)
    return success, len(errors), errors


def recovery_counts(root: Path, candidates: list[int]) -> tuple[int, int, list[int]]:
    recovery = collect_recovery_pages(root)
    success = 0
    errors: list[int] = []
    for page in candidates:
        item = recovery.get(page)
        if item and item.status == "success":
            success += 1
        else:
            errors.append(page)
    return success, len(errors), errors


def retry_candidates(root: Path, min_length: int = SHORT_TEXT_LENGTH, max_unreadable: int = 3) -> list[int]:
    candidates = []
    for page in read_ocr_pages(root):
        if page.status in {"error", "empty"} or page.text_length < min_length or page.unreadable_count > max_unreadable:
            candidates.append(page.page)
    return sorted(candidates)


def summarize_merged(root: Path) -> dict[str, list[int] | int]:
    merged = merge_pages(collect_primary_pages(root), collect_recovery_pages(root), strip_headings=True)
    return {
        "merged_count": len(merged),
        "manual_review": [page.page for page in merged if page.status == "manual_review_required"],
        "unreadable": [page.page for page in merged if UNREADABLE_MARK in page.text],
        "short": [page.page for page in merged if page.status == "selected" and len(page.text) < SHORT_TEXT_LENGTH],
        "recovery_used": [page.page for page in merged if page.source == "recovery"],
        "primary_used": [page.page for page in merged if page.source == "primary"],
    }


def write_summary(
    root: Path,
    start: int,
    end: int,
    selected_pages: list[int],
    primary_model: str,
    recovery_model: str,
    primary_success: int,
    primary_error: int,
    primary_error_pages: list[int],
    recovery_candidates: list[int],
    recovery_success: int,
    recovery_error: int,
    recovery_error_pages: list[int],
    merged: dict[str, list[int] | int],
    steps: list[StepResult],
) -> None:
    report_dir(root).mkdir(parents=True, exist_ok=True)
    content = f"""# OCR End-to-End Review Pack Summary

## Run

- run timestamp: {datetime.now(timezone.utc).replace(microsecond=0).isoformat()}
- input range: {start}-{end}
- total pages selected: {len(selected_pages)}
- primary model: {primary_model}
- recovery model: {recovery_model}

## Primary OCR

- success count: {primary_success}
- error/other count: {primary_error}
- error/other pages: {pages_csv(primary_error_pages)}

## Recovery OCR

- recovery candidates: {pages_csv(recovery_candidates)}
- success count: {recovery_success}
- error/other count: {recovery_error}
- error/other pages: {pages_csv(recovery_error_pages)}

## Merged Review Pack

- merged pages count: {merged['merged_count']}
- pages requiring manual review: {pages_csv(merged['manual_review'])}
- pages containing {UNREADABLE_MARK}: {pages_csv(merged['unreadable'])}
- pages with very short text: {pages_csv(merged['short'])}
- pages where recovery output was used: {pages_csv(merged['recovery_used'])}

## Stale Output Warning

Existing OCR outputs can predate the current near-verbatim prompt. Treat already existing pages as review-required unless they were regenerated in the current controlled OCR pass.

## Steps

{chr(10).join(f'- {step.name}: exit={step.returncode}' for step in steps) if steps else '- none'}

## Next Recommended Step

Manually review `08_ocr_merged/merged_full_text.md`, starting with recovery, unreadable, short, and manual-review pages. Do not generate tickets until checked text is prepared.
"""
    (report_dir(root) / "ocr_end_to_end_summary.md").write_text(content, encoding="utf-8")


def write_manual_review_plan(root: Path, merged: dict[str, list[int] | int], recovery_candidates: list[int], recovery_error_pages: list[int]) -> None:
    high_priority = sorted(set(merged["recovery_used"]) | set(merged["unreadable"]) | set(merged["short"]) | set(recovery_candidates))
    normal = [page for page in merged["primary_used"] if page not in high_priority]
    blocked = sorted(merged["manual_review"])
    content = f"""# OCR Manual Review Plan

## High Priority Review

- recovery pages: {pages_csv(merged['recovery_used'])}
- pages with {UNREADABLE_MARK}: {pages_csv(merged['unreadable'])}
- pages with short text: {pages_csv(merged['short'])}
- pages with service heading stripped: {pages_csv(merged['recovery_used'])}
- combined high priority: {pages_csv(high_priority)}

## Normal Review

{chr(10).join(f'- page_{page_label(page)}' for page in normal) if normal else '- none'}

## Blocked

{chr(10).join(f'- page_{page_label(page)}' for page in blocked) if blocked else '- none'}
"""
    report_dir(root).mkdir(parents=True, exist_ok=True)
    (report_dir(root) / "manual_review_plan.md").write_text(content, encoding="utf-8")


def run_primary(args: argparse.Namespace, root: Path, repo_root: Path, chunks: list[tuple[int, int]]) -> list[StepResult]:
    steps = []
    for chunk_start, chunk_end in chunks:
        command = [
            sys.executable,
            "scripts/ollama_vision_batch_ocr.py",
            "--root",
            str(root),
            "--ollama-url",
            args.ollama_url,
            "--model",
            args.primary_model,
            "--start",
            str(chunk_start),
            "--end",
            str(chunk_end),
            "--limit",
            str(chunk_end - chunk_start + 1),
        ]
        if args.force:
            command.append("--force")
        if args.resume:
            command.append("--resume")
        steps.append(run_command(command, repo_root))
    return steps


def run_recovery(args: argparse.Namespace, root: Path, repo_root: Path) -> StepResult:
    command = [
        sys.executable,
        "scripts/ollama_vision_recovery.py",
        "--root",
        str(root),
        "--ollama-url",
        args.ollama_url,
        "--primary-model",
        args.primary_model,
        "--recovery-model",
        args.recovery_model,
    ]
    if args.force:
        command.append("--force")
    return run_command(command, repo_root)


def run_merge(args: argparse.Namespace, root: Path, repo_root: Path) -> StepResult:
    command = [sys.executable, "scripts/ocr_merge_review_pack.py", "--root", str(root), "--strip-service-headings"]
    if args.force:
        command.append("--force")
    return run_command(command, repo_root)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default="exam_materials")
    parser.add_argument("--ollama-url", default="http://127.0.0.1:11434")
    parser.add_argument("--primary-model", default="qwen2.5vl:7b")
    parser.add_argument("--recovery-model", default="qwen2.5vl:32b")
    parser.add_argument("--start", type=int, required=True)
    parser.add_argument("--end", type=int, required=True)
    parser.add_argument("--chunk-size", type=int, default=10)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--skip-primary", action="store_true")
    parser.add_argument("--skip-recovery", action="store_true")
    parser.add_argument("--skip-merge", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--max-errors", type=int, default=10)
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    root = Path(args.root)
    chunks = page_chunks(args.start, args.end, args.chunk_size)
    selected_pages = list(range(args.start, args.end + 1))
    if args.dry_run:
        print(f"dry-run: yes")
        print(f"chunks: {', '.join(f'{start}-{end}' for start, end in chunks) if chunks else 'none'}")
        print("no outputs written")
        return

    steps: list[StepResult] = []
    if not args.skip_primary:
        steps.extend(run_primary(args, root, repo_root, chunks))

    primary_success, primary_error, primary_error_pages = primary_counts(root, selected_pages)
    failed_steps = [step for step in steps if step.returncode != 0]
    if primary_error > args.max_errors or len(failed_steps) > args.max_errors:
        print(f"Blocker: max errors exceeded after primary OCR: primary_error={primary_error}, failed_steps={len(failed_steps)}, max_errors={args.max_errors}")
        raise SystemExit(1)

    candidates = retry_candidates(root)
    recovery_success = 0
    recovery_error = 0
    recovery_error_pages: list[int] = []
    if not args.skip_recovery:
        recovery_step = run_recovery(args, root, repo_root)
        steps.append(recovery_step)
        recovery_success, recovery_error, recovery_error_pages = recovery_counts(root, candidates)
        if recovery_error > args.max_errors:
            print(f"Blocker: max errors exceeded after recovery OCR: recovery_error={recovery_error}, max_errors={args.max_errors}")
            raise SystemExit(1)

    if not args.skip_merge:
        steps.append(run_merge(args, root, repo_root))

    merged = summarize_merged(root)
    write_summary(
        root,
        args.start,
        args.end,
        selected_pages,
        args.primary_model,
        args.recovery_model,
        primary_success,
        primary_error,
        primary_error_pages,
        candidates,
        recovery_success,
        recovery_error,
        recovery_error_pages,
        merged,
        steps,
    )
    write_manual_review_plan(root, merged, candidates, recovery_error_pages)
    print(f"pages selected: {len(selected_pages)}")
    print(f"primary success: {primary_success}")
    print(f"primary error/other: {primary_error}")
    print(f"recovery candidates: {len(candidates)}")
    print(f"recovery success: {recovery_success}")
    print(f"recovery error/other: {recovery_error}")
    print(f"merged pages: {merged['merged_count']}")
    print(f"manual review pages: {len(merged['manual_review'])}")
    print(f"summary: {report_dir(root) / 'ocr_end_to_end_summary.md'}")


if __name__ == "__main__":
    main()
