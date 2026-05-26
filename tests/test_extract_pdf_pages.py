import importlib.util
import subprocess
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
SCRIPT = ROOT_DIR / "scripts" / "extract_pdf_pages.py"


def test_extract_pdf_pages_dry_run_does_not_write(tmp_path):
    root = tmp_path / "exam_materials"
    scan_dir = root / "00_scans"
    scan_dir.mkdir(parents=True)
    (scan_dir / "ticket_01_page_01.pdf").write_text("", encoding="utf-8")

    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--root", str(root), "--dry-run"],
        cwd=ROOT_DIR,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    assert "PDFs found: 1" in result.stdout
    assert "dry-run: no files written" in result.stdout
    assert not (scan_dir / "_preprocessed").exists()


def test_extract_pdf_pages_reports_missing_pymupdf_when_unavailable(tmp_path):
    if importlib.util.find_spec("fitz"):
        return
    root = tmp_path / "exam_materials"
    scan_dir = root / "00_scans"
    scan_dir.mkdir(parents=True)
    (scan_dir / "ticket_01_page_01.pdf").write_text("", encoding="utf-8")

    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--root", str(root)],
        cwd=ROOT_DIR,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 1
    assert "Missing optional dependency: pymupdf" in result.stdout
    assert "Traceback" not in result.stderr
