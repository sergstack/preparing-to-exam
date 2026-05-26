from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from exam_materials_lib import iter_preprocessed_images


SUPPORTED_ENGINES = {"none", "paddleocr", "tesseract"}
MISSING_TESSERACT = "Missing OCR engine: tesseract. Install it locally before using --engine tesseract."
MISSING_PYTESSERACT = "Missing optional dependency: pytesseract. Install with: python3 -m pip install pytesseract"
MISSING_PADDLEOCR = "Missing optional OCR dependency: paddleocr.\nInstall with:\npython3 -m pip install paddleocr"


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


def write_ocr_result(root: Path, prefix: str, index: int, sample: Path, text: str) -> None:
    target = benchmark_dir(root) / f"{prefix}_result_{index:03d}.md"
    target.write_text(f"# {prefix.upper()} Result {index:03d}\n\nSource: `{sample.relative_to(root).as_posix()}`\n\n```text\n{text}\n```\n", encoding="utf-8")


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
    for prefix in ("ocr", "paddleocr"):
        for index, sample in enumerate(samples, start=1):
            path = out_dir / f"{prefix}_result_{index:03d}.md"
            if not path.exists():
                continue
            content = path.read_text(encoding="utf-8")
            text = content.split("```text", 1)[-1].rsplit("```", 1)[0].strip()
            engine = "tesseract" if prefix == "ocr" else "paddleocr"
            lines.append(f"- {sample.relative_to(root).as_posix()} | {engine} | {len(text)} | {preview(text)}")
    return lines or ["- none"]


def write_summary(root: Path, samples: list[Path], engine: str, dependency_messages: list[str], lengths: list[int]) -> None:
    length_lines = []
    for index, sample in enumerate(samples, start=1):
        length = lengths[index - 1] if index <= len(lengths) else 0
        length_lines.append(f"- {sample.relative_to(root).as_posix()}: {length}")
    if not length_lines:
        length_lines.append("- none: 0")

    content = f"""# OCR Sample Benchmark Summary

## Selected Files

{relative_list(root, samples)}

## OCR Engine

{engine}

## Dependency Status

{chr(10).join(f"- {message}" for message in dependency_messages)}

## Recognized Text Length

{chr(10).join(length_lines)}

## Existing Result Comparison

Format: selected file | engine | text length | first 300 chars preview

{chr(10).join(existing_result_previews(root, samples))}

## Manual Quality Checklist

- русский текст читается?
- заголовки сохранились?
- списки сохранились?
- таблицы/формулы сломались?
- можно ли использовать для билетов?

## Recommendation

- use PaddleOCR
- try PaddleOCR-VL
- manual OCR
- change preprocessing settings
"""
    (benchmark_dir(root) / "ocr_benchmark_summary.md").write_text(content, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default="exam_materials")
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--engine", choices=sorted(SUPPORTED_ENGINES), default="none")
    args = parser.parse_args()

    root = Path(args.root)
    out_dir = benchmark_dir(root)
    out_dir.mkdir(parents=True, exist_ok=True)
    samples = select_samples(root, max(args.limit, 0))
    write_selection(root, samples)

    ok, messages = dependency_status(args.engine)
    if not ok:
        write_summary(root, samples, args.engine, messages, [])
        for message in messages:
            print(message)
        print(f"report written: {out_dir / 'ocr_benchmark_summary.md'}")
        raise SystemExit(1)

    if args.engine == "tesseract":
        lengths = run_tesseract(samples, root)
    elif args.engine == "paddleocr":
        lengths = run_paddleocr(samples, root)
    else:
        lengths = [0 for _ in samples]
    write_summary(root, samples, args.engine, messages, lengths)
    print(f"selected files: {len(samples)}")
    print(f"OCR engine: {args.engine}")
    print(f"report written: {out_dir / 'ocr_benchmark_summary.md'}")


if __name__ == "__main__":
    main()
