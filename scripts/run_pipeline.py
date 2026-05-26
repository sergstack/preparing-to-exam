from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from exam_materials_lib import SUPPORTED_SCAN_SUFFIXES, TICKET_RE, load_rows


SCRIPT_DIR = Path(__file__).resolve().parent


def run_step(script_name: str, root: Path, extra_args: list[str] | None = None) -> None:
    command = [sys.executable, str(SCRIPT_DIR / script_name), "--root", str(root)]
    if extra_args:
        command.extend(extra_args)
    print("$ " + " ".join(command))
    subprocess.run(command, check=True)


def dry_run_summary(root: Path) -> None:
    scan_dir = root / "00_scans"
    files = sorted(
        path
        for path in scan_dir.iterdir()
        if path.is_file() and path.suffix.lower() in SUPPORTED_SCAN_SUFFIXES
    ) if scan_dir.exists() else []
    ticket_ids = sorted({match.group("ticket") for path in files if (match := TICKET_RE.match(path.name))})
    unknown = [path.name for path in files if not TICKET_RE.match(path.name)]
    print("dry-run: no files or progress workbook will be modified")
    print(f"root: {root}")
    print(f"scan files found: {len(files)}")
    print(f"tickets detected: {len(ticket_ids)}")
    print(f"unknown filenames: {len(unknown)}")
    print(f"text stubs that would be checked/created: {len(ticket_ids)}")
    print("auto-promotion: skipped")


def strict_has_fix_status(root: Path) -> bool:
    if not (root / "progress.xlsx").exists():
        return False
    rows = load_rows(root)
    for row in rows.values():
        if row.get("final_status") == "fix":
            return True
        if row.get("ocr_status") in {"missing", "fix", "pending"}:
            return True
    return False


def promote_ready(root: Path, force: bool) -> None:
    rows = load_rows(root)
    for ticket_id, row in sorted(rows.items()):
        if ticket_id == "unknown" or row.get("final_status") != "ready":
            continue
        extra_args = ["--ticket", ticket_id]
        if force:
            extra_args.append("--force")
        run_step("promote_ticket.py", root, extra_args)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default="exam_materials")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--promote-ready", action="store_true")
    args = parser.parse_args()

    root = Path(args.root)
    if args.dry_run:
        dry_run_summary(root)
        return

    force_args = ["--force"] if args.force else []
    run_step("init_exam_materials.py", root, force_args)
    run_step("register_scans.py", root)
    run_step("create_text_stubs.py", root, force_args)
    run_step("create_ticket_templates.py", root, force_args)
    run_step("validate_text_stubs.py", root)
    run_step("validate_tickets.py", root)
    if args.promote_ready:
        promote_ready(root, args.force)

    rows = load_rows(root)
    print("pipeline summary:")
    print(f"tickets tracked: {len([ticket_id for ticket_id in rows if ticket_id != 'unknown'])}")
    print(f"rows needing fix: {len([row for row in rows.values() if row.get('final_status') == 'fix'])}")
    print(f"auto-promotion: {'enabled' if args.promote_ready else 'disabled'}")
    if args.strict and strict_has_fix_status(root):
        print("strict: fix or pending statuses found")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
