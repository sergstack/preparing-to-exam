from __future__ import annotations

import argparse
from pathlib import Path

from exam_materials_lib import (
    SUPPORTED_SCAN_SUFFIXES,
    TICKET_RE,
    append_note,
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
    args = parser.parse_args()

    root = Path(args.root)
    ensure_root(root)
    ensure_progress_workbook(root)
    rows = load_rows(root)
    grouped: dict[str, list[Path]] = {}
    unknown = 0

    for path in sorted((root / "00_scans").iterdir()):
        if not path.is_file() or path.suffix.lower() not in SUPPORTED_SCAN_SUFFIXES:
            continue
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

    for ticket_id, files in grouped.items():
        row = upsert_ticket(rows, ticket_id)
        row["scan_files"] = relative_scan_list(root, files)
        row["ocr_status"] = row.get("ocr_status") or "pending"
        row["ticket_status"] = row.get("ticket_status") or "raw"
        row["final_status"] = row.get("final_status") or "raw"

    save_rows(root, rows)
    print(f"registered tickets: {len(grouped)}")
    print(f"unknown filenames: {unknown}")
    print(f"progress: {root / 'progress.xlsx'}")


if __name__ == "__main__":
    main()
