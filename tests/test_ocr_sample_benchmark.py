import os
import json
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
SCRIPT = ROOT_DIR / "scripts" / "ocr_sample_benchmark.py"


def create_png(path: Path) -> None:
    try:
        from PIL import Image
    except ImportError:
        path.write_bytes(b"not-a-real-png")
        return
    Image.new("RGB", (2, 2), "white").save(path)


def test_engine_none_respects_limit_and_writes_report(tmp_path):
    root = tmp_path / "exam_materials"
    preprocessed = root / "00_scans" / "_preprocessed"
    preprocessed.mkdir(parents=True)
    for index in range(1, 8):
        create_png(preprocessed / f"page_{index:03d}.png")

    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--root", str(root), "--limit", "5", "--engine", "none"],
        cwd=ROOT_DIR,
        text=True,
        capture_output=True,
        check=False,
    )

    selection = root / "04_ocr_benchmark" / "sample_selection.md"
    summary = root / "04_ocr_benchmark" / "ocr_benchmark_summary.md"
    assert result.returncode == 0
    assert selection.read_text(encoding="utf-8").count("- 00_scans/_preprocessed/") == 5
    assert "engine=none: OCR not run" in summary.read_text(encoding="utf-8")
    assert "selected files: 5" in result.stdout
    assert "--engine paddleocr" not in result.stderr


def test_missing_tesseract_engine_returns_clean_blocker(tmp_path):
    root = tmp_path / "exam_materials"
    preprocessed = root / "00_scans" / "_preprocessed"
    preprocessed.mkdir(parents=True)
    create_png(preprocessed / "page_001.png")

    env = os.environ.copy()
    env["PATH"] = ""
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--root", str(root), "--limit", "1", "--engine", "tesseract"],
        cwd=ROOT_DIR,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 1
    assert "Missing OCR engine: tesseract" in result.stdout
    assert "Traceback" not in result.stderr


def test_paddleocr_missing_dependency_returns_clean_blocker(tmp_path):
    root = tmp_path / "exam_materials"
    preprocessed = root / "00_scans" / "_preprocessed"
    preprocessed.mkdir(parents=True)
    create_png(preprocessed / "page_001.png")

    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--root", str(root), "--limit", "1", "--engine", "paddleocr"],
        cwd=ROOT_DIR,
        text=True,
        capture_output=True,
        check=False,
    )

    if result.returncode == 0:
        return
    assert result.returncode == 1
    assert "Missing optional OCR dependency: paddleocr." in result.stdout
    assert "python3 -m pip install paddleocr" in result.stdout
    assert "Traceback" not in result.stderr


def test_paddleocr_is_listed_in_cli_choices():
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--help"],
        cwd=ROOT_DIR,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    assert "paddleocr" in result.stdout
    assert "ollama-vision" in result.stdout


def test_missing_ollama_endpoint_returns_clean_blocker(tmp_path):
    root = tmp_path / "exam_materials"
    preprocessed = root / "00_scans" / "_preprocessed"
    preprocessed.mkdir(parents=True)
    create_png(preprocessed / "page_001.png")

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--root",
            str(root),
            "--limit",
            "1",
            "--engine",
            "ollama-vision",
            "--ollama-url",
            "http://127.0.0.1:9",
        ],
        cwd=ROOT_DIR,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 1
    assert "Ollama request failed" in result.stdout
    assert "Traceback" not in result.stderr


class MockOllamaHandler(BaseHTTPRequestHandler):
    models = [{"name": "minicpm-v"}]
    pulled = []
    generated = []

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
        if self.path == "/api/pull":
            self.pulled.append(payload)
            self.models = [{"name": payload["name"]}]
            self.respond({"status": "success"})
            return
        if self.path == "/api/generate":
            self.generated.append(payload)
            self.respond({"response": "Тестовый OCR текст"})
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


def run_mock_ollama(handler_class):
    server = HTTPServer(("127.0.0.1", 0), handler_class)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, f"http://127.0.0.1:{server.server_port}"


def test_no_vision_model_found_returns_clean_blocker(tmp_path):
    class NoVisionHandler(MockOllamaHandler):
        models = [{"name": "llama3"}]

    server, url = run_mock_ollama(NoVisionHandler)
    try:
        root = tmp_path / "exam_materials"
        preprocessed = root / "00_scans" / "_preprocessed"
        preprocessed.mkdir(parents=True)
        create_png(preprocessed / "page_001.png")

        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--root", str(root), "--limit", "1", "--engine", "ollama-vision", "--ollama-url", url],
            cwd=ROOT_DIR,
            text=True,
            capture_output=True,
            check=False,
        )
    finally:
        server.shutdown()

    assert result.returncode == 1
    assert "No Ollama vision model found" in result.stdout
    assert "Suggested first tries: minicpm-v, llava, llama3.2-vision." in result.stdout
    assert "Traceback" not in result.stderr


def test_pull_model_calls_remote_api_and_writes_result(tmp_path):
    class PullHandler(MockOllamaHandler):
        models = []
        pulled = []
        generated = []

    server, url = run_mock_ollama(PullHandler)
    try:
        root = tmp_path / "exam_materials"
        preprocessed = root / "00_scans" / "_preprocessed"
        preprocessed.mkdir(parents=True)
        for index in range(1, 3):
            create_png(preprocessed / f"page_{index:03d}.png")

        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--root",
                str(root),
                "--limit",
                "1",
                "--engine",
                "ollama-vision",
                "--ollama-url",
                url,
                "--model",
                "minicpm-v",
                "--pull-model",
            ],
            cwd=ROOT_DIR,
            text=True,
            capture_output=True,
            check=False,
        )
    finally:
        server.shutdown()

    assert result.returncode == 0
    assert PullHandler.pulled == [{"name": "minicpm-v", "stream": False}]
    assert len(PullHandler.generated) == 1
    result_file = root / "04_ocr_benchmark" / "ollama_vision_result_001.md"
    assert "Тестовый OCR текст" in result_file.read_text(encoding="utf-8")
    assert not (root / "04_ocr_benchmark" / "ollama_vision_result_002.md").exists()


def test_source_png_is_not_modified(tmp_path):
    root = tmp_path / "exam_materials"
    preprocessed = root / "00_scans" / "_preprocessed"
    preprocessed.mkdir(parents=True)
    source = preprocessed / "page_001.png"
    create_png(source)
    before = source.read_bytes()

    subprocess.run(
        [sys.executable, str(SCRIPT), "--root", str(root), "--limit", "1", "--engine", "none"],
        cwd=ROOT_DIR,
        text=True,
        capture_output=True,
        check=False,
    )

    assert source.read_bytes() == before


def test_ocr_outputs_are_ignored_by_gitignore():
    gitignore = (ROOT_DIR / ".gitignore").read_text(encoding="utf-8")
    assert "exam_materials/04_ocr_benchmark/" in gitignore


def test_outputs_are_written_only_to_benchmark_dir(tmp_path):
    root = tmp_path / "exam_materials"
    preprocessed = root / "00_scans" / "_preprocessed"
    preprocessed.mkdir(parents=True)
    create_png(preprocessed / "page_001.png")

    subprocess.run(
        [sys.executable, str(SCRIPT), "--root", str(root), "--limit", "1", "--engine", "none"],
        cwd=ROOT_DIR,
        text=True,
        capture_output=True,
        check=False,
    )

    files = [path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file()]
    assert "04_ocr_benchmark/sample_selection.md" in files
    assert "04_ocr_benchmark/ocr_benchmark_summary.md" in files
    assert all(path.startswith("00_scans/") or path.startswith("04_ocr_benchmark/") for path in files)
