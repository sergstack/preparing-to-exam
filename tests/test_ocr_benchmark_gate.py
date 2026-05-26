import subprocess
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
SCRIPT = ROOT_DIR / "scripts" / "ocr_benchmark_gate.py"


def test_ocr_benchmark_gate_writes_report(tmp_path):
    root = tmp_path / "exam_materials"
    scan_dir = root / "00_scans"
    preprocessed = scan_dir / "_preprocessed"
    preprocessed.mkdir(parents=True)
    (scan_dir / "ticket_01_page_01.jpg").write_text("", encoding="utf-8")
    (scan_dir / "ticket_02_page_01.pdf").write_text("", encoding="utf-8")
    (preprocessed / "ticket_01_page_01_ocr.png").write_text("", encoding="utf-8")

    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--root", str(root)],
        cwd=ROOT_DIR,
        text=True,
        capture_output=True,
        check=False,
    )

    report = root / "ocr_benchmark_report.md"
    content = report.read_text(encoding="utf-8")
    assert result.returncode == 0
    assert report.exists()
    assert "raw files count: 2" in content
    assert "PDFs count: 1" in content
    assert "images count: 1" in content
    assert "preprocessed images count: 1" in content
    assert "external OCR only after privacy approval" in content
