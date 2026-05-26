import subprocess
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
SCRIPT = ROOT_DIR / "scripts" / "validate_checked_text.py"


def make_root(tmp_path: Path) -> Path:
    root = tmp_path / "exam_materials"
    (root / "08_ocr_merged").mkdir(parents=True)
    (root / "10_checked_text").mkdir(parents=True)
    return root


def write_merged(root: Path, page: int) -> None:
    (root / "08_ocr_merged" / f"merged_page_{page:03d}.md").write_text("# merged\n", encoding="utf-8")


def write_checked(root: Path, page: int, status: str = "draft", priority: str = "normal", text: str = "checked text") -> None:
    (root / "10_checked_text" / f"checked_page_{page:03d}.md").write_text(
        f"""# Checked Text Page {page:03d}

Source:
merged_page_{page:03d}.md

Review priority:
{priority}

Status:
{status}

## Reviewer notes

## Checked text

```text
{text}
```
""",
        encoding="utf-8",
    )


def run_script(root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(SCRIPT), "--root", str(root)], cwd=ROOT_DIR, text=True, capture_output=True, check=False)


def test_validation_detects_missing_sections(tmp_path):
    root = make_root(tmp_path)
    write_merged(root, 1)
    (root / "10_checked_text" / "checked_page_001.md").write_text("# broken\n", encoding="utf-8")

    result = run_script(root)

    summary = (root / "10_checked_text" / "checked_text_validation_summary.md").read_text(encoding="utf-8")
    assert result.returncode == 0
    assert "missing section" in summary


def test_validation_detects_non_ready_pages(tmp_path):
    root = make_root(tmp_path)
    write_merged(root, 1)
    write_checked(root, 1, status="draft")

    result = run_script(root)

    summary = (root / "10_checked_text" / "checked_text_validation_summary.md").read_text(encoding="utf-8")
    assert result.returncode == 0
    assert "non-ready pages: 1" in summary


def test_unreadable_checked_page_is_not_ready(tmp_path):
    root = make_root(tmp_path)
    write_merged(root, 1)
    write_checked(root, 1, status="checked", text="[неразборчиво]")

    run_script(root)

    summary = (root / "10_checked_text" / "checked_text_validation_summary.md").read_text(encoding="utf-8")
    assert "checked page still contains unreadable marker" in summary


def test_dashboard_is_created(tmp_path):
    root = make_root(tmp_path)
    write_merged(root, 1)
    write_checked(root, 1, status="needs_manual_fix", priority="high")

    result = run_script(root)

    dashboard = root / "10_checked_text" / "review_dashboard.md"
    assert result.returncode == 0
    assert dashboard.exists()
    assert "high-priority pages: 1" in dashboard.read_text(encoding="utf-8")
