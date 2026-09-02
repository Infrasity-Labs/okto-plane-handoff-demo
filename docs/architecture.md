# Architecture — Pulse + Nexus on Plane

## Integration point

Pulse and Nexus remain architecturally independent (no import, network call,
or config flag connects their codebases) — the only connection is a single
agent client (here: one Claude Code session, playing both `backend-agent` and
`frontend-agent`) holding both MCP server URLs simultaneously, working
against the same `plane/` checkout.

- **Pulse** governs *what to build*: ideation → refinement → spec → sprint →
  card lifecycle, knowledge graph, spec-gated validation.
- **Nexus** governs *who's allowed to act and when*: handoff create/claim/
  complete, session presence, event-log audit trail.

## Sequence (as it actually ran)

```
Ideation (assumptions, pre-code-read)
   │
   ▼
Refinement (real codebase investigation) ──► supersedes 3 ideation decisions
   │
   ▼
Spec (validated: 85/86/84/85/18, all coverage 100%)
   │
   ▼
Sprint (4 cards, dependency-linked)
   │
   ├─► Backend card ──► done (17 real pytest passes)
   │        │
   │        ▼
   │   Nexus handoff: backend-agent → frontend-agent
   │   (API contract as artifact, real create/claim/complete trail)
   │        │
   │        ▼
   └─► Frontend card ──► REJECTED (task validation: completeness 78 < 80)
            │
            ▼
       Playwright added, real bug found + fixed running e2e,
       then blocked on a stuck 429 (see walkthrough.md)
```

## Agent roles

| Role | Preset (Pulse) | Nexus identity | Client | Actually used as |
|---|---|---|---|---|
| Spec Agent | Spec | `spec-agent` | — | not separately exercised — same session did ideation/refinement/spec |
| Backend Agent | Executor | `backend-agent` | Claude Code | ran as `local-agent` due to an MCP client identity-caching bug (disclosed) |
| Frontend Agent | Executor | `frontend-agent` | Claude Code (standing in for Cursor) | ran as the real `frontend-agent` identity via a direct HTTP MCP workaround |
| Validator Agent | Validator | `validator-agent` | — | task validations submitted under `local-agent`, `reviewer_separation_mode=off` on this board |

## Real bugs found this session

Three categories, documented in full in the git history / Pulse card
comments — summarized here:

1. **Pulse product bugs** (workarounds documented, not permanent fixes):
   - Resource-gate (mockup/architecture) attachment only works in `draft`
     status, but there's no `evaluating→draft` transition — requires a
     round-trip through `approved→review→draft`.
   - TR-coverage's own `blocked_reason` message tells you to call
     `link_task(target_type='tr', ...)`, but that path actually requires a
     *content-locked* spec — the real fix is
     `update_spec_entity(operation='link_task')`, which needs `draft`.
   - Sprint task assignment (`assign_tasks_to_sprint`) and sprint activation
     (`move_sprint`) both crash with `policy_subject_versioning_transaction_missing`
     on a board's *first* sprint — worked around with a direct, user-approved
     SQLite write (`card.sprint_id`, `sprints.status`).

2. **`makeplane/plane` upstream bugs** (fixed locally, worth a real PR):
   - `docker-compose.yml`'s `proxy` service didn't pass `SITE_ADDRESS`/
     `CERT_EMAIL`/etc. into the container → Caddy crash-looped.
   - `docker-compose.yml`'s `live` service had no `env_file` at all → failed
     required-env validation on every boot.
   - Local dev `.env` ships `USE_MINIO=0` and
     `AWS_S3_ENDPOINT_URL=http://localhost:9000`, neither reachable from
     inside the `api`/`worker` containers — the async export pipeline can
     never actually complete locally with the shipped defaults.

3. **This feature's own bug** (found + fixed):
   - `_apply_rich_filters` (added this session) assigned
     `order_issue_queryset()`'s return value — a `(queryset,
     effective_order_by_param)` tuple — directly as the queryset. Any real
     export combining a filter with a sort crashed with
     `'SoftDeletionQuerySet' object has no attribute 'parent'`. Invisible to
     mocked unit tests; caught only by actually running the Celery task
     against a live worker. Fixed with a regression test.

## What's NOT resolved

The Playwright e2e suite (`apps/web/e2e/export-csv.spec.ts`) is real and
committed, but its one full run was blocked by a persistent 429 from
`AuthenticationThrottle` — see `docs/walkthrough.md` for the full debugging
trail (ruled out: simple rate-limit window expiry, Caddy-level limiting;
not yet tried: direct Redis cache-key inspection/reset).
