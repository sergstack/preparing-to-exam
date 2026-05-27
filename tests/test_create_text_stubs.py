from scripts.create_text_stubs import main as stubs_main
from scripts.exam_materials_lib import load_rows
from scripts.init_exam_materials import main as init_main
from scripts.register_scans import main as register_main


def test_create_text_stubs_for_registered_tickets(tmp_path, monkeypatch):
    root = tmp_path / "exam_materials"
    monkeypatch.setattr("sys.argv", ["init_exam_materials.py", "--root", str(root)])
    init_main()
    (root / "00_scans" / "ticket_01_page_01.jpg").write_text("", encoding="utf-8")
    monkeypatch.setattr("sys.argv", ["register_scans.py", "--root", str(root)])
    register_main()

    monkeypatch.setattr("sys.argv", ["create_text_stubs.py", "--root", str(root)])
    stubs_main()

    text_path = root / "01_text" / "ticket_01_raw.md"
    content = text_path.read_text(encoding="utf-8")
    assert "# Ticket 01 OCR Text" in content
    assert "- 00_scans/ticket_01_page_01.jpg" in content
    assert "[paste OCR text here]" in content
    assert "## Manual checks" in content
    assert load_rows(root)["01"]["final_status"] == "raw"


def test_create_text_stubs_does_not_overwrite_without_force(tmp_path, monkeypatch):
    root = tmp_path / "exam_materials"
    monkeypatch.setattr("sys.argv", ["init_exam_materials.py", "--root", str(root)])
    init_main()
    rows = load_rows(root)
    rows["01"] = {
        "ticket_id": "01",
        "scan_files": "00_scans/ticket_01_page_01.jpg",
        "ocr_status": "pending",
        "ticket_status": "raw",
        "check_notes": "",
        "final_status": "raw",
        "updated_at": "",
    }
    from scripts.exam_materials_lib import save_rows

    save_rows(root, rows)
    target = root / "01_text" / "ticket_01_raw.md"
    target.write_text("custom", encoding="utf-8")

    monkeypatch.setattr("sys.argv", ["create_text_stubs.py", "--root", str(root)])
    stubs_main()

    assert target.read_text(encoding="utf-8") == "custom"


def test_create_text_stubs_dry_run_does_not_modify_files_or_progress(tmp_path, monkeypatch, capsys):
    root = tmp_path / "exam_materials"
    monkeypatch.setattr("sys.argv", ["init_exam_materials.py", "--root", str(root)])
    init_main()
    (root / "00_scans" / "ticket_01_page_01.jpg").write_text("", encoding="utf-8")
    monkeypatch.setattr("sys.argv", ["register_scans.py", "--root", str(root)])
    register_main()
    before = (root / "progress.xlsx").read_bytes()

    monkeypatch.setattr("sys.argv", ["create_text_stubs.py", "--root", str(root), "--dry-run"])
    stubs_main()

    assert (root / "progress.xlsx").read_bytes() == before
    assert not (root / "01_text" / "ticket_01_raw.md").exists()
    output = capsys.readouterr().out
    assert "text stubs created: 1" in output
    assert "dry-run: no files or progress workbook modified" in output
