from __future__ import annotations

import argparse
from pathlib import Path

from exam_materials_lib import ensure_root, load_rows, save_rows, text_stub, write_file


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default="exam_materials")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    root = Path(args.root)
    ensure_root(root)
    rows = load_rows(root)
    created = 0

    for ticket_id, row in sorted(rows.items()):
        if ticket_id == "unknown":
            continue
        path = root / "01_text" / f"ticket_{ticket_id}_raw.md"
        if write_file(path, text_stub(ticket_id, row.get("scan_files", "")), force=args.force):
            created += 1
        row["ocr_status"] = row.get("ocr_status") or "pending"
        row["final_status"] = row.get("final_status") or "ocr"

    save_rows(root, rows)
    print(f"text stubs created: {created}")
    print(f"progress: {root / 'progress.xlsx'}")


if __name__ == "__main__":
    main()
