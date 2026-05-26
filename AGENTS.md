# AGENTS.md

## Scope

Project-level instructions for this repository.

## Working Rules

- Inspect relevant files before editing.
- Keep changes minimal and tied to the user request.
- Do not add secrets, `.env` files, credentials, tokens, or private study data.
- Do not commit real scans, OCR text, ticket drafts, final materials, or
  `progress.xlsx`.
- Do not add RAG, vector databases, embeddings, web UI, autonomous agents,
  external API calls, or mandatory OCR engine dependencies.
- Prefer small Python scripts and tests over broad architecture.
- Use `pathlib` for filesystem paths.
- Run the smallest relevant tests before reporting completion.
- Report changed files, commands run, test results, blockers, and risks
  honestly.

## Generated Materials

The following paths are user/generated materials and must stay out of git:

```text
exam_materials/00_scans/
exam_materials/01_text/
exam_materials/02_tickets/
exam_materials/03_final/
exam_materials/progress.xlsx
```
