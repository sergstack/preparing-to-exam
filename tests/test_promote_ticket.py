from scripts.exam_materials_lib import load_rows, ticket_template
from scripts.init_exam_materials import main as init_main
from scripts.promote_ticket import main as promote_main


def test_promote_ticket_success_when_sections_exist(tmp_path, monkeypatch):
    root = tmp_path / "exam_materials"
    monkeypatch.setattr("sys.argv", ["init_exam_materials.py", "--root", str(root)])
    init_main()
    source = root / "02_tickets" / "ticket_01.md"
    source.write_text(ticket_template("01"), encoding="utf-8")

    monkeypatch.setattr("sys.argv", ["promote_ticket.py", "--root", str(root), "--ticket", "01"])
    promote_main()

    assert (root / "03_final" / "ticket_01.md").read_text(encoding="utf-8") == source.read_text(encoding="utf-8")
    rows = load_rows(root)
    assert rows["01"]["ticket_status"] == "done"
    assert rows["01"]["final_status"] == "ready"


def test_promote_ticket_failure_when_sections_missing(tmp_path, monkeypatch):
    root = tmp_path / "exam_materials"
    monkeypatch.setattr("sys.argv", ["init_exam_materials.py", "--root", str(root)])
    init_main()
    (root / "02_tickets" / "ticket_01.md").write_text("# incomplete", encoding="utf-8")

    monkeypatch.setattr("sys.argv", ["promote_ticket.py", "--root", str(root), "--ticket", "01"])
    promote_main()

    assert not (root / "03_final" / "ticket_01.md").exists()
    rows = load_rows(root)
    assert rows["01"]["final_status"] == "fix"
    assert rows["01"]["check_notes"].startswith("missing sections:")
