from __future__ import annotations

import argparse
from pathlib import Path

from exam_materials_lib import ensure_root, load_rows, save_rows, text_stub, write_file


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default="exam_materials")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    root = Path(args.root)
    if args.dry_run and not (root / "progress.xlsx").exists():
        print("text stubs created: 0")
        print("dry-run: no files or progress workbook modified")
        print(f"progress: {root / 'progress.xlsx'}")
        return

    if not args.dry_run:
        ensure_root(root)
    rows = load_rows(root)
    created = 0

    for ticket_id, row in sorted(rows.items()):
        if ticket_id == "unknown":
            continue
        path = root / "01_text" / f"ticket_{ticket_id}_raw.md"
        would_create = args.force or not path.exists()
        if args.dry_run:
            if would_create:
                created += 1
        elif write_file(path, text_stub(ticket_id, row.get("scan_files", "")), force=args.force):
            created += 1
        if not args.dry_run:
            row["ocr_status"] = row.get("ocr_status") or "pending"
            row["final_status"] = row.get("final_status") or "ocr"

    if not args.dry_run:
        save_rows(root, rows)
    print(f"text stubs created: {created}")
    if args.dry_run:
        print("dry-run: no files or progress workbook modified")
    print(f"progress: {root / 'progress.xlsx'}")


if __name__ == "__main__":
    main()
