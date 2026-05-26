# Project Specification: Preparing to Exam

Status: draft for phased Codex implementation  
Repository: `sergstack/preparing-to-exam`  
Primary workflow: scanned notes/documents → OCR or manual text → structured tickets → final study materials  
Current release baseline: GitHub Foundation v1 / PR #1

---

## 1. Purpose

`preparing-to-exam` is a small local-first toolset for preparing exam study materials from scanned notes, photographed pages, PDFs, and manually extracted text.

The project must help the user quickly move from raw source material to a clean set of study tickets without building a large AI platform.

Target outcome:

```text
raw scans / PDFs
→ OCR or manual text
→ ticket drafts
→ checked final materials
→ progress tracking
```

The project is intentionally not a RAG system, not a vector database, not an agent platform, and not a web application.

---

## 2. Design Principles

1. **Speed before architecture**  
   First useful result is more important than a perfect knowledge system.

2. **Local-first**  
   The tool must work with local files and must not require external APIs.

3. **No private materials in git**  
   Real scans, OCR text, generated tickets, and final study materials are user data and must stay ignored by git.

4. **Idempotent CLI commands**  
   Re-running scripts must be safe.

5. **No overwrite by default**  
   User-edited files must not be overwritten unless `--force` is explicitly passed.

6. **Small quality gate**  
   A final ticket is allowed only if required sections exist.

7. **No premature AI infrastructure**  
   No RAG, vector DB, embeddings, web UI, autonomous agents, or background workflow orchestration before explicit approval.

---

## 3. Current Baseline

Foundation v1 should provide:

```text
.
├── README.md
├── AGENTS.md
├── CONTRIBUTING.md
├── CHANGELOG.md
├── .gitignore
├── pyproject.toml
├── requirements.txt
├── scripts/
├── tests/
├── docs/WORKFLOW.md
├── .github/
└── exam_materials/.gitkeep
```

Expected working project folder after initialization:

```text
exam_materials/
├── 00_scans/
├── 01_text/
├── 02_tickets/
├── 03_final/
├── progress.xlsx
└── README.md
```

Baseline CLI:

```bash
python scripts/init_exam_materials.py --root exam_materials
python scripts/register_scans.py --root exam_materials
python scripts/create_text_stubs.py --root exam_materials
python scripts/create_ticket_templates.py --root exam_materials
python scripts/promote_ticket.py --root exam_materials --ticket 01
```

---

## 4. User Scenario

The user has scanned or photographed educational materials. Some files may be image-only PDFs where text cannot be parsed directly.

Example source profile:

```text
- file type: PDF or image
- content: scanned document pages
- parseable text layer: may be absent
- expected processing: image/PDF page extraction → OCR/manual text → structured ticket
```

Important: sample documents may contain personal or sensitive data. They must be used only as local test inputs and must never be committed to the repository.

---

## 5. Non-Goals

Do not implement in the current project scope:

```text
- RAG
- vector DB
- embeddings
- web UI
- autonomous agents
- external API integrations
- mandatory OCR engine dependency
- mandatory LLM integration
- private document storage in git
- complex source cards
- confidence labels
- full spaced repetition system
- advanced exam trainer
- production orchestration
```

These can be future backlog items only after the core workflow is stable.

---

## 6. Core Data Flow

```text
00_scans
   ↓ register
progress.xlsx
   ↓ create stubs
01_text
   ↓ create templates
02_tickets
   ↓ promote after section check
03_final
```

### Stage meanings

| Stage | Folder | Meaning |
|---|---|---|
| Raw inputs | `00_scans/` | User files: scans, photos, PDFs |
| Text layer | `01_text/` | OCR text or manually pasted text |
| Draft tickets | `02_tickets/` | Structured ticket drafts |
| Final materials | `03_final/` | Materials ready for studying |
| Tracking | `progress.xlsx` | Status and notes |

---

## 7. File Naming Convention

Preferred input file names:

```text
ticket_01_page_01.jpg
ticket_01_page_02.png
ticket_02_page_01.pdf
```

Supported input extensions:

```text
.jpg
.jpeg
.png
.pdf
```

Unknown names are allowed, but must be registered with a check note:

```text
filename_check
```

The system must not fail because of unknown names.

---

## 8. Progress Workbook Contract

File:

```text
exam_materials/progress.xlsx
```

Required columns:

| Column | Required | Description |
|---|---:|---|
| `ticket_id` | yes | Ticket identifier, e.g. `01` |
| `scan_files` | yes | Related raw files |
| `ocr_status` | yes | `no`, `weak`, `done` |
| `ticket_status` | yes | `no`, `draft`, `done` |
| `check_notes` | yes | Manual checks, missing sections, filename issues |
| `final_status` | yes | `raw`, `ocr`, `draft`, `fix`, `ready` |
| `updated_at` | yes | ISO timestamp |

Allowed `final_status` values:

```text
raw
ocr
draft
fix
ready
```

Status rules:

| Condition | Status |
|---|---|
| Scan exists, no text | `raw` |
| Text exists, no ticket | `ocr` |
| Ticket draft exists | `draft` |
| Required checks missing | `fix` |
| Ticket copied to final | `ready` |

---

## 9. Ticket Template Contract

Ticket path:

```text
exam_materials/02_tickets/ticket_01.md
```

Required sections:

```markdown
# Билет 01. Название

## Кратко

## План ответа
1.
2.
3.

## Ответ на 5 минут

## Что выучить точно

## Вопросы для самопроверки
1.
2.
3.

## Проверить по скану
-
```

Promotion to `03_final/` must be blocked if any required section header is missing.

---

## 10. Development Roadmap

### Phase 0 — Foundation v1

Status: implemented in PR #1.

Goal:

```text
Initialize repository as a safe Python CLI project.
```

Scope:

- documentation;
- `.gitignore`;
- Python scripts;
- tests;
- GitHub Actions CI;
- minimal local workflow.

Acceptance:

- tests pass;
- smoke workflow passes;
- real user files are ignored;
- no OCR/LLM/RAG implemented.

---

### Phase 1 — Intake Hardening

Goal:

```text
Make file intake safer and clearer for real scanned materials.
```

Tasks:

1. Improve `register_scans.py` output summary.
2. Add duplicate file detection by name.
3. Add support for multi-page ticket grouping.
4. Add clear warning for unknown filenames.
5. Add `--dry-run` mode for registration.

Allowed files:

```text
scripts/register_scans.py
scripts/exam_materials_lib.py
tests/test_register_scans.py
docs/WORKFLOW.md
README.md
```

Acceptance:

- `--dry-run` does not modify `progress.xlsx`;
- known filename pattern grouped by ticket;
- unknown files registered safely or reported in dry run;
- tests added/updated.

Smoke command:

```bash
python scripts/register_scans.py --root /tmp/exam_materials_smoke --dry-run
python -m pytest -q
```

---

### Phase 2 — PDF/Image Preprocessing Stub

Goal:

```text
Prepare safe local copies for OCR without changing raw files.
```

Tasks:

1. Add optional `scripts/preprocess_scans.py`.
2. Create outputs under `00_scans/_preprocessed/`.
3. Never overwrite raw inputs.
4. Support image files first.
5. For PDFs, create a clear placeholder behavior if PDF rendering dependency is absent.
6. Add graceful failure when optional dependencies are missing.

Allowed operations:

```text
- copy to preprocessed folder
- normalize file extension if needed
- optional grayscale if Pillow is available
- optional contrast enhancement if Pillow is available
```

Forbidden:

```text
- no destructive edits
- no mandatory heavy OCR dependencies
- no online services
```

Acceptance:

- raw scans unchanged;
- preprocessed copies created when dependencies are available;
- script exits clearly when dependencies are missing;
- tests cover no-overwrite behavior.

---

### Phase 3 — OCR Integration Decision Gate

Goal:

```text
Choose whether OCR remains manual or gets an optional local engine integration.
```

This is an inspect-only/design phase first.

Codex must not implement OCR before returning a decision memo.

Decision memo should compare:

| Option | Use case | Risk |
|---|---|---|
| Manual OCR paste | Few documents | Slow but safe |
| Tesseract optional | Printed text | Weak for handwriting |
| PaddleOCR optional | Mixed scans | Adds dependency |
| External OCR | Better quality | Not allowed without privacy decision |
| Vision LLM | Hard scans | Separate LLM project decision |

Output:

```text
docs/OCR_DECISION.md
```

Acceptance:

- no new OCR dependency added;
- privacy risks listed;
- recommendation for next implementation phase included.

---

### Phase 4 — Text Stub Quality Improvements

Goal:

```text
Make OCR/manual text files easier to fill and validate.
```

Tasks:

1. Add source file list to every stub.
2. Add `## OCR text` and `## Manual checks` sections.
3. Add a simple validator for text stubs.
4. Detect empty OCR text block.
5. Update progress status to `ocr` only when text block has real content.

Possible script:

```text
scripts/validate_text_stubs.py
```

Acceptance:

- empty stub does not falsely mark OCR as done;
- non-empty OCR block marks `ocr_status = done`;
- tests cover empty/non-empty behavior.

---

### Phase 5 — Ticket Draft Validation

Goal:

```text
Make ticket drafts safer before promotion.
```

Tasks:

1. Add content checks beyond section headers.
2. Required sections must not be completely empty.
3. `## Проверить по скану` may remain non-empty and still allow `fix` status.
4. Add `scripts/validate_tickets.py`.
5. Produce a concise validation report.

Validation report example:

```text
ticket_01.md: ready
ticket_02.md: fix — empty required section: Ответ на 5 минут
ticket_03.md: fix — unresolved scan checks
```

Acceptance:

- missing headers are detected;
- empty required sections are detected;
- `progress.xlsx` updated consistently;
- tests added.

---

### Phase 6 — Batch Workflow Command

Goal:

```text
Provide one safe command to run all deterministic steps.
```

Possible script:

```text
scripts/run_pipeline.py
```

Command:

```bash
python scripts/run_pipeline.py --root exam_materials
```

Must run:

```text
init → register scans → create text stubs → create ticket templates → validate
```

Do not auto-promote by default.

Optional flag:

```bash
python scripts/run_pipeline.py --root exam_materials --promote-ready
```

Acceptance:

- pipeline is idempotent;
- user content not overwritten;
- validation summary printed;
- tests cover basic batch run.

---

### Phase 7 — LLM Prompt Pack, Not LLM Automation

Goal:

```text
Add ready-to-copy prompts for manual LLM use without integrating API calls.
```

Create:

```text
docs/PROMPTS.md
```

Prompts:

1. OCR cleanup prompt.
2. Ticket creation prompt.
3. Self-check questions prompt.
4. Final review prompt.

Forbidden:

```text
- no API calls
- no model routing implementation
- no Ollama integration
- no generated output committed
```

Acceptance:

- prompts are clear and operational;
- README links to prompt pack;
- no code changes required unless link added.

---

### Phase 8 — Release v1.0

Goal:

```text
Mark the deterministic local workflow as usable.
```

Release checklist:

- all tests pass;
- smoke workflow passes;
- README is current;
- no user data committed;
- generated artifacts ignored;
- limitations listed;
- rollback path clear.

Release candidate commands:

```bash
python -m pytest -q
python scripts/init_exam_materials.py --root /tmp/exam_materials_release
mkdir -p /tmp/exam_materials_release/00_scans
touch /tmp/exam_materials_release/00_scans/ticket_01_page_01.jpg
python scripts/register_scans.py --root /tmp/exam_materials_release
python scripts/create_text_stubs.py --root /tmp/exam_materials_release
python scripts/create_ticket_templates.py --root /tmp/exam_materials_release
python scripts/promote_ticket.py --root /tmp/exam_materials_release --ticket 01
```

---

## 11. Codex Task Package Template for Future Phases

Every implementation task must include:

```markdown
# Codex Task

## Context

## Objective

## Inputs

## Files to inspect

## Files allowed to modify

## Forbidden actions

## Expected outputs

## Acceptance criteria

## Tests / smoke checks

## Rollback plan

## Final response format
```

Codex must stop with a blocker if objective, allowed files, acceptance criteria, or test/smoke check are missing.

---

## 12. Testing Strategy

Use the smallest useful test for each phase.

Test types:

| Area | Test type |
|---|---|
| CLI initialization | unit / smoke |
| Progress workbook | contract |
| Scan registration | unit |
| Stub creation | unit |
| Ticket promotion | unit / contract |
| End-to-end local flow | smoke |
| Git ignore safety | file check |

Default command:

```bash
python -m pytest -q
```

Smoke workflow must use `/tmp` or a temporary directory and must not depend on private user data.

---

## 13. Security and Privacy Rules

Never commit:

```text
- real scans
- real OCR text
- generated tickets from private materials
- final study materials from private materials
- passports, contracts, phone numbers, addresses, signatures
- `.env`
- API keys
- credentials
- logs containing private paths or data
```

The `.gitignore` must keep generated and user-specific materials out of git.

If a task requires using a real sample file, Codex must use it locally only and report that it was not committed.

---

## 14. Done Definition

A phase is done when:

```text
- objective is complete;
- changes are scoped;
- tests/checks are run;
- acceptance criteria are evaluated;
- risks are listed;
- rollback or next step is clear;
- final report is concise and usable.
```

Final Codex response format:

```text
Summary:
Files changed:
Tests/checks run:
Assumptions:
Risks/limitations:
Acceptance status:
Next step:
```

---

## 15. Recommended Next Codex Task

Recommended next phase after Foundation v1 merge:

```text
Phase 1 — Intake Hardening
```

Reason:

```text
The next bottleneck is reliable registration and tracking of real scan/PDF inputs before any OCR or LLM work begins.
```

Do not start OCR integration before intake and progress tracking are stable.
