from scripts.exam_materials_lib import load_rows
from scripts.init_exam_materials import main as init_main
from scripts.register_scans import main as register_main


def test_register_scans_groups_supported_files(tmp_path, monkeypatch):
    root = tmp_path / "exam_materials"
    monkeypatch.setattr("sys.argv", ["init_exam_materials.py", "--root", str(root)])
    init_main()
    (root / "00_scans" / "ticket_01_page_01.jpg").write_text("", encoding="utf-8")
    (root / "00_scans" / "ticket_01_page_02.pdf").write_text("", encoding="utf-8")

    monkeypatch.setattr("sys.argv", ["register_scans.py", "--root", str(root)])
    register_main()

    rows = load_rows(root)
    assert rows["01"]["scan_files"] == "00_scans/ticket_01_page_01.jpg\n00_scans/ticket_01_page_02.pdf"
    assert rows["01"]["ocr_status"] == "pending"
    assert rows["01"]["final_status"] == "raw"


def test_register_scans_records_unknown_filename(tmp_path, monkeypatch):
    root = tmp_path / "exam_materials"
    monkeypatch.setattr("sys.argv", ["init_exam_materials.py", "--root", str(root)])
    init_main()
    (root / "00_scans" / "bad_name.jpg").write_text("", encoding="utf-8")

    monkeypatch.setattr("sys.argv", ["register_scans.py", "--root", str(root)])
    register_main()

    rows = load_rows(root)
    assert rows["unknown"]["check_notes"] == "filename_check"
