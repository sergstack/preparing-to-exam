# Ollama QA

Optional local quality review for checked text or ticket drafts.

## Commands

Preview selected files without calling Ollama:

```bash
python3 scripts/ollama_quality_gate.py --input exam_materials/10_checked_text --sample 5 --dry-run
```

Write an advisory review report:

```bash
python3 scripts/ollama_quality_gate.py \
  --input exam_materials/02_tickets \
  --sample 5 \
  --model qwen2.5:7b \
  --timeout 60 \
  --output exam_materials/09_review_reports/ollama_quality_review.md
```

## Safety Rules

- Uses only `http://127.0.0.1:*` or `http://localhost:*` Ollama URLs.
- Reviews only a bounded markdown sample.
- Sends file names, not absolute local paths, in prompts.
- Writes a markdown report only.
- Never edits checked text, ticket drafts, final materials, or `progress.xlsx`.
- Exits gracefully if Ollama is unavailable or model output is invalid.

## Review Dimensions

- OCR/text completeness.
- Unreadable fragments.
- Formatting issues.
- Ticket structure.
- Missing question or answer sections.
- Duplicated fragments.
- Suspiciously short output.
- Russian readability.
- Exam-readiness.

The report is advisory. Human review remains required for any `warn` or `fail`
item.
