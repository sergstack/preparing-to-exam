import json
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
SCRIPT = ROOT_DIR / "scripts" / "ollama_vision_batch_ocr.py"


def create_png(path: Path) -> None:
    try:
        from PIL import Image
    except ImportError:
        path.write_bytes(b"not-a-real-png")
        return
    Image.new("RGB", (2, 2), "white").save(path)


class MockOllamaHandler(BaseHTTPRequestHandler):
    generated = []
    models = [{"name": "qwen2.5vl:7b"}]

    def do_GET(self):
        if self.path == "/api/version":
            self.respond({"version": "test"})
            return
        if self.path == "/api/tags":
            self.respond({"models": self.models})
            return
        self.send_error(404)

    def do_POST(self):
        length = int(self.headers.get("content-length", "0"))
        payload = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
        if self.path == "/api/generate":
            self.generated.append(payload)
            self.respond({"response": f"OCR text {len(self.generated)}"})
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


def run_mock_ollama(handler_class=MockOllamaHandler):
    handler_class.generated = []
    server = HTTPServer(("127.0.0.1", 0), handler_class)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, f"http://127.0.0.1:{server.server_port}"


def make_root(tmp_path: Path, count: int = 12) -> Path:
    root = tmp_path / "exam_materials"
    preprocessed = root / "00_scans" / "_preprocessed"
    preprocessed.mkdir(parents=True)
    for index in range(1, count + 1):
        create_png(preprocessed / f"page_{index:03d}_ocr.png")
    return root


def test_dry_run_respects_default_limit(tmp_path):
    server, url = run_mock_ollama()
    try:
        root = make_root(tmp_path, 12)
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--root", str(root), "--ollama-url", url, "--model", "qwen2.5vl:7b", "--dry-run"],
            cwd=ROOT_DIR,
            text=True,
            capture_output=True,
            check=False,
        )
    finally:
        server.shutdown()

    assert result.returncode == 0
    assert "selected pages: 10" in result.stdout
    assert len(MockOllamaHandler.generated) == 0
    assert (root / "05_ocr_pages" / "ocr_batch_summary.md").exists()
    assert not (root / "05_ocr_pages" / "page_001.md").exists()


def test_start_end_and_limit_call_generate_for_selected_pages(tmp_path):
    server, url = run_mock_ollama()
    try:
        root = make_root(tmp_path, 8)
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--root",
                str(root),
                "--ollama-url",
                url,
                "--model",
                "qwen2.5vl:7b",
                "--start",
                "2",
                "--end",
                "5",
                "--limit",
                "2",
            ],
            cwd=ROOT_DIR,
            text=True,
            capture_output=True,
            check=False,
        )
    finally:
        server.shutdown()

    assert result.returncode == 0
    assert len(MockOllamaHandler.generated) == 2
    assert (root / "05_ocr_pages" / "page_002.md").exists()
    assert (root / "05_ocr_pages" / "page_003.md").exists()
    assert not (root / "05_ocr_pages" / "page_004.md").exists()


def test_all_flag_processes_all_selected_pages(tmp_path):
    server, url = run_mock_ollama()
    try:
        root = make_root(tmp_path, 3)
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--root",
                str(root),
                "--ollama-url",
                url,
                "--model",
                "qwen2.5vl:7b",
                "--all",
            ],
            cwd=ROOT_DIR,
            text=True,
            capture_output=True,
            check=False,
        )
    finally:
        server.shutdown()

    assert result.returncode == 0
    assert len(MockOllamaHandler.generated) == 3


def test_existing_output_is_not_overwritten_without_force(tmp_path):
    server, url = run_mock_ollama()
    try:
        root = make_root(tmp_path, 1)
        out_dir = root / "05_ocr_pages"
        out_dir.mkdir(parents=True)
        target = out_dir / "page_001.md"
        target.write_text("custom", encoding="utf-8")
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--root", str(root), "--ollama-url", url, "--model", "qwen2.5vl:7b", "--limit", "1"],
            cwd=ROOT_DIR,
            text=True,
            capture_output=True,
            check=False,
        )
    finally:
        server.shutdown()

    assert result.returncode == 0
    assert target.read_text(encoding="utf-8") == "custom"
    assert len(MockOllamaHandler.generated) == 0


def test_source_png_is_not_modified(tmp_path):
    server, url = run_mock_ollama()
    try:
        root = make_root(tmp_path, 1)
        source = root / "00_scans" / "_preprocessed" / "page_001_ocr.png"
        before = source.read_bytes()
        subprocess.run(
            [sys.executable, str(SCRIPT), "--root", str(root), "--ollama-url", url, "--model", "qwen2.5vl:7b", "--limit", "1"],
            cwd=ROOT_DIR,
            text=True,
            capture_output=True,
            check=False,
        )
    finally:
        server.shutdown()

    assert source.read_bytes() == before


def test_missing_model_returns_clean_blocker(tmp_path):
    server, url = run_mock_ollama()
    try:
        root = make_root(tmp_path, 1)
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--root", str(root), "--ollama-url", url, "--model", "missing:latest", "--limit", "1"],
            cwd=ROOT_DIR,
            text=True,
            capture_output=True,
            check=False,
        )
    finally:
        server.shutdown()

    assert result.returncode == 1
    assert "Ollama model is not installed" in result.stdout
    assert "Traceback" not in result.stderr


def test_outputs_are_ignored_by_gitignore():
    gitignore = (ROOT_DIR / ".gitignore").read_text(encoding="utf-8")
    assert "exam_materials/05_ocr_pages/" in gitignore
