from __future__ import annotations

import argparse
import base64
from dataclasses import dataclass
from pathlib import Path

from exam_materials_lib import iter_preprocessed_images
from ocr_sample_benchmark import http_json, ollama_url


OCR_PROMPT = (
    "Ты выполняешь дословную расшифровку рукописного или сканированного конспекта.\n\n"
    "Задача: переписать текст слово в слово, сохраняя исходные формулировки автора.\n\n"
    "Разрешено только лёгкое приведение в читаемый вид:\n"
    "- исправить очевидный OCR-мусор;\n"
    "- аккуратно восстановить переносы строк;\n"
    "- сохранить заголовки, списки, нумерацию и сокращения;\n"
    "- если фрагмент не читается, написать [неразборчиво];\n"
    "- если слово сомнительно, пометить [проверить: ...].\n\n"
    "Запрещено:\n"
    "- пересказывать;\n"
    "- сокращать;\n"
    "- объяснять;\n"
    "- улучшать стиль;\n"
    "- добавлять факты;\n"
    "- менять термины;\n"
    "- превращать конспект в готовый билет.\n\n"
    "Верни только расшифрованный текст."
)


@dataclass
class PageResult:
    page_number: int
    source: Path
    target: Path
    status: str
    text_length: int
    note: str = ""


def output_dir(root: Path) -> Path:
    return root / "05_ocr_pages"


def output_path(root: Path, page_number: int) -> Path:
    return output_dir(root) / f"page_{page_number:03d}.md"


def ocr_ready_images(root: Path) -> list[Path]:
    images = iter_preprocessed_images(root)
    ready = [path for path in images if path.stem.endswith("_ocr")]
    return ready or images


def selected_images(root: Path, start: int, end: int | None, limit: int, all_pages: bool) -> list[tuple[int, Path]]:
    images = ocr_ready_images(root)
    start_index = max(start, 1) - 1
    stop_index = end if end is not None else None
    selected = list(enumerate(images[start_index:stop_index], start=start_index + 1))
    if all_pages:
        return selected
    return selected[:limit]


def check_ollama_model(ollama_base_url: str, model: str) -> list[str]:
    version = http_json("GET", ollama_url(ollama_base_url, "/api/version"))
    tags = http_json("GET", ollama_url(ollama_base_url, "/api/tags"))
    models = tags.get("models", [])
    names = []
    if isinstance(models, list):
        for item in models:
            if isinstance(item, dict):
                name = item.get("name") or item.get("model")
                if isinstance(name, str):
                    names.append(name)
    if model not in names:
        raise RuntimeError(f"Ollama model is not installed on {ollama_base_url}: {model}")
    return [
        f"Ollama URL: {ollama_base_url}",
        f"Ollama version: {version.get('version', 'unknown')}",
        f"model: {model}",
        f"available models: {', '.join(names) if names else 'none'}",
    ]


def run_ocr(source: Path, ollama_base_url: str, model: str) -> str:
    image = base64.b64encode(source.read_bytes()).decode("ascii")
    payload = {
        "model": model,
        "prompt": OCR_PROMPT,
        "images": [image],
        "stream": False,
    }
    response = http_json("POST", ollama_url(ollama_base_url, "/api/generate"), payload, timeout=600)
    return str(response.get("response", "")).strip()


def write_page(root: Path, page_number: int, source: Path, model: str, status: str, text: str, note: str = "") -> None:
    rel_source = source.relative_to(root).as_posix()
    content = f"""# OCR Page {page_number:03d}

Source image:
`{rel_source}`

Model:
`{model}`

Status:
{status}

Text length:
{len(text)}

## OCR text

```text
{text}
```
"""
    if note:
        content += f"\n## Notes\n\n{note}\n"
    output_path(root, page_number).write_text(content, encoding="utf-8")


def write_summary(root: Path, metadata: list[str], results: list[PageResult], dry_run: bool, all_pages: bool) -> None:
    lines = []
    for result in results:
        lines.append(
            f"- page_{result.page_number:03d}: {result.status}, length={result.text_length}, "
            f"source={result.source.relative_to(root).as_posix()}"
        )
    success = sum(1 for result in results if result.status == "success")
    empty = sum(1 for result in results if result.status == "empty")
    errors = sum(1 for result in results if result.status == "error")
    skipped = sum(1 for result in results if result.status.startswith("skipped"))
    content = f"""# Ollama Vision OCR Batch Summary

## Metadata

{chr(10).join(f"- {item}" for item in metadata)}
- dry-run: {'yes' if dry_run else 'no'}
- all pages requested: {'yes' if all_pages else 'no'}
- Transcription mode: near-verbatim / light cleanup only

## Counts

- selected pages: {len(results)}
- success: {success}
- empty: {empty}
- error: {errors}
- skipped: {skipped}

## Pages

{chr(10).join(lines) if lines else '- none'}

## Validation Checklist

- Review pages with `empty` or `error` status.
- Spot-check Russian readability before generating text stubs.
- Confirm headings, lists, and numbering are preserved well enough.
- Do not create tickets from OCR text until manual validation is complete.

## Recommended Next Step

Validate successful OCR pages, then copy approved text into `01_text/` stubs in a separate step.
"""
    (output_dir(root) / "ocr_batch_summary.md").write_text(content, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default="exam_materials")
    parser.add_argument("--ollama-url", default="http://127.0.0.1:11434")
    parser.add_argument("--model", required=True)
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--start", type=int, default=1)
    parser.add_argument("--end", type=int)
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()

    root = Path(args.root)
    out_dir = output_dir(root)
    out_dir.mkdir(parents=True, exist_ok=True)
    try:
        metadata = check_ollama_model(args.ollama_url, args.model)
    except RuntimeError as exc:
        print(f"Blocker: {exc}")
        raise SystemExit(1)
    pages = selected_images(root, args.start, args.end, max(args.limit, 0), args.all)
    results: list[PageResult] = []

    for page_number, source in pages:
        target = output_path(root, page_number)
        if target.exists() and not args.force:
            status = "skipped_existing" if args.resume else "skipped_existing"
            results.append(PageResult(page_number, source, target, status, 0, "target exists"))
            continue
        if args.dry_run:
            results.append(PageResult(page_number, source, target, "dry_run", 0))
            continue

        try:
            text = run_ocr(source, args.ollama_url, args.model)
            status = "success" if text else "empty"
            write_page(root, page_number, source, args.model, status, text)
            results.append(PageResult(page_number, source, target, status, len(text)))
        except Exception as exc:
            note = str(exc)
            write_page(root, page_number, source, args.model, "error", "", note)
            results.append(PageResult(page_number, source, target, "error", 0, note))

    write_summary(root, metadata, results, args.dry_run, args.all)
    print(f"selected pages: {len(results)}")
    print(f"output folder: {out_dir}")
    print(f"summary: {out_dir / 'ocr_batch_summary.md'}")


if __name__ == "__main__":
    main()
