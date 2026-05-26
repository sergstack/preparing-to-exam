# Workflow

This repository supports a simple local study-material preparation flow:

```text
00_scans -> 01_text -> 02_tickets -> 03_final -> progress.xlsx
```

## 1. Scans

Place source files in:

```text
exam_materials/00_scans/
```

Use names like:

```text
ticket_01_page_01.jpg
ticket_01_page_02.jpg
```

Preview registration before updating `progress.xlsx`:

```bash
python scripts/register_scans.py --root exam_materials --dry-run
```

## 2. OCR or Manual Text

For PDFs and image scans, run the local preprocessing gate before OCR:

```bash
python scripts/ocr_benchmark_gate.py --root exam_materials
python scripts/extract_pdf_pages.py --root exam_materials --dry-run
python scripts/preprocess_scans.py --root exam_materials --dry-run
```

PDF pages and OCR-ready image copies are written only under
`exam_materials/00_scans/_preprocessed/`, which is ignored by git. See
[OCR_DECISION.md](OCR_DECISION.md) before adding OCR tools or model downloads.

Before running OCR on a whole document, create a small local benchmark:

```bash
python3 scripts/ocr_sample_benchmark.py --root exam_materials --limit 5 --engine none
```

If `tesseract` and `pytesseract` are installed locally, test OCR on the same
small sample:

```bash
python3 scripts/ocr_sample_benchmark.py --root exam_materials --limit 5 --engine tesseract
```

If Tesseract quality is poor, try optional PaddleOCR on the same small sample:

```bash
python3 scripts/ocr_sample_benchmark.py --root exam_materials --limit 5 --engine paddleocr
```

If local OCR quality remains poor, test an Ollama vision model through the
remote HTTP API:

```bash
python3 scripts/ocr_sample_benchmark.py --root exam_materials --limit 5 --engine ollama-vision --ollama-url http://127.0.0.1:11434 --model minicpm-v
```

To install the selected model on that Ollama server, add `--pull-model`. The
project does not use the local `ollama pull` shell command by default.

After a successful sample, run a controlled batch OCR with an explicit limit or
page range:

```bash
python3 scripts/ollama_vision_batch_ocr.py --root exam_materials --ollama-url http://127.0.0.1:11434 --model qwen2.5vl:7b --limit 10
python3 scripts/ollama_vision_batch_ocr.py --root exam_materials --ollama-url http://127.0.0.1:11434 --model qwen2.5vl:7b --start 1 --end 10
```

Batch OCR outputs go to `exam_materials/05_ocr_pages/`, which is ignored by git.
Use `--all` only when you intentionally want every preprocessed OCR image.

Run:

```bash
python scripts/create_text_stubs.py --root exam_materials
```

Then paste OCR or manually typed text into files under:

```text
exam_materials/01_text/
```

Validate stubs before creating or relying on ticket drafts:

```bash
python scripts/validate_text_stubs.py --root exam_materials
```

Empty placeholder OCR text remains `pending`; non-empty OCR text can be marked
`done` in `progress.xlsx`.

## 3. Ticket Drafts

Run:

```bash
python scripts/create_ticket_templates.py --root exam_materials
```

Edit files under:

```text
exam_materials/02_tickets/
```

Validate drafts:

```bash
python scripts/validate_tickets.py --root exam_materials
```

## 4. Final Materials

Promote a complete ticket:

```bash
python scripts/promote_ticket.py --root exam_materials --ticket 01
```

Complete tickets are copied into:

```text
exam_materials/03_final/
```

## 5. Progress Tracking

`progress.xlsx` tracks scan registration, OCR status, ticket draft status,
review notes, final status, and update time. It is generated locally and ignored
by git.

## Batch Pipeline

Run all safe local steps without auto-promotion:

```bash
python scripts/run_pipeline.py --root exam_materials
```

Preview without modifying local materials:

```bash
python scripts/run_pipeline.py --root exam_materials --dry-run
```

## Manual Prompts

Copy-ready prompts for OCR cleanup, ticket creation, self-check questions, and
final review are available in [PROMPTS.md](PROMPTS.md). They are documentation
only; there is no LLM runner or API integration.
