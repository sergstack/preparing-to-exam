import json
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
SCRIPT = ROOT_DIR / "scripts" / "ollama_quality_gate.py"


class MockOllamaQualityHandler(BaseHTTPRequestHandler):
    generated = []
    response_text = json.dumps({"status": "warn", "summary": "Нужна ручная проверка.", "issues": ["empty OCR text"]})

    def do_POST(self):
        length = int(self.headers.get("content-length", "0"))
        payload = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
        if self.path == "/api/generate":
            self.generated.append(payload)
            self.respond({"response": self.response_text})
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
    MockOllamaQualityHandler.generated = []
    MockOllamaQualityHandler.response_text = json.dumps(
        {"status": "warn", "summary": "Нужна ручная проверка.", "issues": ["empty OCR text"]}
    )
    server = HTTPServer(("127.0.0.1", 0), MockOllamaQualityHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, f"http://127.0.0.1:{server.server_port}"


def test_quality_gate_dry_run_does_not_call_ollama_or_write_report(tmp_path):
    input_dir = tmp_path / "tickets"
    input_dir.mkdir()
    (input_dir / "ticket_01.md").write_text("# Билет 01\n", encoding="utf-8")
    output = tmp_path / "report.md"

    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--input", str(input_dir), "--output", str(output), "--dry-run"],
        cwd=ROOT_DIR,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    assert "selected files: 1" in result.stdout
    assert "dry-run: Ollama not called and no report written" in result.stdout
    assert not output.exists()


def test_quality_gate_writes_report_from_mocked_ollama(tmp_path):
    server, url = run_mock_ollama()
    try:
        input_dir = tmp_path / "tickets"
        input_dir.mkdir()
        (input_dir / "ticket_01.md").write_text("# Билет 01\n\n## Кратко\n", encoding="utf-8")
        output = tmp_path / "ollama_quality_review.md"
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--input",
                str(input_dir),
                "--output",
                str(output),
                "--ollama-url",
                url,
                "--model",
                "test-model",
                "--sample",
                "1",
            ],
            cwd=ROOT_DIR,
            text=True,
            capture_output=True,
            check=False,
        )
    finally:
        server.shutdown()

    assert result.returncode == 0
    assert output.exists()
    report = output.read_text(encoding="utf-8")
    assert "`ticket_01.md`: warn" in report
    assert "empty OCR text" in report
    assert len(MockOllamaQualityHandler.generated) == 1
    prompt = MockOllamaQualityHandler.generated[0]["prompt"]
    assert str(input_dir) not in prompt
    assert "ticket_01.md" in prompt


def test_quality_gate_rejects_non_local_ollama_url(tmp_path):
    input_dir = tmp_path / "tickets"
    input_dir.mkdir()
    (input_dir / "ticket_01.md").write_text("# Билет 01\n", encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--input",
            str(input_dir),
            "--ollama-url",
            "https://example.com",
        ],
        cwd=ROOT_DIR,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 1
    assert "ollama-url must point to localhost or 127.0.0.1" in result.stdout


def test_quality_gate_handles_unavailable_ollama_gracefully(tmp_path):
    input_dir = tmp_path / "tickets"
    input_dir.mkdir()
    (input_dir / "ticket_01.md").write_text("# Билет 01\n", encoding="utf-8")
    output = tmp_path / "report.md"

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--input",
            str(input_dir),
            "--output",
            str(output),
            "--ollama-url",
            "http://127.0.0.1:9",
            "--timeout",
            "1",
        ],
        cwd=ROOT_DIR,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 2
    assert "Ollama unavailable or review failed gracefully" in result.stdout
    assert output.exists()
