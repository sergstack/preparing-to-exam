from __future__ import annotations

import argparse
from pathlib import Path

from exam_materials_lib import (
    append_note,
    ensure_root,
    has_non_empty_ocr_text,
    load_rows,
    missing_text_stub_sections,
    save_rows,
)


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

    for ticket_id, row in sorted(rows.items()):
        if ticket_id == "unknown":
            continue
        checked += 1
        path = root / "01_text" / f"ticket_{ticket_id}_raw.md"
        if not path.exists():
            needs_fix += 1
            row["ocr_status"] = "missing"
            row["final_status"] = row.get("final_status") or "raw"
            row["check_notes"] = append_note(row.get("check_notes", ""), "missing text stub")
            print(f"ticket_{ticket_id}_raw.md: fix - missing stub")
            continue

        text = path.read_text(encoding="utf-8")
        missing = missing_text_stub_sections(text)
        if missing:
            needs_fix += 1
            row["ocr_status"] = "fix"
            row["final_status"] = row.get("final_status") or "ocr"
            row["check_notes"] = append_note(row.get("check_notes", ""), "missing headings: " + ", ".join(missing))
            print(f"ticket_{ticket_id}_raw.md: fix - missing headings: {', '.join(missing)}")
            continue

        if has_non_empty_ocr_text(text):
            ready += 1
            row["ocr_status"] = "done"
            row["final_status"] = row.get("final_status") or "ocr"
            print(f"ticket_{ticket_id}_raw.md: done")
        else:
            needs_fix += 1
            row["ocr_status"] = "pending"
            row["final_status"] = row.get("final_status") or "ocr"
            row["check_notes"] = append_note(row.get("check_notes", ""), "empty OCR text")
            print(f"ticket_{ticket_id}_raw.md: fix - empty OCR text")

    save_rows(root, rows)
    print(f"checked: {checked}")
    print(f"ocr ready: {ready}")
    print(f"needs fix: {needs_fix}")


if __name__ == "__main__":
    main()
