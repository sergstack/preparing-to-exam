# OCR Decision

OCR and LLM work are separate stages.

This project first prepares local PDFs and scans for OCR. Existing local text
LLMs, if used later, should only help after OCR: cleanup, ticket drafting, and
self-check generation. They are not part of the preprocessing gate.

## Current Approach

1. Keep raw scans and PDFs local in `exam_materials/00_scans/`.
2. Extract PDF pages only into ignored local artifacts.
3. Preprocess image copies for OCR without modifying raw files.
4. Try manual paste or simple OCR first.
5. If Tesseract produces unreadable text, benchmark optional PaddleOCR on the
   same small sample before moving to vision OCR.
6. If local OCR quality remains poor, benchmark an Ollama vision model through
   the configured Ollama HTTP API on the same small sample.
7. Download or configure a larger vision OCR model only if real scans show poor
   OCR quality.
8. Run batch OCR only after sample quality is acceptable, and keep OCR outputs
   ignored until manually validated.

## Later OCR Candidates

- PaddleOCR
- Ollama vision models such as `minicpm-v`, `llava`, or `llama3.2-vision`
- PaddleOCR-VL
- PaddleOCR-VL GGUF

## Privacy

Real scans and source materials must not be uploaded to external OCR, LLM, or
cloud services without explicit approval.
