from __future__ import annotations

import argparse
from pathlib import Path

from exam_materials_lib import ensure_progress_workbook, ensure_root, write_file


README = """# Exam Materials

Local generated workspace for scans, OCR/manual text, ticket drafts, final
materials, and progress tracking.

This folder may contain private study materials. Generated contents are ignored
by git except `.gitkeep`.
"""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default="exam_materials")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    root = Path(args.root)
    ensure_root(root)
    ensure_progress_workbook(root)
    readme_created = write_file(root / "README.md", README, force=args.force)

    print(f"initialized: {root}")
    print("folders: 00_scans, 01_text, 02_tickets, 03_final")
    print(f"progress: {root / 'progress.xlsx'}")
    print(f"readme: {'written' if readme_created else 'kept'}")


if __name__ == "__main__":
    main()
