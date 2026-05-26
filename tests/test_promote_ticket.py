from scripts.exam_materials_lib import load_rows, ticket_template
from scripts.init_exam_materials import main as init_main
from scripts.promote_ticket import main as promote_main
from scripts.validate_tickets import main as validate_tickets_main


VALID_TICKET = """# Билет 01. Название

## Кратко
Краткий ответ.

## План ответа
1. Первый пункт
2. Второй пункт
3. Третий пункт

## Ответ на 5 минут
Развернутый ответ.

## Что выучить точно
Ключевые определения.

## Вопросы для самопроверки
1. Вопрос один?
2. Вопрос два?
3. Вопрос три?

## Проверить по скану

"""


def test_promote_ticket_success_when_sections_exist(tmp_path, monkeypatch):
    root = tmp_path / "exam_materials"
    monkeypatch.setattr("sys.argv", ["init_exam_materials.py", "--root", str(root)])
    init_main()
    source = root / "02_tickets" / "ticket_01.md"
    source.write_text(VALID_TICKET, encoding="utf-8")

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
    assert rows["01"]["check_notes"].startswith("missing header:")


def test_validate_tickets_detects_empty_sections(tmp_path, monkeypatch):
    root = tmp_path / "exam_materials"
    monkeypatch.setattr("sys.argv", ["init_exam_materials.py", "--root", str(root)])
    init_main()
    (root / "02_tickets" / "ticket_01.md").write_text(ticket_template("01"), encoding="utf-8")

    monkeypatch.setattr("sys.argv", ["validate_tickets.py", "--root", str(root)])
    validate_tickets_main()

    rows = load_rows(root)
    assert rows["01"]["ticket_status"] == "fix"
    assert rows["01"]["final_status"] == "fix"
    assert "empty section: Кратко" in rows["01"]["check_notes"]


def test_validate_tickets_detects_unresolved_scan_checks(tmp_path, monkeypatch):
    root = tmp_path / "exam_materials"
    monkeypatch.setattr("sys.argv", ["init_exam_materials.py", "--root", str(root)])
    init_main()
    ticket = VALID_TICKET.replace("## Проверить по скану\n\n", "## Проверить по скану\n- сверить формулу\n")
    (root / "02_tickets" / "ticket_01.md").write_text(ticket, encoding="utf-8")

    monkeypatch.setattr("sys.argv", ["validate_tickets.py", "--root", str(root)])
    validate_tickets_main()

    rows = load_rows(root)
    assert rows["01"]["final_status"] == "fix"
    assert "unresolved scan checks" in rows["01"]["check_notes"]
