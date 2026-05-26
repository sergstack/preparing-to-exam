# Manual Prompt Pack

Use these prompts manually in the LLM tool of your choice. This repository does
not provide API calls, model runners, Ollama integration, or automatic prompt
execution.

Do not paste private material into external tools unless you are allowed to do
so.

## OCR Cleanup Prompt

```text
You are helping clean OCR text for exam preparation.

Task:
Clean the OCR text below without adding new facts.

Rules:
- Preserve the original meaning.
- Fix obvious OCR mistakes, broken line breaks, and duplicated fragments.
- Mark unreadable or uncertain places as [проверить по скану].
- Do not invent missing content.
- Keep formulas, dates, names, and definitions as close to the source as possible.
- Return only cleaned text.

OCR text:
<<<
PASTE OCR TEXT HERE
>>>
```

## Ticket Creation Prompt

```text
You are preparing a concise exam ticket answer from verified source text.

Task:
Create a study ticket using the required structure.

Rules:
- Use only the source text below.
- Do not add facts that are not present in the source.
- If something is unclear, write [проверить по скану].
- Keep the answer suitable for oral exam preparation.
- Return Markdown only.

Required structure:
# Билет NN. Название

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

Source text:
<<<
PASTE VERIFIED TEXT HERE
>>>
```

## Self-Check Questions Prompt

```text
You are helping prepare self-check questions for an exam ticket.

Task:
Create self-check questions from the ticket draft below.

Rules:
- Use only the ticket draft.
- Cover definitions, sequence of explanation, examples, and likely examiner follow-ups.
- Do not answer the questions unless explicitly asked.
- Mark weak or unclear areas as [проверить по скану].

Ticket draft:
<<<
PASTE TICKET DRAFT HERE
>>>
```

## Final Review Prompt

```text
You are reviewing an exam ticket for clarity and completeness.

Task:
Review the ticket draft below and return a concise checklist.

Rules:
- Do not rewrite the ticket unless asked.
- Identify missing required sections.
- Identify empty or weak sections.
- Identify unresolved [проверить по скану] notes.
- Identify unsupported claims that should be checked against scans.
- Do not invent source facts.

Ticket draft:
<<<
PASTE TICKET DRAFT HERE
>>>
```
