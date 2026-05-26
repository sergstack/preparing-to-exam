from __future__ import annotations

import argparse
from pathlib import Path

from exam_materials_lib import (
    SUPPORTED_SCAN_SUFFIXES,
    TICKET_RE,
    append_note,
    duplicate_names,
    ensure_progress_workbook,
    ensure_root,
    load_rows,
    relative_scan_list,
    save_rows,
    upsert_ticket,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default="exam_materials")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    root = Path(args.root)
    if args.dry_run:
        rows = load_rows(root) if (root / "progress.xlsx").exists() else {}
    else:
        ensure_root(root)
        ensure_progress_workbook(root)
        rows = load_rows(root)
    original_rows = {ticket_id: row.copy() for ticket_id, row in rows.items()}
    grouped: dict[str, list[Path]] = {}
    unknown = 0
    scan_dir = root / "00_scans"
    files = sorted(
        path
        for path in scan_dir.iterdir()
        if path.is_file() and path.suffix.lower() in SUPPORTED_SCAN_SUFFIXES
    ) if scan_dir.exists() else []
    duplicates = duplicate_names(files)

    for path in files:
        match = TICKET_RE.match(path.name)
        if not match:
            unknown += 1
            ticket_id = "unknown"
            row = upsert_ticket(rows, ticket_id)
            row["check_notes"] = append_note(row.get("check_notes", ""), "filename_check")
            row["final_status"] = row.get("final_status") or "raw"
            continue
        ticket_id = match.group("ticket")
        grouped.setdefault(ticket_id, []).append(path)

    for ticket_id, grouped_files in grouped.items():
        row = upsert_ticket(rows, ticket_id)
        row["scan_files"] = relative_scan_list(root, grouped_files)
        row["ocr_status"] = row.get("ocr_status") or "pending"
        row["ticket_status"] = row.get("ticket_status") or "raw"
        row["final_status"] = row.get("final_status") or "raw"

    changed = [
        ticket_id
        for ticket_id, row in rows.items()
        if ticket_id not in original_rows or row != original_rows[ticket_id]
    ]
    created = [ticket_id for ticket_id in changed if ticket_id not in original_rows]
    updated = [ticket_id for ticket_id in changed if ticket_id in original_rows]

    if not args.dry_run:
        save_rows(root, rows)

    print(f"files found: {len(files)}")
    print(f"registered tickets: {len(grouped)}")
    print(f"unknown filenames: {unknown}")
    print(f"duplicate filenames: {', '.join(duplicates) if duplicates else 'none'}")
    print(f"progress rows created: {len(created)}")
    print(f"progress rows updated: {len(updated)}")
    if args.dry_run:
        print("dry-run: progress.xlsx not modified")
    print(f"progress: {root / 'progress.xlsx'}")


if __name__ == "__main__":
    main()
