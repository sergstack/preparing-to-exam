# Preparing to Exam

Minimal local workflow for preparing exam study materials from scanned notes.

The project keeps the process small:

```text
scans -> OCR/manual text -> ticket drafts -> final study materials -> progress tracking
```

It intentionally does not include RAG, vector databases, embeddings, a web UI,
autonomous agents, external API calls, or mandatory OCR dependencies.

Manual copy-ready prompts are available in [docs/PROMPTS.md](docs/PROMPTS.md).

## Quick Start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

python scripts/init_exam_materials.py --root exam_materials
python scripts/register_scans.py --root exam_materials
python scripts/create_text_stubs.py --root exam_materials
python scripts/create_ticket_templates.py --root exam_materials
python scripts/promote_ticket.py --root exam_materials --ticket 01
```

## Folder Structure

```text
exam_materials/
├── 00_scans/      # user scans, ignored by git
├── 01_text/       # OCR/manual raw text, ignored by git
├── 02_tickets/    # draft tickets, ignored by git
├── 03_final/      # final materials, ignored by git
└── progress.xlsx  # generated tracking workbook, ignored by git
```

Only `exam_materials/.gitkeep` is committed. User materials stay local.

## Commands

Initialize folders and the progress workbook:

```bash
python scripts/init_exam_materials.py --root exam_materials
```

Register scan files from `00_scans/`:

```bash
python scripts/register_scans.py --root exam_materials
```

Preview scan registration without modifying `progress.xlsx`:

```bash
python scripts/register_scans.py --root exam_materials --dry-run
```

Create raw text stubs:

```bash
python scripts/create_text_stubs.py --root exam_materials
```

Validate OCR/manual text stubs:

```bash
python scripts/validate_text_stubs.py --root exam_materials
```

Create ticket draft templates:

```bash
python scripts/create_ticket_templates.py --root exam_materials
```

Validate ticket drafts before promotion:

```bash
python scripts/validate_tickets.py --root exam_materials
```

Promote a complete ticket draft to final materials:

```bash
python scripts/promote_ticket.py --root exam_materials --ticket 01
```

Run the safe local pipeline without auto-promotion:

```bash
python scripts/run_pipeline.py --root exam_materials
```

Preview the batch pipeline without modifying local materials:

```bash
python scripts/run_pipeline.py --root exam_materials --dry-run
```

Run the local OCR preprocessing gate:

```bash
python scripts/ocr_benchmark_gate.py --root exam_materials
python scripts/extract_pdf_pages.py --root exam_materials --dry-run
python scripts/preprocess_scans.py --root exam_materials --dry-run
```

`extract_pdf_pages.py` uses optional `pymupdf` only when rendering PDF pages.
`preprocess_scans.py` uses optional `Pillow` for image copies. Raw files are not
modified.

Run a small OCR sample benchmark before processing a full document:

```bash
python3 scripts/ocr_sample_benchmark.py --root exam_materials --limit 5 --engine none
python3 scripts/ocr_sample_benchmark.py --root exam_materials --limit 5 --engine tesseract
python3 scripts/ocr_sample_benchmark.py --root exam_materials --limit 5 --engine paddleocr
python3 scripts/ocr_sample_benchmark.py --root exam_materials --limit 5 --engine ollama-vision --ollama-url http://127.0.0.1:11434 --model minicpm-v
```

Benchmark outputs are local artifacts under `exam_materials/04_ocr_benchmark/`
and are ignored by git.
PaddleOCR is optional; install it only when needed with
`python3 -m pip install paddleocr`.
Ollama vision OCR is optional and uses the configured Ollama HTTP API; model
pulls use `/api/pull` on that same server when `--pull-model` is passed.

Run a controlled Ollama Vision batch OCR only after the sample quality is good:

```bash
python3 scripts/ollama_vision_batch_ocr.py --root exam_materials --ollama-url http://127.0.0.1:11434 --model qwen2.5vl:7b --limit 10
```

Batch OCR writes ignored local artifacts under `exam_materials/05_ocr_pages/`.
It does not process every page unless `--all` is explicitly passed.
OCR output is near-verbatim transcription with light cleanup only: keep the
author's wording, mark uncertain words as `[проверить: ...]`, and mark unreadable
fragments as `[неразборчиво]`. Do not turn OCR text into tickets at this stage.

Compare Ollama vision models on a fixed small page set before changing the batch
OCR model:

```bash
python3 scripts/ollama_vision_model_compare.py --root exam_materials --ollama-url http://127.0.0.1:11434 --models qwen2.5vl:7b,qwen2.5vl:32b --pages 2,4,5,6,10 --pull-missing
```

Model comparison writes ignored local artifacts under
`exam_materials/06_model_compare/`. Missing models are pulled through the
configured remote Ollama HTTP API only when `--pull-missing` is passed.

Recover only failed or weak OCR pages with a stronger model:

```bash
python3 scripts/ollama_vision_recovery.py --root exam_materials --ollama-url http://127.0.0.1:11434 --primary-model qwen2.5vl:7b --recovery-model qwen2.5vl:32b --dry-run
python3 scripts/ollama_vision_recovery.py --root exam_materials --ollama-url http://127.0.0.1:11434 --primary-model qwen2.5vl:7b --recovery-model qwen2.5vl:32b --pages 2,6 --force
```

Recovery outputs go to `exam_materials/07_ocr_recovery/`, which is ignored by
git. The recovery model is for failed/problem pages only; it does not replace
the primary batch OCR model.

Merge primary and recovery OCR into a single review pack before creating checked
text stubs:

```bash
python3 scripts/ocr_merge_review_pack.py --root exam_materials --strip-service-headings --force
```

Merged OCR outputs go to `exam_materials/08_ocr_merged/`, which is ignored by
git. This step only selects and packages OCR text for manual review; it does not
summarize text or generate tickets.

Run an end-to-end OCR review-pack pass for a controlled page range:

```bash
python3 scripts/ocr_end_to_end_review_pack.py --root exam_materials --ollama-url http://127.0.0.1:11434 --primary-model qwen2.5vl:7b --recovery-model qwen2.5vl:32b --start 21 --end 90 --chunk-size 10 --force
```

The end-to-end step runs primary OCR in chunks, retries problem pages with the
recovery model, rebuilds the merged review pack, and writes ignored review
reports under `exam_materials/09_review_reports/`. It does not generate tickets.

Create a checked text layer from the merged OCR review pack:

```bash
python3 scripts/create_checked_text_stubs.py --root exam_materials
python3 scripts/validate_checked_text.py --root exam_materials
python3 scripts/build_checked_text_full.py --root exam_materials
```

Checked text outputs go to `exam_materials/10_checked_text/`, which is ignored
by git. This layer is for manual near-verbatim correction and validation before
any ticket generation.

## Filename Convention

Use this scan filename pattern:

```text
ticket_01_page_01.jpg
ticket_01_page_02.jpg
```

Supported scan file types:

```text
.jpg .jpeg .png .pdf
```

Unknown filenames are recorded with `filename_check` in `check_notes`; they do
not stop the workflow.

## Progress Statuses

`progress.xlsx` contains:

```text
ticket_id
scan_files
ocr_status
ticket_status
check_notes
final_status
updated_at
```

Allowed `final_status` values:

```text
raw
ocr
draft
fix
ready
```

## Safe Workflow

1. Put scans into `exam_materials/00_scans/`.
2. Run scan registration.
3. Create raw text stubs and paste OCR/manual text into them.
4. Validate text stubs before treating OCR/manual text as complete.
5. Create ticket templates.
6. Edit and validate drafts in `02_tickets/`.
7. Promote structurally complete drafts into `03_final/`.

Use `--force` only when you intentionally want generated templates to be
recreated.
