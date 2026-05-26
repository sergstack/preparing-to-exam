import json
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
SCRIPT = ROOT_DIR / "scripts" / "ollama_vision_recovery.py"


def create_png(path: Path) -> None:
    try:
        from PIL import Image
    except ImportError:
        path.write_bytes(b"not-a-real-png")
        return
    Image.new("RGB", (2, 2), "white").save(path)


def make_root(tmp_path: Path) -> Path:
    root = tmp_path / "exam_materials"
    preprocessed = root / "00_scans" / "_preprocessed"
    ocr_pages = root / "05_ocr_pages"
    preprocessed.mkdir(parents=True)
    ocr_pages.mkdir(parents=True)
    for page in range(1, 7):
        create_png(preprocessed / f"page_{page:03d}_ocr.png")
    return root


def write_ocr_page(root: Path, page: int, status: str, text: str, length: int | None = None) -> Path:
    target = root / "05_ocr_pages" / f"page_{page:03d}.md"
    target.write_text(
        f"""# OCR Page {page:03d}

Status:
{status}

Text length:
{len(text) if length is None else length}

## OCR text

```text
{text}
```
""",
        encoding="utf-8",
    )
    return target


class MockOllamaHandler(BaseHTTPRequestHandler):
    generated = []

    def do_GET(self):
        if self.path == "/api/version":
            self.respond({"version": "test"})
            return
        if self.path == "/api/tags":
            self.respond({"models": [{"name": "qwen2.5vl:32b"}]})
            return
        self.send_error(404)

    def do_POST(self):
        length = int(self.headers.get("content-length", "0"))
        payload = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
        if self.path == "/api/generate":
            type(self).generated.append(payload)
            self.respond({"response": f"recovered text {len(type(self).generated)}"})
            return
        self.send_error(404)

    def respond(self, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(200)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        return


def run_mock_ollama():
    MockOllamaHandler.generated = []
    server = HTTPServer(("127.0.0.1", 0), MockOllamaHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, f"http://127.0.0.1:{server.server_port}"


def run_recovery(root: Path, *args: str, url: str = "http://127.0.0.1:1") -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--root", str(root), "--ollama-url", url, *args],
        cwd=ROOT_DIR,
        text=True,
        capture_output=True,
        check=False,
    )


def test_detects_error_empty_short_and_unreadable_pages(tmp_path):
    root = make_root(tmp_path)
    write_ocr_page(root, 1, "success", "valid text" * 60)
    write_ocr_page(root, 2, "error", "")
    write_ocr_page(root, 3, "empty", "")
    write_ocr_page(root, 4, "success", "short")
    write_ocr_page(root, 5, "success", "[неразборчиво]\n" * 4, length=400)

    result = run_recovery(root, "--dry-run")

    retry_list = (root / "07_ocr_recovery" / "retry_list.md").read_text(encoding="utf-8")
    assert result.returncode == 0
    assert "page_002" in retry_list
    assert "page_003" in retry_list
    assert "page_004" in retry_list
    assert "page_005" in retry_list
    assert "page_001" not in retry_list


def test_dry_run_does_not_call_ollama(tmp_path):
    root = make_root(tmp_path)
    write_ocr_page(root, 2, "error", "")

    result = run_recovery(root, "--dry-run")

    assert result.returncode == 0
    assert "recovery attempted: 0" in result.stdout


def test_pages_override_replaces_auto_detection(tmp_path):
    root = make_root(tmp_path)
    write_ocr_page(root, 1, "success", "valid text" * 60)
    write_ocr_page(root, 2, "error", "")

    result = run_recovery(root, "--pages", "1", "--dry-run")

    retry_list = (root / "07_ocr_recovery" / "retry_list.md").read_text(encoding="utf-8")
    assert result.returncode == 0
    assert "page_001" in retry_list
    assert "page_002" not in retry_list


def test_recovery_output_is_written_under_07_and_source_pages_not_overwritten(tmp_path):
    server, url = run_mock_ollama()
    try:
        root = make_root(tmp_path)
        source_ocr = write_ocr_page(root, 2, "error", "")
        before = source_ocr.read_text(encoding="utf-8")
        result = run_recovery(root, "--pages", "2", "--force", url=url)
    finally:
        server.shutdown()

    assert result.returncode == 0
    assert source_ocr.read_text(encoding="utf-8") == before
    assert (root / "07_ocr_recovery" / "recovery_page_002.md").exists()
    assert (root / "07_ocr_recovery" / "ocr_recovery_summary.md").exists()
    assert len(MockOllamaHandler.generated) == 1


def test_existing_recovery_output_is_not_overwritten_without_force(tmp_path):
    server, url = run_mock_ollama()
    try:
        root = make_root(tmp_path)
        write_ocr_page(root, 2, "error", "")
        target = root / "07_ocr_recovery" / "recovery_page_002.md"
        target.parent.mkdir(parents=True)
        target.write_text("existing", encoding="utf-8")
        result = run_recovery(root, "--pages", "2", url=url)
    finally:
        server.shutdown()

    assert result.returncode == 0
    assert target.read_text(encoding="utf-8") == "existing"
    assert len(MockOllamaHandler.generated) == 0


def test_outputs_are_ignored_by_gitignore():
    gitignore = (ROOT_DIR / ".gitignore").read_text(encoding="utf-8")
    assert "exam_materials/07_ocr_recovery/" in gitignore
