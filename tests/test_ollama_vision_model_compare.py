import json
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
SCRIPT = ROOT_DIR / "scripts" / "ollama_vision_model_compare.py"


def create_png(path: Path) -> None:
    try:
        from PIL import Image
    except ImportError:
        path.write_bytes(b"not-a-real-png")
        return
    Image.new("RGB", (2, 2), "white").save(path)


class MockOllamaHandler(BaseHTTPRequestHandler):
    models = [{"name": "qwen2.5vl:7b"}]
    pulled = []
    generated = []
    fail_pages = set()

    def do_GET(self):
        if self.path == "/api/tags":
            self.respond({"models": type(self).models})
            return
        self.send_error(404)

    def do_POST(self):
        length = int(self.headers.get("content-length", "0"))
        payload = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
        if self.path == "/api/pull":
            type(self).pulled.append(payload)
            type(self).models = [*type(self).models, {"name": payload["name"]}]
            self.respond({"status": "success"})
            return
        if self.path == "/api/generate":
            type(self).generated.append(payload)
            if len(type(self).generated) in type(self).fail_pages:
                self.send_error(500)
                return
            self.respond({"response": f"OCR text {len(type(self).generated)}"})
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
    handler_class.models = [{"name": "qwen2.5vl:7b"}]
    handler_class.pulled = []
    handler_class.generated = []
    server = HTTPServer(("127.0.0.1", 0), handler_class)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, f"http://127.0.0.1:{server.server_port}"


def make_root(tmp_path: Path, count: int = 10) -> Path:
    root = tmp_path / "exam_materials"
    preprocessed = root / "00_scans" / "_preprocessed"
    preprocessed.mkdir(parents=True)
    for index in range(1, count + 1):
        create_png(preprocessed / f"page_{index:03d}_ocr.png")
    return root


def test_parse_helpers():
    sys.path.insert(0, str(ROOT_DIR / "scripts"))
    from ollama_vision_model_compare import parse_models, parse_pages

    assert parse_models("a,b, c") == ["a", "b", "c"]
    assert parse_pages("2,4,10") == [2, 4, 10]


def test_missing_model_without_pull_returns_clean_blocker(tmp_path):
    server, url = run_mock_ollama()
    try:
        root = make_root(tmp_path)
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--root", str(root), "--ollama-url", url, "--models", "qwen2.5vl:32b", "--pages", "2"],
            cwd=ROOT_DIR,
            text=True,
            capture_output=True,
            check=False,
        )
    finally:
        server.shutdown()

    assert result.returncode == 1
    assert "Model is not installed" in result.stdout
    assert "Traceback" not in result.stderr


def test_pull_missing_calls_remote_pull_and_writes_outputs(tmp_path):
    server, url = run_mock_ollama()
    try:
        root = make_root(tmp_path)
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--root",
                str(root),
                "--ollama-url",
                url,
                "--models",
                "qwen2.5vl:7b,qwen2.5vl:32b",
                "--pages",
                "2,4",
                "--pull-missing",
            ],
            cwd=ROOT_DIR,
            text=True,
            capture_output=True,
            check=False,
        )
    finally:
        server.shutdown()

    assert result.returncode == 0
    assert MockOllamaHandler.pulled == [{"name": "qwen2.5vl:32b", "stream": False}]
    assert len(MockOllamaHandler.generated) == 4
    assert (root / "06_model_compare" / "qwen2_5vl_7b_page_002.md").exists()
    assert (root / "06_model_compare" / "qwen2_5vl_32b_page_004.md").exists()
    assert (root / "06_model_compare" / "model_compare_summary.md").exists()


def test_per_page_errors_are_recorded_without_crashing(tmp_path):
    class FailingHandler(MockOllamaHandler):
        fail_pages = {2}

    server, url = run_mock_ollama(FailingHandler)
    try:
        root = make_root(tmp_path)
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--root", str(root), "--ollama-url", url, "--models", "qwen2.5vl:7b", "--pages", "2,4"],
            cwd=ROOT_DIR,
            text=True,
            capture_output=True,
            check=False,
        )
    finally:
        server.shutdown()

    summary = root / "06_model_compare" / "model_compare_summary.md"
    assert result.returncode == 0
    assert "status=error" in summary.read_text(encoding="utf-8")
    assert "status=success" in summary.read_text(encoding="utf-8")


def test_outputs_stay_under_compare_dir_and_source_is_not_modified(tmp_path):
    server, url = run_mock_ollama()
    try:
        root = make_root(tmp_path, 1)
        source = root / "00_scans" / "_preprocessed" / "page_001_ocr.png"
        before = source.read_bytes()
        subprocess.run(
            [sys.executable, str(SCRIPT), "--root", str(root), "--ollama-url", url, "--models", "qwen2.5vl:7b", "--pages", "1"],
            cwd=ROOT_DIR,
            text=True,
            capture_output=True,
            check=False,
        )
    finally:
        server.shutdown()

    files = [path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file()]
    assert source.read_bytes() == before
    assert any(path.startswith("06_model_compare/") for path in files)
    assert all(path.startswith("00_scans/") or path.startswith("06_model_compare/") for path in files)


def test_outputs_are_ignored_by_gitignore():
    gitignore = (ROOT_DIR / ".gitignore").read_text(encoding="utf-8")
    assert "exam_materials/06_model_compare/" in gitignore
