from __future__ import annotations

import argparse
from pathlib import Path

from exam_materials_lib import RAW_TEXT_RE, ensure_root, load_rows, save_rows, ticket_template, upsert_ticket, write_file


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default="exam_materials")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    root = Path(args.root)
    ensure_root(root)
    rows = load_rows(root)
    created = 0

    for path in sorted((root / "01_text").glob("ticket_*_raw.md")):
        match = RAW_TEXT_RE.match(path.name)
        if not match:
            continue
        ticket_id = match.group("ticket")
        target = root / "02_tickets" / f"ticket_{ticket_id}.md"
        if write_file(target, ticket_template(ticket_id), force=args.force):
            created += 1
        row = upsert_ticket(rows, ticket_id)
        row["ocr_status"] = "done"
        row["ticket_status"] = "draft"
        row["final_status"] = "draft"

    save_rows(root, rows)
    print(f"ticket templates created: {created}")
    print(f"progress: {root / 'progress.xlsx'}")


if __name__ == "__main__":
    main()
