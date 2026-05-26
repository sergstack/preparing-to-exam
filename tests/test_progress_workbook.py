from openpyxl import load_workbook

from scripts.exam_materials_lib import PROGRESS_COLUMNS, ensure_progress_workbook
from scripts.validate_text_stubs import main as validate_text_main


def test_progress_workbook_columns(tmp_path):
    root = tmp_path / "exam_materials"
    root.mkdir()

    ensure_progress_workbook(root)

    workbook = load_workbook(root / "progress.xlsx")
    sheet = workbook.active
    assert [cell.value for cell in sheet[1]] == list(PROGRESS_COLUMNS)
    workbook.close()


def test_validate_text_stubs_updates_empty_and_non_empty_statuses(tmp_path, monkeypatch):
    from scripts.exam_materials_lib import save_rows, text_stub

    root = tmp_path / "exam_materials"
    (root / "01_text").mkdir(parents=True)
    rows = {
        "01": {
            "ticket_id": "01",
            "scan_files": "00_scans/ticket_01_page_01.jpg",
            "ocr_status": "pending",
            "ticket_status": "raw",
            "check_notes": "",
            "final_status": "raw",
            "updated_at": "",
        },
        "02": {
            "ticket_id": "02",
            "scan_files": "00_scans/ticket_02_page_01.jpg",
            "ocr_status": "pending",
            "ticket_status": "raw",
            "check_notes": "",
            "final_status": "raw",
            "updated_at": "",
        },
    }
    ensure_progress_workbook(root)
    save_rows(root, rows)
    (root / "01_text" / "ticket_01_raw.md").write_text(text_stub("01", rows["01"]["scan_files"]), encoding="utf-8")
    (root / "01_text" / "ticket_02_raw.md").write_text(
        text_stub("02", rows["02"]["scan_files"]).replace("[paste OCR text here]", "Recognized text."),
        encoding="utf-8",
    )

    monkeypatch.setattr("sys.argv", ["validate_text_stubs.py", "--root", str(root)])
    validate_text_main()

    from scripts.exam_materials_lib import load_rows

    updated = load_rows(root)
    assert updated["01"]["ocr_status"] == "pending"
    assert "empty OCR text" in updated["01"]["check_notes"]
    assert updated["02"]["ocr_status"] == "done"
