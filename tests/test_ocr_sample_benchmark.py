import os
import subprocess
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
SCRIPT = ROOT_DIR / "scripts" / "ocr_sample_benchmark.py"


def create_png(path: Path) -> None:
    try:
        from PIL import Image
    except ImportError:
        path.write_bytes(b"not-a-real-png")
        return
    Image.new("RGB", (2, 2), "white").save(path)


def test_engine_none_respects_limit_and_writes_report(tmp_path):
    root = tmp_path / "exam_materials"
    preprocessed = root / "00_scans" / "_preprocessed"
    preprocessed.mkdir(parents=True)
    for index in range(1, 8):
        create_png(preprocessed / f"page_{index:03d}.png")

    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--root", str(root), "--limit", "5", "--engine", "none"],
        cwd=ROOT_DIR,
        text=True,
        capture_output=True,
        check=False,
    )

    selection = root / "04_ocr_benchmark" / "sample_selection.md"
    summary = root / "04_ocr_benchmark" / "ocr_benchmark_summary.md"
    assert result.returncode == 0
    assert selection.read_text(encoding="utf-8").count("- 00_scans/_preprocessed/") == 5
    assert "engine=none: OCR not run" in summary.read_text(encoding="utf-8")
    assert "selected files: 5" in result.stdout


def test_missing_tesseract_engine_returns_clean_blocker(tmp_path):
    root = tmp_path / "exam_materials"
    preprocessed = root / "00_scans" / "_preprocessed"
    preprocessed.mkdir(parents=True)
    create_png(preprocessed / "page_001.png")

    env = os.environ.copy()
    env["PATH"] = ""
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--root", str(root), "--limit", "1", "--engine", "tesseract"],
        cwd=ROOT_DIR,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 1
    assert "Missing OCR engine: tesseract" in result.stdout
    assert "Traceback" not in result.stderr


def test_source_png_is_not_modified(tmp_path):
    root = tmp_path / "exam_materials"
    preprocessed = root / "00_scans" / "_preprocessed"
    preprocessed.mkdir(parents=True)
    source = preprocessed / "page_001.png"
    create_png(source)
    before = source.read_bytes()

    subprocess.run(
        [sys.executable, str(SCRIPT), "--root", str(root), "--limit", "1", "--engine", "none"],
        cwd=ROOT_DIR,
        text=True,
        capture_output=True,
        check=False,
    )

    assert source.read_bytes() == before


def test_ocr_outputs_are_ignored_by_gitignore():
    gitignore = (ROOT_DIR / ".gitignore").read_text(encoding="utf-8")
    assert "exam_materials/04_ocr_benchmark/" in gitignore
