from __future__ import annotations

import argparse
import base64
from dataclasses import dataclass
from pathlib import Path

from exam_materials_lib import iter_preprocessed_images
from ocr_sample_benchmark import http_json, ollama_url, preview
from ollama_vision_batch_ocr import OCR_PROMPT


@dataclass
class CompareResult:
    model: str
    page: int
    source: Path
    status: str
    text_length: int
    preview_text: str
    note: str = ""


def compare_dir(root: Path) -> Path:
    return root / "06_model_compare"


def parse_models(value: str) -> list[str]:
    return [part.strip() for part in value.split(",") if part.strip()]


def parse_pages(value: str) -> list[int]:
    pages = []
    for part in value.split(","):
        part = part.strip()
        if not part:
            continue
        pages.append(int(part))
    return pages


def safe_model_name(model: str) -> str:
    return model.replace(":", "_").replace("/", "_").replace(".", "_").replace("-", "_")


def ocr_ready_images(root: Path) -> list[Path]:
    images = iter_preprocessed_images(root)
    ready = [path for path in images if path.stem.endswith("_ocr")]
    return ready or images


def image_for_page(root: Path, page: int) -> Path:
    images = ocr_ready_images(root)
    index = page - 1
    if index < 0 or index >= len(images):
        raise IndexError(f"page {page:03d} is outside available image range")
    return images[index]


def source_for_error(root: Path, page: int) -> Path:
    try:
        return image_for_page(root, page)
    except Exception:
        return root / "00_scans" / "_preprocessed" / f"page_{page:03d}_ocr.png"


def installed_models(ollama_base_url: str) -> list[str]:
    tags = http_json("GET", ollama_url(ollama_base_url, "/api/tags"))
    models = tags.get("models", [])
    names = []
    if isinstance(models, list):
        for item in models:
            if isinstance(item, dict):
                name = item.get("name") or item.get("model")
                if isinstance(name, str):
                    names.append(name)
    return names


def ensure_models(ollama_base_url: str, models: list[str], pull_missing: bool) -> tuple[list[str], list[str]]:
    existing = installed_models(ollama_base_url)
    status = []
    for model in models:
        if model in existing:
            status.append(f"{model}: already present")
            continue
        if not pull_missing:
            raise RuntimeError(f"Model is not installed on {ollama_base_url}: {model}. Re-run with --pull-missing to pull it remotely.")
        try:
            http_json("POST", ollama_url(ollama_base_url, "/api/pull"), {"name": model, "stream": False}, timeout=1800)
        except RuntimeError as exc:
            raise RuntimeError(f"Failed to pull model {model} via remote Ollama API: {exc}") from exc
        existing = installed_models(ollama_base_url)
        if model not in existing:
            raise RuntimeError(f"Model pull completed but model is still not listed by /api/tags: {model}")
        status.append(f"{model}: pulled")
    return existing, status


def run_vision_ocr(ollama_base_url: str, model: str, source: Path) -> str:
    payload = {
        "model": model,
        "prompt": OCR_PROMPT,
        "images": [base64.b64encode(source.read_bytes()).decode("ascii")],
        "stream": False,
    }
    response = http_json("POST", ollama_url(ollama_base_url, "/api/generate"), payload, timeout=900)
    return str(response.get("response", "")).strip()


def write_result(root: Path, result: CompareResult, text: str) -> None:
    target = compare_dir(root) / f"{safe_model_name(result.model)}_page_{result.page:03d}.md"
    content = f"""# Model Compare Result

Model:
`{result.model}`

Page:
{result.page:03d}

Source image:
`{result.source.relative_to(root).as_posix()}`

Status:
{result.status}

Text length:
{result.text_length}

## OCR text

```text
{text}
```
"""
    if result.note:
        content += f"\n## Notes\n\n{result.note}\n"
    target.write_text(content, encoding="utf-8")


def write_summary(root: Path, ollama_base_url: str, models: list[str], pages: list[int], model_status: list[str], results: list[CompareResult]) -> None:
    lines = [
        f"- model={result.model}, page={result.page:03d}, status={result.status}, length={result.text_length}, preview={result.preview_text}"
        for result in results
    ]
    content = f"""# Ollama Vision Model Compare Summary

## Metadata

- Ollama URL: {ollama_base_url}
- models compared: {', '.join(models)}
- pages compared: {', '.join(str(page) for page in pages)}
- model status: {'; '.join(model_status)}

## Results

{chr(10).join(lines) if lines else '- none'}

## Manual Quality Checklist

- Does the output preserve near-verbatim wording?
- Is Russian text readable?
- Are headings, lists, formulas, and numbering preserved?
- Are uncertain places marked instead of guessed?
- Does the model avoid converting notes into tickets?

## Recommendation Options

- keep `qwen2.5vl:7b`
- use `qwen2.5vl:32b` only for failed pages
- switch to `qwen2.5vl:32b` for all OCR
- try another model
- improve preprocessing
"""
    (compare_dir(root) / "model_compare_summary.md").write_text(content, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default="exam_materials")
    parser.add_argument("--ollama-url", default="http://127.0.0.1:11434")
    parser.add_argument("--models", required=True)
    parser.add_argument("--pages", required=True)
    parser.add_argument("--pull-missing", action="store_true")
    args = parser.parse_args()

    root = Path(args.root)
    out_dir = compare_dir(root)
    out_dir.mkdir(parents=True, exist_ok=True)
    models = parse_models(args.models)
    pages = parse_pages(args.pages)
    try:
        _, model_status = ensure_models(args.ollama_url, models, args.pull_missing)
    except RuntimeError as exc:
        print(f"Blocker: {exc}")
        raise SystemExit(1)

    results: list[CompareResult] = []
    for model in models:
        for page in pages:
            try:
                source = image_for_page(root, page)
                text = run_vision_ocr(args.ollama_url, model, source)
                status = "success" if text else "empty"
                result = CompareResult(model, page, source, status, len(text), preview(text))
                write_result(root, result, text)
            except Exception as exc:
                source = source_for_error(root, page)
                result = CompareResult(model, page, source, "error", 0, "", str(exc))
                write_result(root, result, "")
            results.append(result)

    write_summary(root, args.ollama_url, models, pages, model_status, results)
    print(f"models compared: {len(models)}")
    print(f"pages compared: {len(pages)}")
    print(f"output folder: {out_dir}")
    print(f"summary: {out_dir / 'model_compare_summary.md'}")


if __name__ == "__main__":
    main()
