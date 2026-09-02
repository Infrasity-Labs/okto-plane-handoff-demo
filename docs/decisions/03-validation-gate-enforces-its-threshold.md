# Decision: let the task-validation gate's threshold decide, not the reviewer

**Stage:** Frontend implementation → validation
**Status:** Demonstrated as designed

## Context

Pulse's task-validation gate requires `estimated_completeness >= 80` on
this board, and **enforces that threshold independently of the reviewer's
own recommendation**. At the point the Frontend card was submitted for
validation, its implementation was complete and type-verified, but the
project's e2e/browser test harness (Playwright) had not yet been added —
so the 2 frontend test scenarios had real, reviewed implementation but no
executed evidence yet.

## Decision

Submit the validation with an honest completeness estimate reflecting
exactly what had executed evidence at that point (`78`), together with
`recommendation="approve"` on the implementation's own merits, and let the
deterministic gate decide rather than rounding the number up to clear the
threshold. The gate's own arithmetic applied: `threshold_violations:
["completeness 78 < min 80"]`, and the card is currently awaiting that
evidence before its next validation pass.

This is the gate doing exactly what it's designed to do: a numeric
threshold that a reviewer's qualitative opinion cannot override.

## Consequence

Real Playwright infrastructure was subsequently built to close the gap —
see `docs/decisions/04-scoping-the-remaining-e2e-pass.md`. The Frontend
card's current status in `demo-state/board-export.json` is an accurate,
live reflection of the work's real state at the point this repo was
published, not a status adjusted to look further along than it is.
