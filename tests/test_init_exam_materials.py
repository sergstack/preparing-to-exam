from pathlib import Path

from openpyxl import load_workbook

from scripts.exam_materials_lib import PROGRESS_COLUMNS
from scripts.init_exam_materials import main as init_main


def test_init_creates_required_folders_and_progress(tmp_path, monkeypatch):
    root = tmp_path / "exam_materials"
    monkeypatch.setattr("sys.argv", ["init_exam_materials.py", "--root", str(root)])

    init_main()
    init_main()

    for name in ("00_scans", "01_text", "02_tickets", "03_final"):
        assert (root / name).is_dir()
    assert (root / "README.md").is_file()

    workbook = load_workbook(root / "progress.xlsx")
    sheet = workbook.active
    assert [cell.value for cell in sheet[1]] == list(PROGRESS_COLUMNS)
    workbook.close()


def test_init_does_not_overwrite_readme_without_force(tmp_path, monkeypatch):
    root = tmp_path / "exam_materials"
    root.mkdir()
    readme = root / "README.md"
    readme.write_text("custom", encoding="utf-8")
    monkeypatch.setattr("sys.argv", ["init_exam_materials.py", "--root", str(root)])

    init_main()

    assert readme.read_text(encoding="utf-8") == "custom"
