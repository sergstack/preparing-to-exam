import sys
from pathlib import Path

import pytest


ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR / "scripts"))

import ocr_end_to_end_review_pack as e2e  # noqa: E402


def write_primary(root: Path, page: int, status: str = "success", text: str = "primary text") -> None:
    target = root / "05_ocr_pages" / f"page_{page:03d}.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        f"""# OCR Page {page:03d}

Status:
{status}

Text length:
{len(text)}

## OCR text

```text
{text}
```
""",
        encoding="utf-8",
    )


def write_recovery(root: Path, page: int, status: str = "success", text: str = "recovery text") -> None:
    target = root / "07_ocr_recovery" / f"recovery_page_{page:03d}.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        f"""# OCR Recovery Page {page:03d}

Status:
{status}

Text length after:
{len(text)}

## OCR text

```text
{text}
```
""",
        encoding="utf-8",
    )


def test_page_range_split_into_chunks():
    assert e2e.page_chunks(21, 30, 4) == [(21, 24), (25, 28), (29, 30)]


def test_dry_run_does_not_write_outputs(tmp_path, monkeypatch):
    root = tmp_path / "exam_materials"
    monkeypatch.setattr(sys, "argv", ["script", "--root", str(root), "--start", "21", "--end", "30", "--dry-run"])

    e2e.main()

    assert not root.exists()


def test_recovery_and_merge_are_called_after_primary(tmp_path, monkeypatch):
    root = tmp_path / "exam_materials"
    calls = []

    def fake_run(command, cwd):
        calls.append(command[1])
        if command[1].endswith("ollama_vision_batch_ocr.py"):
            start = int(command[command.index("--start") + 1])
            end = int(command[command.index("--end") + 1])
            for page in range(start, end + 1):
                if page == 22:
                    write_primary(root, page, "error", "")
                else:
                    write_primary(root, page, "success", "primary text" * 40)
        elif command[1].endswith("ollama_vision_recovery.py"):
            write_recovery(root, 22, "success", "recovery text" * 40)
        elif command[1].endswith("ocr_merge_review_pack.py"):
            pass
        return e2e.StepResult(command[1], 0, "", "")

    monkeypatch.setattr(e2e, "run_command", fake_run)
    monkeypatch.setattr(sys, "argv", ["script", "--root", str(root), "--start", "21", "--end", "23", "--chunk-size", "2", "--force"])

    e2e.main()

    assert calls == [
        "scripts/ollama_vision_batch_ocr.py",
        "scripts/ollama_vision_batch_ocr.py",
        "scripts/ollama_vision_recovery.py",
        "scripts/ocr_merge_review_pack.py",
    ]
    assert (root / "09_review_reports" / "ocr_end_to_end_summary.md").exists()
    assert (root / "09_review_reports" / "manual_review_plan.md").exists()


def test_continue_on_per_page_errors_and_records_recovery(tmp_path, monkeypatch):
    root = tmp_path / "exam_materials"

    def fake_run(command, cwd):
        if command[1].endswith("ollama_vision_batch_ocr.py"):
            write_primary(root, 21, "success", "primary text" * 40)
            write_primary(root, 22, "error", "")
        if command[1].endswith("ollama_vision_recovery.py"):
            write_recovery(root, 22, "success", "recovery text" * 40)
        return e2e.StepResult(command[1], 0, "", "")

    monkeypatch.setattr(e2e, "run_command", fake_run)
    monkeypatch.setattr(sys, "argv", ["script", "--root", str(root), "--start", "21", "--end", "22", "--max-errors", "10", "--force"])

    e2e.main()

    summary = (root / "09_review_reports" / "ocr_end_to_end_summary.md").read_text(encoding="utf-8")
    assert "error/other pages: 022" in summary
    assert "recovery candidates: 022" in summary
    assert "pages where recovery output was used: 022" in summary


def test_stop_when_max_errors_exceeded(tmp_path, monkeypatch):
    root = tmp_path / "exam_materials"
    calls = []

    def fake_run(command, cwd):
        calls.append(command[1])
        if command[1].endswith("ollama_vision_batch_ocr.py"):
            write_primary(root, 21, "error", "")
            write_primary(root, 22, "error", "")
        return e2e.StepResult(command[1], 0, "", "")

    monkeypatch.setattr(e2e, "run_command", fake_run)
    monkeypatch.setattr(sys, "argv", ["script", "--root", str(root), "--start", "21", "--end", "22", "--max-errors", "1"])

    with pytest.raises(SystemExit):
        e2e.main()

    assert "scripts/ollama_vision_recovery.py" not in calls


def test_outputs_are_only_under_ignored_artifact_folders(tmp_path, monkeypatch):
    root = tmp_path / "exam_materials"

    def fake_run(command, cwd):
        if command[1].endswith("ollama_vision_batch_ocr.py"):
            write_primary(root, 21, "success", "primary text" * 40)
        return e2e.StepResult(command[1], 0, "", "")

    monkeypatch.setattr(e2e, "run_command", fake_run)
    monkeypatch.setattr(sys, "argv", ["script", "--root", str(root), "--start", "21", "--end", "21", "--skip-recovery", "--skip-merge"])

    e2e.main()

    files = [path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file()]
    assert all(path.startswith(("05_ocr_pages/", "07_ocr_recovery/", "08_ocr_merged/", "09_review_reports/")) for path in files)


def test_review_reports_are_ignored_by_gitignore():
    gitignore = (ROOT_DIR / ".gitignore").read_text(encoding="utf-8")
    assert "exam_materials/09_review_reports/" in gitignore
