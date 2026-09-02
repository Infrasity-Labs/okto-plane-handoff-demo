# Walkthrough — the actual trace

This is written from the real session, including the dead ends. Board:
`d72390b0-43d9-4448-883b-e5937f8e4454`. Spec: `e4720b70-f539-44fa-8f2f-b4cf140d9f3a`.

## 1. Ideate

`okto_pulse_create_ideation` → title only, deliberately no `problem_statement`
yet (per protocol: ambiguity-killer Q&A comes before writing it). Three
`okto_pulse_ask_ideation_choice_question` calls covering the genuine open
questions: sync/async threshold, CSV column set, signed-URL expiry. User
answered via chat (not through Pulse's own Q&A UI, since the same principal
can't both ask and answer — `okto_pulse_answer_ideation_question` correctly
rejected that with `self_answering_not_allowed`); the resolution was written
into `problem_statement`/`proposed_approach` instead, per the protocol's
alternative confirmation path.

`okto_pulse_evaluate_ideation` scored domains=2, ambiguity=2,
dependencies=1 → complexity=**medium**. Medium/Large complexity turned out
to *require* a completed Refinement before Spec derivation — not optional,
despite how the source planning doc summarized it.

Resource gate hit: mockup/architecture attachment only works in `draft`, but
the ideation was already in `evaluating`. No `evaluating→draft` edge exists.
Fix: `evaluating→approved→review→draft` round-trip (each edge individually
allowed), attach resources, then `draft→review→approved→evaluating→done`
again.

## 2. Refine

`okto_pulse_create_refinement(delivery_context="brownfield")`. Ran the
mandatory KG stage-2 query set (`kg_find_similar_decisions`,
`kg_find_contradictions`) — clean, fresh board.

**Real investigation**, not paraphrasing: a general-purpose subagent read the
actual forked `plane/` source — `apps/api/plane/app/views/exporter/base.py`,
`apps/api/plane/bgtasks/export_task.py`, `apps/api/plane/db/models/exporter.py`
— and found the complete existing async export pipeline described in
`docs/architecture.md`. This directly contradicted three ideation decisions.
Surfaced to the user as an explicit choice (not silently overridden); user
chose to adopt Plane's existing conventions in all three cases.

Wrote the refinement's `analysis`/`decisions` citing real `file:line`
locations, updated `in_scope`/`out_of_scope` to the corrected (leaner) scope,
then `draft→review→approved→done`.

## 3. Spec

`okto_pulse_derive_spec_from_refinement`. Populated 8 FRs, 5 TRs, 6 ACs, 6
BRs, 1 API contract — all referencing real symbols. Ran the mandatory KG
stage-3 sweep. `draft→review→approved`.

Hit the TR-linkage bug here: `blocked_reason` said to call
`link_task(target_type='tr', ...)`, which failed with
`"Traceability-only path is only available for content-locked specs"` — the
real path is `update_spec_entity(operation='link_task')`, which needs
`draft`. Round-tripped back to `draft`, linked the API contract + all 5 TRs
there, then forward again. Same pattern recurred for the Decision-coverage
gate (needed ≥1 active Decision with a linked task) and the resource-gate
mockup-on-spec requirement.

`okto_pulse_record_requirement_lint` — first attempt used `score=100` with no
findings and got `requirement_lint_score_findings_mismatch`; the scale is
lower-is-better (a defect count), not higher-is-better. `score=0` succeeded.

`okto_pulse_submit_spec_validation` — real five-dimension scores (85/86/84/85/18)
against the board's 70/80/80/80/30 thresholds. Passed → spec `validated`
and content-locked.

`okto_pulse_submit_spec_evaluation` (breakdown/granularity/dependency/test-coverage,
85/83/85/85, overall 85, recommend approve) → spec `in_progress`.

## 4. Sprint

`okto_pulse_create_sprint` succeeded. `okto_pulse_assign_tasks_to_sprint`
crashed with `policy_subject_versioning_transaction_missing` — a
known-pattern bug (documented in a prior session's memory) on a board's
*first* sprint. User-approved direct SQLite write:
`UPDATE cards SET sprint_id=... ; UPDATE sprints SET version=version+1`.
`okto_pulse_move_sprint(status="active")` hit the *same* error — same fix
pattern, `UPDATE sprints SET status='active'`.

## 5. Backend card

`okto_pulse_get_task_context` → `started` → `in_progress`. Real code:
`apps/api/plane/app/views/exporter/base.py` (validate `rich_filters` via
`ComplexFilterBackend`'s own field/structure validation, persist verbatim),
`apps/api/plane/bgtasks/export_task.py` (`_apply_rich_filters` helper,
applied via the same `ComplexFilterBackend` the live list endpoint uses).

**First implementation attempt used the wrong wire format** — routed through
`LegacyToRichFiltersConverter` assuming legacy flat field names. A second
Explore subagent investigation (triggered while building the *frontend*
piece) found the Issues List view's actual `richFilters` store already
produces the JSON filter-tree shape `ComplexFilterBackend` natively consumes
— confirmed against `packages/shared-state/src/store/work-item-filters/adapter.ts`.
Backend commit amended (`aac6565a01`) to apply the tree directly — simpler,
and zero client-side mapping needed.

Wrote `apps/api/plane/tests/contract/app/test_export_issues_rich_filters_app.py`.
Ran for real: `docker compose build api`, then
`docker compose run --rm --no-deps -e DJANGO_SETTINGS_MODULE=plane.settings.test
api sh -c "pip install -q -r requirements/test.txt && python -m pytest ... --reuse-db --nomigrations"`
(pytest.ini isn't copied into the image — pass `DJANGO_SETTINGS_MODULE` and
`--reuse-db --nomigrations` explicitly). 17/17 passed including pre-existing
regression coverage. `okto_pulse_move_card(status="validation")` →
`okto_pulse_submit_task_validation` → real gate, `done`.

## 6. Nexus handoff

Identity problem: this Claude Code session's MCP client never picked up a
changed `api_key` on `/mcp` reconnect (tried 3 times across the session,
config file verified correct each time, confirmed server-side correctness
independently via raw `curl`) — filed as product feedback. Practical
workaround: use `curl -L "http://127.0.0.1:8202/mcp?api_key=<key>" -X POST`
with the exact JSON-RPC `tools/call` body to act under the correct identity
for `session_open`/`handoff_claim`/`handoff_complete`, while `handoff_create`
itself ran under the stuck `local-agent` identity (disclosed in the event
log's `session.opened` metadata).

Real trail (`demo-state/nexus-event-log.json`): `handoff_create` (local-agent,
API contract as payload) → `session_open` (frontend-agent, via curl) →
`handoff_claim` (frontend-agent) → `handoff_complete` (frontend-agent, with
the contract-correction result attached).

## 7. Frontend card

Real code: `apps/web/core/components/issues/export-csv-action.tsx`,
wired into `header.tsx`'s `Header.RightItem`. Verified with
`pnpm run check:types` — first attempt failed with `Cannot find module
'@plane/constants'` etc. across the *whole* app (confirmed pre-existing:
even `header.tsx`'s original imports failed identically), root cause was
unbuilt workspace packages (`corepack`/`husky` step had failed during initial
`setup.sh`). Fixed: `npm install -g corepack && corepack enable`, then
`npx turbo run build --filter=@plane/constants --filter=@plane/types ...`
for the 9 packages this file's import graph touches. Typecheck then passed
clean (exit 0) for the whole app.

`okto_pulse_move_card` → `validation` → `okto_pulse_submit_task_validation`
with an honest `estimated_completeness=78` (no e2e harness existed in this
repo) → **gate correctly failed** despite `recommendation="approve"**:
`threshold_violations: ["completeness 78 < min 80"]`, `card_status:
"rejected"`. This is the deterministic gate doing its job.

## 8. Closing the gap (partial)

Decided to actually build the missing e2e coverage rather than accept the
rejection. In order:

1. `pnpm add -D @playwright/test` + `playwright.config.ts` pointed at the
   already-running docker-compose stack (`http://localhost`), not a spawned
   dev server.
2. Rebuilt `api`/`worker`/`beat-worker`/`web` images (`docker compose build`)
   and recreated the containers so the running stack actually reflected the
   session's code changes (no bind mounts in this compose file).
3. Needed authenticated test sessions without driving the real signup/login
   UI. First attempt: manually construct a Django session via
   `SessionStore()` — resolved correctly when queried directly, but the live
   app still returned 401 and **actively cleared the cookie**. Root cause:
   Django's `get_user()` verifies `_auth_user_hash` (the session auth hash)
   against the current user, and a manually-built session omitted it.
   Confirmed by contrast: `django.test.Client().force_login(user)` worked
   immediately (200) — it produced a much longer, differently-formatted
   session key, going through Django's real `login()` path. Fix: use
   `force_login()` in a `manage.py shell` script (creates two users — a
   workspace admin/member and a guest with no create/export permission — a
   workspace, a project, a few issues) and capture the resulting cookie
   values, rather than hand-rolling `SessionStore`.
4. First real end-to-end export attempt (via `curl`, with a real
   `session-id` cookie) reached `status: "failed"`. Worker logs showed
   `'SoftDeletionQuerySet' object has no attribute 'parent'` — the tuple bug
   described above and in `docs/architecture.md`. Fixed, rebuilt, retested:
   a second attempt (no `rich_filters`) failed differently — `Could not
   connect to the endpoint URL: "http://localhost:9000/..."` — the
   `USE_MINIO=0`/`AWS_S3_ENDPOINT_URL=http://localhost:9000` local-env
   misconfiguration (container-unreachable). Fixed in `apps/api/.env`
   (untracked, not committed) to `USE_MINIO=1` /
   `http://plane-minio:9000`. Recreated containers. Retested: **`status:
   "completed"`**, valid signed URL with a 7-day expiry
   (`X-Amz-Expires=604800`), confirming the TR that said not to touch the
   expiry policy.
5. Wrote `apps/web/e2e/export-csv.spec.ts` (3 scenarios: guest-hidden,
   member-visible, click→toast→completed). First run: guest-hidden passed,
   the other two timed out waiting for the button. Debugging revealed a 429
   from the page's own top-level navigation request —
   `AuthenticationThrottle` (`plane/authentication/rate_limit.py`,
   `10/minute`, IP-scoped, `Retry-After: 21` observed). Waited out the
   retry-after, re-ran: **still 429**, on *both* sessions this time,
   confirming the earlier "pass" was a false positive (an empty/broken page
   trivially has zero buttons — `toHaveCount(0)` doesn't verify the page
   actually rendered).
6. Backed off completely (zero requests) for 80+ seconds, re-tried once: still
   429, immediately, on the very first request. This rules out a simple
   rolling-window explanation — the throttle state appears stuck beyond its
   nominal `10/minute` decay, which would need a direct look at the
   Redis-backed cache key (DRF's `SimpleRateThrottle` is cache-backed) to
   resolve, not more waiting.

**Stopped here** — real infrastructure, real bug found and fixed
(`_apply_rich_filters` + the MinIO env fix), but the e2e suite itself has
zero confirmed-passing runs against a properly-rendering page. Left as the
honest state for the next session to pick up.
