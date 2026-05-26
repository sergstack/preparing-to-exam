import subprocess
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
SCRIPT = ROOT_DIR / "scripts" / "ocr_merge_review_pack.py"


def make_root(tmp_path: Path) -> Path:
    root = tmp_path / "exam_materials"
    (root / "05_ocr_pages").mkdir(parents=True)
    (root / "07_ocr_recovery").mkdir(parents=True)
    return root


def write_primary(root: Path, page: int, status: str = "success", text: str = "primary text") -> Path:
    target = root / "05_ocr_pages" / f"page_{page:03d}.md"
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
    return target


def write_recovery(root: Path, page: int, status: str = "success", text: str = "recovery text") -> Path:
    target = root / "07_ocr_recovery" / f"recovery_page_{page:03d}.md"
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
    return target


def run_merge(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--root", str(root), *args],
        cwd=ROOT_DIR,
        text=True,
        capture_output=True,
        check=False,
    )


def test_recovery_overrides_primary_for_same_page(tmp_path):
    root = make_root(tmp_path)
    write_primary(root, 1, text="old primary")
    write_recovery(root, 1, text="new recovery")

    result = run_merge(root)

    merged = (root / "08_ocr_merged" / "merged_page_001.md").read_text(encoding="utf-8")
    assert result.returncode == 0
    assert "Source:\nrecovery" in merged
    assert "new recovery" in merged
    assert "old primary" not in merged


def test_primary_used_when_no_recovery_exists(tmp_path):
    root = make_root(tmp_path)
    write_primary(root, 1, text="primary only")

    result = run_merge(root)

    merged = (root / "08_ocr_merged" / "merged_page_001.md").read_text(encoding="utf-8")
    assert result.returncode == 0
    assert "Source:\nprimary" in merged
    assert "primary only" in merged


def test_missing_page_goes_to_manual_review_and_order_is_preserved(tmp_path):
    root = make_root(tmp_path)
    write_primary(root, 1, text="first")
    write_primary(root, 3, text="third")

    result = run_merge(root)

    manual = (root / "08_ocr_merged" / "manual_review_list.md").read_text(encoding="utf-8")
    full_text = (root / "08_ocr_merged" / "merged_full_text.md").read_text(encoding="utf-8")
    assert result.returncode == 0
    assert "page_002" in manual
    assert full_text.index("## Page 001") < full_text.index("## Page 002") < full_text.index("## Page 003")


def test_full_text_created(tmp_path):
    root = make_root(tmp_path)
    write_primary(root, 1, text="page one")

    result = run_merge(root)

    full_text = root / "08_ocr_merged" / "merged_full_text.md"
    assert result.returncode == 0
    assert full_text.exists()
    assert "near-verbatim / light cleanup only" in full_text.read_text(encoding="utf-8")


def test_nested_code_fences_inside_ocr_text_are_preserved(tmp_path):
    root = make_root(tmp_path)
    write_recovery(root, 1, text="before\n```text\ninner\n```\nafter")

    result = run_merge(root)

    merged = (root / "08_ocr_merged" / "merged_page_001.md").read_text(encoding="utf-8")
    assert result.returncode == 0
    assert "before" in merged
    assert "inner" in merged
    assert "after" in merged
    assert "````text" in merged


def test_service_headings_stripped_only_when_flag_used(tmp_path):
    root = make_root(tmp_path)
    text = "### Расшифровка текста:\n\nactual text\n\n### Примечания:\n1. model note"
    write_recovery(root, 1, text=text)

    run_merge(root, "--force")
    unstripped = (root / "08_ocr_merged" / "merged_page_001.md").read_text(encoding="utf-8")
    run_merge(root, "--strip-service-headings", "--force")
    stripped = (root / "08_ocr_merged" / "merged_page_001.md").read_text(encoding="utf-8")

    assert "Расшифровка текста" in unstripped
    assert "Примечания" in unstripped
    assert "Расшифровка текста" not in stripped
    assert "Примечания" not in stripped
    assert "actual text" in stripped


def test_source_files_are_not_modified(tmp_path):
    root = make_root(tmp_path)
    primary = write_primary(root, 1, text="primary")
    recovery = write_recovery(root, 1, text="recovery")
    before_primary = primary.read_text(encoding="utf-8")
    before_recovery = recovery.read_text(encoding="utf-8")

    result = run_merge(root)

    assert result.returncode == 0
    assert primary.read_text(encoding="utf-8") == before_primary
    assert recovery.read_text(encoding="utf-8") == before_recovery


def test_dry_run_does_not_write_outputs(tmp_path):
    root = make_root(tmp_path)
    write_primary(root, 1, text="primary")

    result = run_merge(root, "--dry-run")

    assert result.returncode == 0
    assert not (root / "08_ocr_merged").exists()


def test_outputs_are_under_08_ocr_merged(tmp_path):
    root = make_root(tmp_path)
    write_primary(root, 1, text="primary")

    result = run_merge(root)

    files = [path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file()]
    assert result.returncode == 0
    assert any(path.startswith("08_ocr_merged/") for path in files)
    assert all(path.startswith(("05_ocr_pages/", "07_ocr_recovery/", "08_ocr_merged/")) for path in files)


def test_outputs_are_ignored_by_gitignore():
    gitignore = (ROOT_DIR / ".gitignore").read_text(encoding="utf-8")
    assert "exam_materials/08_ocr_merged/" in gitignore
