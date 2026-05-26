from __future__ import annotations

import argparse
from pathlib import Path

from exam_materials_lib import ensure_root, load_rows, save_rows, ticket_id_from_arg, upsert_ticket, validate_ticket_text


def validate_ticket_file(root: Path, ticket_path: Path) -> tuple[str, list[str]]:
    ticket_id = ticket_id_from_arg(ticket_path.stem)
    text = ticket_path.read_text(encoding="utf-8")
    return ticket_id, validate_ticket_text(text)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default="exam_materials")
    args = parser.parse_args()

    root = Path(args.root)
    ensure_root(root)
    rows = load_rows(root)
    checked = 0
    ready = 0
    needs_fix = 0

    for ticket_path in sorted((root / "02_tickets").glob("ticket_*.md")):
        checked += 1
        ticket_id, issues = validate_ticket_file(root, ticket_path)
        row = upsert_ticket(rows, ticket_id)
        if issues:
            needs_fix += 1
            row["ticket_status"] = "fix"
            row["final_status"] = "fix"
            row["check_notes"] = "; ".join(issues)
            print(f"{ticket_path.name}: fix - {issues[0]}")
        else:
            ready += 1
            row["ticket_status"] = "ready"
            row["final_status"] = "ready"
            row["check_notes"] = row.get("check_notes", "")
            print(f"{ticket_path.name}: ready")

    save_rows(root, rows)
    print(f"checked: {checked}")
    print(f"ready: {ready}")
    print(f"needs fix: {needs_fix}")


if __name__ == "__main__":
    main()
