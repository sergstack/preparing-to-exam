from __future__ import annotations

import argparse
import base64
import json
import shutil
from pathlib import Path
from urllib import error, request

from exam_materials_lib import iter_preprocessed_images


SUPPORTED_ENGINES = {"none", "ollama-vision", "paddleocr", "tesseract"}
VISION_MODEL_HINTS = (
    "llava",
    "minicpm-v",
    "qwen-vl",
    "qwen2.5-vl",
    "qwen2.5vl",
    "llama3.2-vision",
    "bakllava",
    "moondream",
    "granite-vision",
)
MISSING_TESSERACT = "Missing OCR engine: tesseract. Install it locally before using --engine tesseract."
MISSING_PYTESSERACT = "Missing optional dependency: pytesseract. Install with: python3 -m pip install pytesseract"
MISSING_PADDLEOCR = "Missing optional OCR dependency: paddleocr.\nInstall with:\npython3 -m pip install paddleocr"
OLLAMA_PROMPT = (
    "Распознай текст на изображении. Верни только текст, как в источнике. "
    "Не пересказывай, не исправляй, не добавляй факты. Сохраняй русские слова, "
    "заголовки и списки. Если фрагмент не читается, напиши [неразборчиво]."
)


def benchmark_dir(root: Path) -> Path:
    return root / "04_ocr_benchmark"


def select_samples(root: Path, limit: int) -> list[Path]:
    images = iter_preprocessed_images(root)
    ocr_ready = [path for path in images if path.stem.endswith("_ocr")]
    return (ocr_ready or images)[:limit]


def relative_list(root: Path, paths: list[Path]) -> str:
    if not paths:
        return "- none"
    return "\n".join(f"- {path.relative_to(root).as_posix()}" for path in paths)


def write_selection(root: Path, samples: list[Path]) -> None:
    content = "# OCR Sample Selection\n\n" + relative_list(root, samples) + "\n"
    (benchmark_dir(root) / "sample_selection.md").write_text(content, encoding="utf-8")


def dependency_status(engine: str) -> tuple[bool, list[str]]:
    if engine == "none":
        return True, ["engine=none: OCR not run"]
    if engine == "paddleocr":
        try:
            import paddleocr  # noqa: F401
            return True, ["paddleocr: found"]
        except ImportError:
            return False, [MISSING_PADDLEOCR]

    messages = []
    ok = True
    if shutil.which("tesseract"):
        messages.append("tesseract binary: found")
    else:
        messages.append(MISSING_TESSERACT)
        ok = False
    try:
        import pytesseract  # noqa: F401
        messages.append("pytesseract: found")
    except ImportError:
        messages.append(MISSING_PYTESSERACT)
        ok = False
    return ok, messages


def ollama_url(base_url: str, path: str) -> str:
    return base_url.rstrip("/") + path


def http_json(method: str, url: str, payload: dict[str, object] | None = None, timeout: int = 30) -> dict[str, object]:
    data = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = request.Request(url, data=data, headers=headers, method=method)
    try:
        with request.urlopen(req, timeout=timeout) as response:
            body = response.read().decode("utf-8")
    except (OSError, error.URLError, error.HTTPError) as exc:
        raise RuntimeError(f"Ollama request failed: {url}: {exc}") from exc
    return json.loads(body) if body else {}


def ollama_models(tags: dict[str, object]) -> list[str]:
    models = tags.get("models", [])
    names = []
    if isinstance(models, list):
        for model in models:
            if not isinstance(model, dict):
                continue
            name = model.get("name") or model.get("model")
            if isinstance(name, str):
                names.append(name)
    return names


def is_likely_vision_model(name: str) -> bool:
    lowered = name.lower()
    return any(hint in lowered for hint in VISION_MODEL_HINTS)


def choose_ollama_model(models: list[str], requested_model: str | None) -> tuple[str | None, bool]:
    if requested_model:
        return requested_model, requested_model in models
    for model in models:
        if is_likely_vision_model(model):
            return model, True
    return None, False


def ollama_preflight(base_url: str, requested_model: str | None, pull_model: bool) -> tuple[str, list[str], list[str], bool]:
    messages = []
    version = http_json("GET", ollama_url(base_url, "/api/version"))
    tags = http_json("GET", ollama_url(base_url, "/api/tags"))
    models = ollama_models(tags)
    model, already_present = choose_ollama_model(models, requested_model)
    messages.append(f"Ollama URL: {base_url}")
    messages.append(f"Ollama version: {version.get('version', 'unknown')}")
    messages.append(f"available models: {', '.join(models) if models else 'none'}")
    if not model:
        raise RuntimeError(
            f"No Ollama vision model found on {base_url}.\n"
            "Run with --model <name> --pull-model.\n"
            "Suggested first tries: minicpm-v, llava, llama3.2-vision."
        )
    messages.append(f"selected model: {model}")
    messages.append(f"model already installed: {'yes' if already_present else 'no'}")
    pulled = False
    if not already_present:
        if not pull_model:
            raise RuntimeError(f"Selected Ollama model is not installed: {model}. Re-run with --pull-model to install it on {base_url}.")
        http_json("POST", ollama_url(base_url, "/api/pull"), {"name": model, "stream": False}, timeout=600)
        pulled = True
        messages.append("model pulled: yes")
    else:
        messages.append("model pulled: no")
    return model, messages, models, pulled


def write_ocr_result(root: Path, prefix: str, index: int, sample: Path, text: str) -> None:
    target = benchmark_dir(root) / f"{prefix}_result_{index:03d}.md"
    target.write_text(f"# {prefix.upper()} Result {index:03d}\n\nSource: `{sample.relative_to(root).as_posix()}`\n\n```text\n{text}\n```\n", encoding="utf-8")


def run_ollama_vision(samples: list[Path], root: Path, base_url: str, model: str) -> list[int]:
    lengths = []
    for index, sample in enumerate(samples, start=1):
        image = base64.b64encode(sample.read_bytes()).decode("ascii")
        payload = {
            "model": model,
            "prompt": OLLAMA_PROMPT,
            "images": [image],
            "stream": False,
        }
        response = http_json("POST", ollama_url(base_url, "/api/generate"), payload, timeout=600)
        text = str(response.get("response", "")).strip()
        lengths.append(len(text))
        write_ocr_result(root, "ollama_vision", index, sample, text)
    return lengths


def run_tesseract(samples: list[Path], root: Path) -> list[int]:
    from PIL import Image
    import pytesseract

    lengths = []
    out_dir = benchmark_dir(root)
    for index, sample in enumerate(samples, start=1):
        with Image.open(sample) as image:
            text = pytesseract.image_to_string(image, lang="rus+eng")
        lengths.append(len(text.strip()))
        write_ocr_result(root, "ocr", index, sample, text)
    return lengths


def extract_paddle_text(result: object) -> str:
    texts: list[str] = []
    for item in result or []:
        data = getattr(item, "json", None)
        if callable(data):
            data = data()
        if isinstance(data, dict):
            json_data = data.get("res", data)
            rec_texts = json_data.get("rec_texts")
            if isinstance(rec_texts, list):
                texts.extend(str(text) for text in rec_texts)
    return "\n".join(texts)


def run_paddleocr(samples: list[Path], root: Path) -> list[int]:
    from paddleocr import PaddleOCR

    try:
        ocr = PaddleOCR(
            lang="ru",
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False,
        )
    except Exception as exc:
        print(f"PaddleOCR initialization failed: {exc}")
        raise SystemExit(1)

    lengths = []
    for index, sample in enumerate(samples, start=1):
        try:
            result = ocr.predict(str(sample))
            text = extract_paddle_text(result)
        except Exception as exc:
            print(f"PaddleOCR failed for {sample.name}: {exc}")
            raise SystemExit(1)
        lengths.append(len(text.strip()))
        write_ocr_result(root, "paddleocr", index, sample, text)
    return lengths


def preview(text: str, limit: int = 300) -> str:
    compact = " ".join(text.split())
    return compact[:limit] if compact else ""


def existing_result_previews(root: Path, samples: list[Path]) -> list[str]:
    lines = []
    out_dir = benchmark_dir(root)
    for prefix in ("ocr", "paddleocr", "ollama_vision"):
        for index, sample in enumerate(samples, start=1):
            path = out_dir / f"{prefix}_result_{index:03d}.md"
            if not path.exists():
                continue
            content = path.read_text(encoding="utf-8")
            text = content.split("```text", 1)[-1].rsplit("```", 1)[0].strip()
            engine = {"ocr": "tesseract", "paddleocr": "paddleocr", "ollama_vision": "ollama-vision"}[prefix]
            lines.append(f"- {sample.relative_to(root).as_posix()} | {engine} | {len(text)} | {preview(text)}")
    return lines or ["- none"]


def write_summary(
    root: Path,
    samples: list[Path],
    engine: str,
    dependency_messages: list[str],
    lengths: list[int],
    metadata: list[str] | None = None,
) -> None:
    length_lines = []
    for index, sample in enumerate(samples, start=1):
        length = lengths[index - 1] if index <= len(lengths) else 0
        length_lines.append(f"- {sample.relative_to(root).as_posix()}: {length}")
    if not length_lines:
        length_lines.append("- none: 0")
    recommendation = {
        "ollama-vision": "- use Ollama Vision for a controlled batch OCR\n- validate OCR text stubs manually\n- adjust preprocessing settings if recurring artifacts appear",
        "paddleocr": "- use PaddleOCR\n- try PaddleOCR-VL\n- manual OCR\n- change preprocessing settings",
    }.get(engine, "- use PaddleOCR\n- try PaddleOCR-VL\n- manual OCR\n- change preprocessing settings")

    content = f"""# OCR Sample Benchmark Summary

## Selected Files

{relative_list(root, samples)}

## OCR Engine

{engine}

## Dependency Status

{chr(10).join(f"- {message}" for message in dependency_messages)}

## Engine Metadata

{chr(10).join(f"- {item}" for item in (metadata or ['none']))}

## Recognized Text Length

{chr(10).join(length_lines)}

## Existing Result Comparison

Format: selected file | engine | text length | first 300 chars preview

{chr(10).join(existing_result_previews(root, samples))}

Comparison note: compare the previews above against Tesseract, PaddleOCR, and Ollama Vision before choosing a full-document OCR path.

## Manual Quality Checklist

- русский текст читается?
- заголовки сохранились?
- списки сохранились?
- таблицы/формулы сломались?
- можно ли использовать для билетов?

## Recommendation

{recommendation}
"""
    (benchmark_dir(root) / "ocr_benchmark_summary.md").write_text(content, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default="exam_materials")
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--engine", choices=sorted(SUPPORTED_ENGINES), default="none")
    parser.add_argument("--ollama-url", default="http://127.0.0.1:11434")
    parser.add_argument("--model")
    parser.add_argument("--pull-model", action="store_true")
    args = parser.parse_args()

    root = Path(args.root)
    out_dir = benchmark_dir(root)
    out_dir.mkdir(parents=True, exist_ok=True)
    samples = select_samples(root, max(args.limit, 0))
    write_selection(root, samples)

    ollama_model = None
    metadata: list[str] = []
    if args.engine == "ollama-vision":
        try:
            ollama_model, messages, models, pulled = ollama_preflight(args.ollama_url, args.model, args.pull_model)
            metadata = [
                f"Ollama URL: {args.ollama_url}",
                f"model used: {ollama_model}",
                f"model already present or pulled: {'pulled' if pulled else 'already present'}",
                f"available Ollama models: {', '.join(models) if models else 'none'}",
            ]
            ok = True
        except RuntimeError as exc:
            messages = [str(exc)]
            ok = False
    else:
        ok, messages = dependency_status(args.engine)
    if not ok:
        write_summary(root, samples, args.engine, messages, [], metadata)
        for message in messages:
            print(message)
        print(f"report written: {out_dir / 'ocr_benchmark_summary.md'}")
        raise SystemExit(1)

    if args.engine == "tesseract":
        lengths = run_tesseract(samples, root)
    elif args.engine == "paddleocr":
        lengths = run_paddleocr(samples, root)
    elif args.engine == "ollama-vision":
        if not ollama_model:
            print("No Ollama model selected.")
            raise SystemExit(1)
        lengths = run_ollama_vision(samples, root, args.ollama_url, ollama_model)
    else:
        lengths = [0 for _ in samples]
    write_summary(root, samples, args.engine, messages, lengths, metadata)
    print(f"selected files: {len(samples)}")
    print(f"OCR engine: {args.engine}")
    print(f"report written: {out_dir / 'ocr_benchmark_summary.md'}")


if __name__ == "__main__":
    main()
