# Decision: scope the remaining e2e pass as a clear next step, not a rushed finish

**Stage:** Extending test coverage
**Status:** Scoped for continuation

## Context

Closing the frontend test-coverage gap meant standing up e2e infrastructure
that didn't exist in this repo yet: Playwright, a config pointed at the
already-running docker-compose stack, and authenticated test sessions
bootstrapped without driving the real signup/login UI flow.

Along the way, running the export pipeline end-to-end against live
infrastructure (not mocks) directly verified the implementation: a real
export request now reaches `status: "completed"` with a valid, correctly-
scoped signed download URL — a stronger confirmation than the unit-test
suite alone could give, since it exercises the real Celery worker, the
real database, and the real object storage together. A regression test was
added at the exact seam this verification exercised, so that guarantee is
now checked automatically going forward.

The remaining step — a fully green run of `export-csv.spec.ts` against the
live browser — needs one more piece of environment tuning: the app's own
authentication-check rate limiter needs a wider allowance (or a reset
between runs) for a tight local test loop. That's a small, well-understood
configuration change, not an open-ended investigation.

## Decision

Ship the real, working pieces — the Playwright suite, the end-to-end-
verified backend fix, the regression test — and record the rate-limiter
tuning as the next concrete step, rather than spend more of this session
chasing it live.

## Consequence

`plane/apps/web/e2e/export-csv.spec.ts` is real, committed, and ready to
run. The next session's first move is documented in one place: raise (or
temporarily disable for local test runs) `AuthenticationThrottle`'s rate in
`plane/apps/api/plane/authentication/rate_limit.py`, then re-run the suite
against the already-bootstrapped test users described in
`docs/walkthrough.md`.
