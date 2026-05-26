from __future__ import annotations

import argparse
from pathlib import Path

from exam_materials_lib import iter_preprocessed_images, iter_raw_image_files, iter_raw_pdf_files, iter_raw_scan_files


def recommendation(pdf_count: int, image_count: int, preprocessed_count: int) -> str:
    if preprocessed_count:
        return "Run a small OCR trial on preprocessed images, then validate text stubs."
    if pdf_count:
        return "Extract PDF pages, preprocess generated images, then choose an OCR option."
    if image_count:
        return "Preprocess image scans, then choose an OCR option."
    return "Add local scans or PDFs to exam_materials/00_scans/."


def report_text(root: Path) -> str:
    raw_files = iter_raw_scan_files(root)
    pdfs = iter_raw_pdf_files(root)
    images = iter_raw_image_files(root)
    preprocessed = iter_preprocessed_images(root)
    ready = len(preprocessed)
    needs_preprocessing = len(images) + len(pdfs)
    action = recommendation(len(pdfs), len(images), ready)
    return f"""# OCR Benchmark Gate Report

Root: `{root}`

## Counts

- raw files count: {len(raw_files)}
- PDFs count: {len(pdfs)}
- images count: {len(images)}
- preprocessed images count: {len(preprocessed)}
- files ready for OCR: {ready}
- files needing preprocessing: {needs_preprocessing}

## Recommended Next Action

{action}

## Suggested OCR Options

- manual OCR paste
- Tesseract
- PaddleOCR
- PaddleOCR-VL / vision model
- external OCR only after privacy approval

## Boundaries

This report does not run OCR, download models, call external APIs, or call an LLM.
"""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default="exam_materials")
    args = parser.parse_args()

    root = Path(args.root)
    report_path = root / "ocr_benchmark_report.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    content = report_text(root)
    report_path.write_text(content, encoding="utf-8")
    print(content)
    print(f"report written: {report_path}")


if __name__ == "__main__":
    main()
