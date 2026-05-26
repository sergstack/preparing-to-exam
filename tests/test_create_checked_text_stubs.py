import subprocess
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
SCRIPT = ROOT_DIR / "scripts" / "create_checked_text_stubs.py"


def make_root(tmp_path: Path) -> Path:
    root = tmp_path / "exam_materials"
    (root / "08_ocr_merged").mkdir(parents=True)
    (root / "09_review_reports").mkdir(parents=True)
    return root


def write_merged(root: Path, page: int, text: str = "merged text") -> None:
    (root / "08_ocr_merged" / f"merged_page_{page:03d}.md").write_text(
        f"""# Merged OCR Page {page:03d}

Status:
selected

## OCR text

```text
{text}
```
""",
        encoding="utf-8",
    )


def run_script(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(SCRIPT), "--root", str(root), *args], cwd=ROOT_DIR, text=True, capture_output=True, check=False)


def test_checked_stubs_are_created_from_merged_pages(tmp_path):
    root = make_root(tmp_path)
    write_merged(root, 1, "merged page one")

    result = run_script(root)

    target = root / "10_checked_text" / "checked_page_001.md"
    assert result.returncode == 0
    assert target.exists()
    assert "merged_page_001.md" in target.read_text(encoding="utf-8")
    assert "merged page one" in target.read_text(encoding="utf-8")


def test_existing_checked_stubs_are_not_overwritten_without_force(tmp_path):
    root = make_root(tmp_path)
    write_merged(root, 1, "new text")
    target = root / "10_checked_text" / "checked_page_001.md"
    target.parent.mkdir()
    target.write_text("manual edit", encoding="utf-8")

    result = run_script(root)

    assert result.returncode == 0
    assert target.read_text(encoding="utf-8") == "manual edit"


def test_high_priority_pages_are_marked(tmp_path):
    root = make_root(tmp_path)
    write_merged(root, 2, "important")
    (root / "09_review_reports" / "manual_review_plan.md").write_text("## High Priority Review\n\n- page_002\n", encoding="utf-8")

    result = run_script(root)

    text = (root / "10_checked_text" / "checked_page_002.md").read_text(encoding="utf-8")
    assert result.returncode == 0
    assert "Review priority:\nhigh" in text


def test_dry_run_does_not_write_outputs(tmp_path):
    root = make_root(tmp_path)
    write_merged(root, 1)

    result = run_script(root, "--dry-run")

    assert result.returncode == 0
    assert not (root / "10_checked_text").exists()
