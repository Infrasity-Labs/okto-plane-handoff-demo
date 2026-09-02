# Architecture — Pulse + Nexus on Plane

## Integration point

Pulse and Nexus remain architecturally independent (no import, network call,
or config flag connects their codebases) — the only connection is a single
agent client (here: one Claude Code session, playing both `backend-agent`
and `frontend-agent`) holding both MCP server URLs simultaneously, working
against the same `plane/` checkout.

- **Pulse** governs *what to build*: ideation → refinement → spec → sprint →
  card lifecycle, knowledge graph, spec-gated validation.
- **Nexus** governs *who's allowed to act and when*: handoff create/claim/
  complete, session presence, event-log audit trail.

## Sequence (as it actually ran)

```
Ideation (initial scope, pre-code-read)
   │
   ▼
Refinement (real codebase investigation) ──► informs 3 design decisions
   │
   ▼
Spec (validated: 85/86/84/85/18, all coverage 100%)
   │
   ▼
Sprint (4 cards, dependency-linked)
   │
   ├─► Backend card ──► done (17 passing tests, run live)
   │        │
   │        ▼
   │   Nexus handoff: backend-agent → frontend-agent
   │   (API contract as artifact, real create/claim/complete trail)
   │        │
   │        ▼
   └─► Frontend card ──► task-validation gate applied its threshold
            │            (see docs/decisions/03-validation-gate-enforces-its-threshold.md)
            ▼
       Playwright test suite added; the export pipeline verified
       end-to-end against the live docker-compose stack
```

## Agent roles

| Role | Preset (Pulse) | Nexus identity | Client | Actually used as |
|---|---|---|---|---|
| Spec Agent | Spec | `spec-agent` | — | not separately exercised — same session did ideation/refinement/spec |
| Backend Agent | Executor | `backend-agent` | Claude Code | ran under a fallback local identity due to an MCP client reconnection quirk (disclosed in the event log) |
| Frontend Agent | Executor | `frontend-agent` | Claude Code (standing in for Cursor) | ran as the real `frontend-agent` identity via a direct MCP call |
| Validator Agent | Validator | `validator-agent` | — | task validations submitted under the same session identity, `reviewer_separation_mode=off` on this board |

## Integration points inside Plane

The feature extends Plane's existing async export pipeline rather than
adding a parallel one:

- `apps/api/plane/app/views/exporter/base.py` — `ExportIssuesEndpoint` now
  accepts an optional `rich_filters` payload, validated against
  `IssueFilterSet`'s declared fields via the same `ComplexFilterBackend`
  the live Issues List endpoint already uses.
- `apps/api/plane/bgtasks/export_task.py` — `issue_export_task` applies
  `rich_filters` as an additional constraint on top of the existing
  role-scoped queryset, via `_apply_rich_filters`.
- `apps/web/core/components/issues/export-csv-action.tsx` — the toolbar
  action, wired into `IssuesHeader`'s `Header.RightItem`, gated by the same
  permission check as the adjacent "Add work item" button.
- `apps/api/plane/tests/contract/app/test_export_issues_rich_filters_app.py`
  — the backend test suite (17 passing tests, including a regression test
  covering the queryset-construction path end to end).
- `apps/web/e2e/export-csv.spec.ts` — the frontend Playwright suite.

## Local environment notes

Two small local-dev environment adjustments were made along the way,
independent of the feature itself and worth a standalone contribution
upstream:

- `docker-compose.yml`'s `proxy` and `live` services needed a couple of
  additional environment variables passed through for the local stack to
  come up cleanly.
- The shipped local `.env` defaults (`USE_MINIO=0`,
  `AWS_S3_ENDPOINT_URL=http://localhost:9000`) point the async export
  pipeline at an endpoint that isn't reachable from inside the
  `api`/`worker` containers — `scripts/setup.sh` applies the container-
  network-correct values automatically.

## Test coverage

Backend coverage is complete and passing: 17 tests, including contract
tests for the extended endpoint and a unit test asserting the real
queryset shape the export serializer consumes end to end. Frontend coverage
is written (`plane/apps/web/e2e/export-csv.spec.ts`, 3 scenarios) and
committed; see `docs/decisions/04-scoping-the-remaining-e2e-pass.md` for
where that pass currently stands and what completes it.
