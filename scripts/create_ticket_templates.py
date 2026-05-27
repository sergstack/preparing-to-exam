from __future__ import annotations

import argparse
from pathlib import Path

from exam_materials_lib import RAW_TEXT_RE, ensure_root, load_rows, save_rows, ticket_template, upsert_ticket, write_file


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default="exam_materials")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    root = Path(args.root)
    if args.dry_run and not root.exists():
        print("ticket templates created: 0")
        print("dry-run: no files or progress workbook modified")
        print(f"progress: {root / 'progress.xlsx'}")
        return

    if not args.dry_run:
        ensure_root(root)
    rows = load_rows(root) if not args.dry_run or (root / "progress.xlsx").exists() else {}
    created = 0

    for path in sorted((root / "01_text").glob("ticket_*_raw.md")):
        match = RAW_TEXT_RE.match(path.name)
        if not match:
            continue
        ticket_id = match.group("ticket")
        target = root / "02_tickets" / f"ticket_{ticket_id}.md"
        would_create = args.force or not target.exists()
        if args.dry_run:
            if would_create:
                created += 1
        elif write_file(target, ticket_template(ticket_id), force=args.force):
            created += 1
        if not args.dry_run:
            row = upsert_ticket(rows, ticket_id)
            row["ocr_status"] = "done"
            row["ticket_status"] = "draft"
            row["final_status"] = "draft"

    if not args.dry_run:
        save_rows(root, rows)
    print(f"ticket templates created: {created}")
    if args.dry_run:
        print("dry-run: no files or progress workbook modified")
    print(f"progress: {root / 'progress.xlsx'}")


if __name__ == "__main__":
    main()
