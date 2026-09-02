# Stage 1 — Ideation: ambiguity-killer Q&A

The actual three `okto_pulse_ask_ideation_choice_question` calls made before
writing `problem_statement`/`proposed_approach`, per Pulse's ambiguity-killer
protocol (never advance an ideation while ambiguity remains).

## Question 1 — sync/async threshold

> What issue-count ceiling should decide sync vs. async (Celery) export?
> Below the ceiling, the CSV streams back immediately in the response; at or
> above it, we queue a Celery job and return a signed download link instead.

Options offered: **500 issues** (recommended — conservative, favors
sync-path latency safety), 1000 issues, no fixed ceiling.

## Question 2 — CSV columns

> Which columns should the CSV export include? This determines the export
> contract the backend and frontend cards both build against.

Options offered: **fixed core set** (recommended — ID, title, status,
priority, assignee, labels, due date, created/updated), match the visible
Issues List columns, all fields (fixed superset).

## Question 3 — signed URL expiry

> How long should a signed async-export download link stay valid before it
> expires?

Options offered: 1 hour (matches Plane's `SIGNED_URL_EXPIRATION` default),
**24 hours** (chosen — more forgiving for a queued export sitting unopened),
configurable via env var.

All three answers were later **superseded during Refinement** once the real
codebase was read — see `docs/decisions/01-ideation-superseded-by-refinement.md`.
