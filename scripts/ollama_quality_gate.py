from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

from ocr_sample_benchmark import http_json, ollama_url


DEFAULT_DIMENSIONS = (
    "OCR/text completeness",
    "unreadable fragments",
    "formatting issues",
    "ticket structure",
    "missing question or answer sections",
    "duplicated fragments",
    "suspiciously short output",
    "Russian language readability",
    "exam-readiness",
)


@dataclass
class ReviewResult:
    source_name: str
    status: str
    issues: list[str]
    summary: str


def is_local_ollama_url(value: str) -> bool:
    return value.startswith("http://127.0.0.1:") or value.startswith("http://localhost:")


def selected_markdown_files(input_path: Path, sample: int) -> list[Path]:
    if input_path.is_file():
        files = [input_path]
    else:
        files = sorted(path for path in input_path.glob("*.md") if path.is_file())
    return files[: max(sample, 0)]


def build_prompt(source_name: str, text: str) -> str:
    dimensions = "\n".join(f"- {item}" for item in DEFAULT_DIMENSIONS)
    return (
        "Ты локальный ревьюер учебных материалов перед экзаменом.\n"
        "Проверь текст и верни только JSON без markdown.\n"
        "Не переписывай материал и не добавляй факты.\n"
        "Оцени только качество готовности текста к ручной проверке.\n\n"
        f"Файл: {source_name}\n"
        "Критерии:\n"
        f"{dimensions}\n\n"
        "JSON schema:\n"
        '{"status":"pass|warn|fail","summary":"short Russian summary","issues":["issue 1"]}\n\n'
        "Текст:\n"
        "```text\n"
        f"{text[:12000]}\n"
        "```"
    )


def normalize_review(source_name: str, payload: object) -> ReviewResult:
    if not isinstance(payload, dict):
        return ReviewResult(source_name, "fail", ["invalid JSON object"], "Модель вернула некорректный JSON.")
    status = payload.get("status")
    if status not in {"pass", "warn", "fail"}:
        return ReviewResult(source_name, "fail", ["invalid status"], "Модель вернула некорректный status.")
    issues_value = payload.get("issues", [])
    if not isinstance(issues_value, list) or not all(isinstance(item, str) for item in issues_value):
        return ReviewResult(source_name, "fail", ["invalid issues"], "Модель вернула некорректный список issues.")
    summary = payload.get("summary", "")
    if not isinstance(summary, str):
        summary = ""
    return ReviewResult(source_name, status, issues_value, summary.strip())


def parse_model_response(source_name: str, response_text: str) -> ReviewResult:
    try:
        payload = json.loads(response_text)
    except json.JSONDecodeError:
        return ReviewResult(source_name, "fail", ["invalid JSON response"], "Модель вернула невалидный JSON.")
    return normalize_review(source_name, payload)


def review_file(path: Path, model: str, base_url: str, timeout: int) -> ReviewResult:
    text = path.read_text(encoding="utf-8")
    payload = {
        "model": model,
        "prompt": build_prompt(path.name, text),
        "stream": False,
        "format": "json",
    }
    response = http_json("POST", ollama_url(base_url, "/api/generate"), payload, timeout=timeout)
    return parse_model_response(path.name, str(response.get("response", "")))


def render_report(input_path: Path, model: str, results: list[ReviewResult], dry_run: bool, note: str = "") -> str:
    lines = []
    for result in results:
        issue_text = "; ".join(result.issues) if result.issues else "none"
        lines.append(f"- `{result.source_name}`: {result.status} - {result.summary or 'no summary'}; issues: {issue_text}")
    return f"""# Ollama Quality Review

Input:
`{input_path}`

Model:
`{model}`

Dry-run:
{'yes' if dry_run else 'no'}

Note:
{note or 'none'}

## Results

{chr(10).join(lines) if lines else '- none'}

## Required Human Action

Review any `warn` or `fail` item manually. This report is advisory and does not modify source materials.
"""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output")
    parser.add_argument("--ollama-url", default="http://127.0.0.1:11434")
    parser.add_argument("--model", default="qwen2.5:7b")
    parser.add_argument("--sample", type=int, default=5)
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    input_path = Path(args.input)
    files = selected_markdown_files(input_path, args.sample)
    if args.dry_run:
        print(f"selected files: {len(files)}")
        for path in files:
            print(f"- {path.name}")
        print("dry-run: Ollama not called and no report written")
        return

    if not is_local_ollama_url(args.ollama_url):
        print("Blocker: ollama-url must point to localhost or 127.0.0.1")
        raise SystemExit(1)

    results: list[ReviewResult] = []
    note = ""
    try:
        for path in files:
            results.append(review_file(path, args.model, args.ollama_url, max(args.timeout, 1)))
    except Exception as exc:
        note = f"Ollama unavailable or review failed gracefully: {exc}"
        print(note)

    report = render_report(input_path, args.model, results, False, note)
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(report, encoding="utf-8")
        print(f"report: {output}")
    else:
        print(report)
    if note:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
