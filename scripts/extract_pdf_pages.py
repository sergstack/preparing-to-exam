from __future__ import annotations

import argparse
from pathlib import Path

from exam_materials_lib import iter_raw_pdf_files, preprocessed_dir


MISSING_PYMUPDF = "Missing optional dependency: pymupdf. Install with: python3 -m pip install pymupdf"


def output_path_for(pdf_path: Path, page_number: int, output_dir: Path) -> Path:
    return output_dir / f"{pdf_path.stem}_page_{page_number:03d}.png"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default="exam_materials")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--zoom", type=float, default=300 / 72)
    args = parser.parse_args()

    root = Path(args.root)
    pdfs = iter_raw_pdf_files(root)
    output_dir = preprocessed_dir(root)
    skipped = 0
    extracted = 0
    planned_pages = 0

    if args.dry_run:
        print(f"PDFs found: {len(pdfs)}")
        print("pages planned: unknown in dry-run without opening PDFs")
        print(f"output folder: {output_dir}")
        print("skipped files: 0")
        print("dry-run: no files written")
        return

    try:
        import fitz
    except ImportError:
        print(MISSING_PYMUPDF)
        raise SystemExit(1)

    output_dir.mkdir(parents=True, exist_ok=True)
    for pdf_path in pdfs:
        try:
            document = fitz.open(pdf_path)
        except Exception as exc:
            skipped += 1
            print(f"skipped {pdf_path.name}: {exc}")
            continue
        with document:
            planned_pages += document.page_count
            matrix = fitz.Matrix(args.zoom, args.zoom)
            for page_index in range(document.page_count):
                target = output_path_for(pdf_path, page_index + 1, output_dir)
                if target.exists() and not args.force:
                    skipped += 1
                    continue
                pixmap = document.load_page(page_index).get_pixmap(matrix=matrix, alpha=False)
                pixmap.save(target)
                extracted += 1

    print(f"PDFs found: {len(pdfs)}")
    print(f"pages planned: {planned_pages}")
    print(f"pages extracted: {extracted}")
    print(f"output folder: {output_dir}")
    print(f"skipped files: {skipped}")


if __name__ == "__main__":
    main()
