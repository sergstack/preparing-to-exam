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
