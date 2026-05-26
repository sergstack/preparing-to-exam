from __future__ import annotations

import argparse
from pathlib import Path

from exam_materials_lib import copy_file, ensure_root, load_rows, save_rows, ticket_id_from_arg, upsert_ticket, validate_ticket_text


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default="exam_materials")
    parser.add_argument("--ticket", required=True)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    root = Path(args.root)
    ticket_id = ticket_id_from_arg(args.ticket)
    ensure_root(root)
    rows = load_rows(root)
    row = upsert_ticket(rows, ticket_id)
    source = root / "02_tickets" / f"ticket_{ticket_id}.md"
    target = root / "03_final" / f"ticket_{ticket_id}.md"

    if not source.exists():
        row["final_status"] = "fix"
        row["check_notes"] = "missing draft"
        save_rows(root, rows)
        print(f"not promoted: ticket_{ticket_id}.md is missing")
        return

    text = source.read_text(encoding="utf-8")
    issues = validate_ticket_text(text)
    if issues:
        row["final_status"] = "fix"
        row["ticket_status"] = "fix"
        row["check_notes"] = "; ".join(issues)
        save_rows(root, rows)
        print(f"not promoted: {issues[0]}")
        return

    copied = copy_file(source, target, force=args.force)
    row["ticket_status"] = "done"
    row["final_status"] = "ready"
    row["check_notes"] = row.get("check_notes", "")
    save_rows(root, rows)
    print(f"promoted: {source} -> {target}" if copied else f"kept existing final: {target}")


if __name__ == "__main__":
    main()
