import subprocess
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
RUN_PIPELINE = ROOT_DIR / "scripts" / "run_pipeline.py"


def test_run_pipeline_baseline(tmp_path):
    root = tmp_path / "exam_materials"
    scan_dir = root / "00_scans"
    scan_dir.mkdir(parents=True)
    (scan_dir / "ticket_01_page_01.jpg").write_text("", encoding="utf-8")

    result = subprocess.run(
        [sys.executable, str(RUN_PIPELINE), "--root", str(root)],
        cwd=ROOT_DIR,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    assert (root / "progress.xlsx").exists()
    assert (root / "01_text" / "ticket_01_raw.md").exists()
    assert (root / "02_tickets" / "ticket_01.md").exists()
    assert "pipeline summary:" in result.stdout


def test_run_pipeline_dry_run_does_not_modify_files(tmp_path):
    root = tmp_path / "exam_materials"
    scan_dir = root / "00_scans"
    scan_dir.mkdir(parents=True)
    (scan_dir / "ticket_01_page_01.jpg").write_text("", encoding="utf-8")

    result = subprocess.run(
        [sys.executable, str(RUN_PIPELINE), "--root", str(root), "--dry-run"],
        cwd=ROOT_DIR,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    assert not (root / "progress.xlsx").exists()
    assert not (root / "01_text").exists()
    assert "dry-run: no files or progress workbook will be modified" in result.stdout
