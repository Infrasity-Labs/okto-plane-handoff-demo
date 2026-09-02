# OktoLabs Combined Use-Case: Pulse + Nexus on Plane

Status: **~50% done, real, and left mid-flight on purpose.** This is a genuine
live-run trace, not a staged demo — see [Known gaps / what's left](#known-gaps--whats-left)
for exactly where it stops and what a next session needs to do to finish it.

## What this is

A fork of `makeplane/plane` (Django API + React/Vite web, AGPL-3.0) with one
real feature — wiring filter-aware CSV export into the Issues List view —
built end-to-end by a Claude Code session acting as both `backend-agent` and
`frontend-agent`, coordinated through a real Nexus handoff and governed by a
real Pulse SDLC pipeline (ideation → refinement → spec → sprint → cards).

Nothing here is scripted after the fact. The ideation's original assumptions
were wrong (see below), a real bug was found and fixed by actually running
the code end-to-end against live infrastructure (not mocks), and the run
stopped on a real, unresolved environment blocker rather than a clean finish.

## The trace, honestly

1. **Ideation** (`CSV export for filtered issue views`) assumed a new
   synchronous export path, a 24h signed-URL expiry, and a fixed core CSV
   column set — reasonable assumptions for a greenfield feature, made before
   any code was read.
2. **Refinement** investigated the actual forked codebase and found Plane
   *already ships* a complete async CSV/XLSX/JSON export pipeline
   (`ExportIssuesEndpoint` → `issue_export_task` → presigned S3/MinIO URL →
   `PrevExports` polling UI) — including an **unused `rich_filters` field**
   on the `ExporterHistory` model and a stubbed-out filter-picker block in
   the frontend's `ExportForm`, clear evidence Plane's own team scaffolded
   this exact integration and never finished it. All three ideation
   assumptions were superseded in favor of reusing what was already there.
3. **Spec** was authored, KG-checked, and pushed through Pulse's real
   validation gate: confidence 85, clarity 86, assertiveness 84,
   decidability 85, ambiguity 18 (against 70/80/80/80/30 thresholds) —
   plus a full coverage sweep (AC/FR→BR/scenario→task/TR→task/decision, all
   100%). Two real Pulse product bugs were hit and worked around along the
   way (see `docs/walkthrough.md`).
4. **Sprint** was created and populated with 4 cards (Backend, Frontend, 2
   Test cards), dependency-linked. Hit a third real Pulse bug (a
   policy-versioning bootstrap gap on a board's first sprint) — worked
   around with a documented, user-approved direct DB write.
5. **Backend card → done**, with real evidence: 17 passing pytest tests run
   inside the project's own docker-compose `api` container, not just written.
6. **Real Nexus handoff**: `backend-agent` → `frontend-agent`, the API
   contract as the artifact, `handoff_create` → `handoff_claim` →
   `handoff_complete` — see `.nexus/event-log-export.json` for the actual
   event trail.
7. **Frontend card → honestly rejected.** Pulse's task-validation gate
   computed completeness=78 (below the board's 80% threshold) because no
   e2e test harness existed in this repo at implementation time — and the
   gate **enforced that threshold over the reviewer's own `approve`
   recommendation**. This is the deterministic gate working exactly as
   designed, not a bug.
8. **Closing the gap, for real**: Playwright was added from scratch,
   authenticated test sessions were bootstrapped via Django (see
   `docs/walkthrough.md` for the real debugging trail — a session-hash
   subtlety, a `USE_MINIO=0` misconfiguration). Running the real pipeline
   end-to-end **found and fixed a genuine bug**: `_apply_rich_filters`
   assigned a `(queryset, order_by_param)` tuple directly as the queryset,
   crashing every export that combined a filter with a sort. Fixed, with a
   regression test, and confirmed against the live stack — a real export
   now reaches `status: "completed"` with a valid signed URL.
9. **Where it actually stops**: the Playwright suite itself is real and
   committed, but its one full run hit a persistent 429 from Plane's
   `AuthenticationThrottle` (10/minute, IP-scoped) that did not clear even
   after 80+ seconds of zero traffic. That's an unresolved, disclosed
   blocker — not swept under the rug.

## Known gaps / what's left

This is deliberately not finished — pick any of these up:

- [ ] **Clear the stuck 429** (`plane/authentication/rate_limit.py`,
      `AuthenticationThrottle`, cache-backed via Redis) and get
      `apps/web/e2e/export-csv.spec.ts` actually green against the live
      stack. See `docs/walkthrough.md` for what's already been ruled out.
- [ ] Move the Frontend card (`bb89c680-ce53-4638-8d0c-ee7e3253fa90`) back to
      `in_progress` in Pulse, resubmit task validation once real e2e
      evidence exists (`okto_pulse_submit_task_validation`).
- [ ] Update the 2 frontend test scenarios
      (`ts_b8cd4cfc`, `ts_4baa4e47`/`ts_2f92da90`) via
      `okto_pulse_update_test_scenario_status` with real Playwright evidence,
      then move the Frontend test card to `done`.
- [ ] Move the Sprint and Spec to `done` once both cards are closed.
- [ ] Re-fix `docker-compose.yml`'s `proxy`/`live` env-passthrough gaps
      (found and fixed locally, see `docs/architecture.md`) as their own PR —
      genuinely useful upstream even independent of this feature.
- [ ] Consider the stretch goal from the original plan: open the real PR to
      `makeplane/plane` once the above is closed out.

## Layout

```
okto-plane-handoff-demo/
├── plane/               forked repo (github.com/yuvicodesgit/plane),
│                        branch feature/issue-csv-export — 4 real commits
├── .pulse/              real board/spec state export (see files)
├── .nexus/              real workspace config + event-log export
├── docs/
│   ├── architecture.md  Pulse + Nexus integration, real bugs found
│   └── walkthrough.md   the actual MCP call trace, including dead ends
└── scripts/setup.sh     bootstrap: plane + pulse + nexus, one command
```

## Running it

```bash
./scripts/setup.sh
```

Then see `docs/walkthrough.md` for the exact commands used to reproduce the
bootstrap test data and the (currently blocked) e2e run.
