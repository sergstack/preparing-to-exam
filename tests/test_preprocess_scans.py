import subprocess
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
SCRIPT = ROOT_DIR / "scripts" / "preprocess_scans.py"


def test_preprocess_scans_dry_run_does_not_write(tmp_path):
    root = tmp_path / "exam_materials"
    scan_dir = root / "00_scans"
    scan_dir.mkdir(parents=True)
    (scan_dir / "ticket_01_page_01.jpg").write_text("", encoding="utf-8")

    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--root", str(root), "--dry-run"],
        cwd=ROOT_DIR,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    assert "input images found: 1" in result.stdout
    assert "dry-run: no files written" in result.stdout
    assert not (scan_dir / "_preprocessed").exists()


def test_preprocess_scans_processes_image_when_pillow_available(tmp_path):
    try:
        from PIL import Image
    except ImportError:
        return

    root = tmp_path / "exam_materials"
    scan_dir = root / "00_scans"
    scan_dir.mkdir(parents=True)
    Image.new("RGB", (2, 2), "white").save(scan_dir / "ticket_01_page_01.jpg")

    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--root", str(root), "--grayscale", "--contrast", "--binarize"],
        cwd=ROOT_DIR,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    assert "outputs written: 1" in result.stdout
    assert (scan_dir / "_preprocessed" / "ticket_01_page_01_ocr.png").exists()
