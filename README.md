# Preparing to Exam

Minimal local workflow for preparing exam study materials from scanned notes.

The project keeps the process small:

```text
scans -> OCR/manual text -> ticket drafts -> final study materials -> progress tracking
```

It intentionally does not include RAG, vector databases, embeddings, a web UI,
autonomous agents, external API calls, or mandatory OCR dependencies.

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

Create ticket draft templates:

```bash
python scripts/create_ticket_templates.py --root exam_materials
```

Promote a complete ticket draft to final materials:

```bash
python scripts/promote_ticket.py --root exam_materials --ticket 01
```

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
4. Create ticket templates.
5. Edit drafts in `02_tickets/`.
6. Promote structurally complete drafts into `03_final/`.

Use `--force` only when you intentionally want generated templates to be
recreated.
