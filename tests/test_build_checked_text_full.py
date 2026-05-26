import subprocess
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
SCRIPT = ROOT_DIR / "scripts" / "build_checked_text_full.py"


def make_root(tmp_path: Path) -> Path:
    root = tmp_path / "exam_materials"
    (root / "10_checked_text").mkdir(parents=True)
    return root


def write_checked(root: Path, page: int, status: str, text: str) -> None:
    (root / "10_checked_text" / f"checked_page_{page:03d}.md").write_text(
        f"""# Checked Text Page {page:03d}

Status:
{status}

## Checked text

```text
{text}
```
""",
        encoding="utf-8",
    )


def run_script(root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(SCRIPT), "--root", str(root)], cwd=ROOT_DIR, text=True, capture_output=True, check=False)


def test_full_checked_text_preserves_page_order(tmp_path):
    root = make_root(tmp_path)
    write_checked(root, 2, "checked", "second")
    write_checked(root, 1, "checked", "first")

    result = run_script(root)

    full = (root / "10_checked_text" / "checked_full_text.md").read_text(encoding="utf-8")
    assert result.returncode == 0
    assert full.index("## Page 001") < full.index("## Page 002")
    assert "first" in full
    assert "second" in full


def test_full_checked_text_warns_when_pages_not_checked(tmp_path):
    root = make_root(tmp_path)
    write_checked(root, 1, "draft", "draft text")

    run_script(root)

    full = (root / "10_checked_text" / "checked_full_text.md").read_text(encoding="utf-8")
    assert "Some pages are not checked: 001" in full
