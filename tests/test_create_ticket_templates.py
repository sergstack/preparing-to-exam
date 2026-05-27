from scripts.create_ticket_templates import main as templates_main
from scripts.exam_materials_lib import load_rows
from scripts.init_exam_materials import main as init_main


def test_create_ticket_templates_from_raw_text(tmp_path, monkeypatch):
    root = tmp_path / "exam_materials"
    monkeypatch.setattr("sys.argv", ["init_exam_materials.py", "--root", str(root)])
    init_main()
    (root / "01_text" / "ticket_01_raw.md").write_text("# raw", encoding="utf-8")

    monkeypatch.setattr("sys.argv", ["create_ticket_templates.py", "--root", str(root)])
    templates_main()

    content = (root / "02_tickets" / "ticket_01.md").read_text(encoding="utf-8")
    assert "# Билет 01. Название" in content
    rows = load_rows(root)
    assert rows["01"]["ocr_status"] == "done"
    assert rows["01"]["ticket_status"] == "draft"
    assert rows["01"]["final_status"] == "draft"


def test_create_ticket_templates_does_not_overwrite_without_force(tmp_path, monkeypatch):
    root = tmp_path / "exam_materials"
    monkeypatch.setattr("sys.argv", ["init_exam_materials.py", "--root", str(root)])
    init_main()
    (root / "01_text" / "ticket_01_raw.md").write_text("# raw", encoding="utf-8")
    target = root / "02_tickets" / "ticket_01.md"
    target.write_text("custom", encoding="utf-8")

    monkeypatch.setattr("sys.argv", ["create_ticket_templates.py", "--root", str(root)])
    templates_main()

    assert target.read_text(encoding="utf-8") == "custom"


def test_create_ticket_templates_dry_run_does_not_modify_files_or_progress(tmp_path, monkeypatch, capsys):
    root = tmp_path / "exam_materials"
    monkeypatch.setattr("sys.argv", ["init_exam_materials.py", "--root", str(root)])
    init_main()
    (root / "01_text" / "ticket_01_raw.md").write_text("# raw", encoding="utf-8")
    before = (root / "progress.xlsx").read_bytes()

    monkeypatch.setattr("sys.argv", ["create_ticket_templates.py", "--root", str(root), "--dry-run"])
    templates_main()

    assert (root / "progress.xlsx").read_bytes() == before
    assert not (root / "02_tickets" / "ticket_01.md").exists()
    output = capsys.readouterr().out
    assert "ticket templates created: 1" in output
    assert "dry-run: no files or progress workbook modified" in output
