# Decision: accept the Frontend card's honest task-validation rejection

**Stage:** Frontend implementation → validation
**Status:** Accepted (not overridden)

## Context

Pulse's task-validation gate requires `estimated_completeness >= 80` on this
board, and **auto-fails regardless of the reviewer's own recommendation** if
any threshold is violated. At the time the Frontend card was submitted for
validation, no e2e/browser test harness existed anywhere in this repo — the
2 frontend test scenarios (permission-hidden button, completed/failed
polling states) had real, type-checked implementation but zero executed
evidence.

## Decision

Submit the validation honestly: `estimated_completeness=78`,
`recommendation="approve"` (the code itself was sound), and let the
deterministic gate decide. It failed: `threshold_violations: ["completeness
78 < min 80"]`, card moved to `rejected`.

This was **not** treated as a bug to work around or a score to inflate. It
is exactly what the gate is for.

## Consequence

Real Playwright infrastructure was subsequently built to try to close the
gap for real (see `docs/decisions/04-e2e-blocker-accepted-unresolved.md`).
The Frontend card remains `rejected` in Pulse at the point this repo was
published — an accurate, current reflection of the work's real state, not
a status forced to look more finished than it is.
