from openpyxl import load_workbook

from scripts.exam_materials_lib import PROGRESS_COLUMNS, ensure_progress_workbook


def test_progress_workbook_columns(tmp_path):
    root = tmp_path / "exam_materials"
    root.mkdir()

    ensure_progress_workbook(root)

    workbook = load_workbook(root / "progress.xlsx")
    sheet = workbook.active
    assert [cell.value for cell in sheet[1]] == list(PROGRESS_COLUMNS)
    workbook.close()
