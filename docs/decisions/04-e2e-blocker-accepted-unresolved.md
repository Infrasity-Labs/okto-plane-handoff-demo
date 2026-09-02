# Decision: stop at a stuck 429 rather than keep burning attempts

**Stage:** Closing the frontend test-coverage gap
**Status:** Left unresolved, deliberately

## Context

Building real e2e coverage found and fixed a genuine bug
(`_apply_rich_filters` returning a tuple instead of a queryset — see
`docs/architecture.md`) and a genuine environment misconfiguration
(`USE_MINIO=0` in local `.env`). Both were confirmed fixed against the live
docker-compose stack: a real export now completes with a valid signed URL.

The last remaining step — getting `apps/web/e2e/export-csv.spec.ts` to a
confirmed-green run — hit a persistent 429 from Plane's own
`AuthenticationThrottle` (`10/minute`, IP-scoped) that did not clear even
after 80+ seconds of zero traffic to the app. One retry cycle showed the
throttle affecting *both* test sessions identically and immediately, ruling
out a simple rolling-window explanation.

## Decision

Stop retrying. Diagnosing this fully would mean inspecting the throttle's
Redis-backed cache key directly — a reasonable next step, but a genuinely
open-ended one, and not what this session's remaining time was for.

## Consequence

This repo ships with:
- A real, committed, but **not confirmed-green** e2e suite
- A card left `rejected` in Pulse, honestly
- A specific, actionable next step recorded in `README.md`'s Known gaps
  section and here, rather than a vague "add tests later"

The alternative — quietly waiting indefinitely, or reporting the suite as
passing without having actually seen it pass — was rejected as dishonest
regardless of how close the finish line looked.
