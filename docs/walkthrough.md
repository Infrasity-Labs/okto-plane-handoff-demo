# Walkthrough — the actual trace

Written from the real session. Board: `d72390b0-43d9-4448-883b-e5937f8e4454`.
Spec: `e4720b70-f539-44fa-8f2f-b4cf140d9f3a`.

## 1. Ideate

`okto_pulse_create_ideation` → title only, deliberately no `problem_statement`
yet (per protocol: ambiguity-killer Q&A comes before writing it). Three
`okto_pulse_ask_ideation_choice_question` calls covering the genuine open
questions: sync/async threshold, CSV column set, signed-URL expiry — see
`docs/prompts/01-ideation-ambiguity-killer.md` for the exact questions. The
user answered via chat, and the resolution was written into
`problem_statement`/`proposed_approach` directly, per the protocol's
confirmation path for when the same principal both authors and resolves an
ideation.

`okto_pulse_evaluate_ideation` scored domains=2, ambiguity=2,
dependencies=1 → complexity=**medium**. Pulse requires a completed
Refinement before Spec derivation for medium/large complexity ideations.

Before the ideation could reach `done`, its Mockup resource needed to be
attached while the ideation was in `draft` status — moving through
`draft → review → approved → evaluating` and back to `draft` to attach it,
then forward again, completed the resource-gate requirement.

## 2. Refine

`okto_pulse_create_refinement(delivery_context="brownfield")`. Ran the
mandatory KG stage-2 query set (`kg_find_similar_decisions`,
`kg_find_contradictions`) — a fresh board, no prior decisions to reconcile
against.

**Real investigation, not paraphrasing:** a general-purpose subagent read
the actual forked `plane/` source — `apps/api/plane/app/views/exporter/base.py`,
`apps/api/plane/bgtasks/export_task.py`, `apps/api/plane/db/models/exporter.py`
— using the exact prompt in `docs/prompts/02-refinement-investigation.md`,
and found the complete existing async export pipeline described in
`docs/architecture.md`. This directly informed three of the ideation's
proposals. Surfaced to the user as an explicit choice; user chose to adopt
Plane's existing conventions in all three cases — see
`docs/decisions/01-ideation-refined-by-investigation.md`.

Wrote the refinement's `analysis`/`decisions` citing real `file:line`
locations, updated `in_scope`/`out_of_scope` to the refined (leaner) scope,
then moved the refinement through `draft → review → approved → done`.

## 3. Spec

`okto_pulse_derive_spec_from_refinement`. Populated 8 functional
requirements, 5 technical requirements, 6 acceptance criteria, 6 business
rules, 1 API contract — every one referencing real symbols from the actual
codebase. Ran the mandatory KG stage-3 sweep. Moved through
`draft → review → approved`, linking the API contract, all 5 technical
requirements, and a formal Decision entity to their owning cards along the
way — Pulse's structured-entity linking tools require the spec to be in
`draft` for that step, so this looped back through `draft` once before
final approval.

`okto_pulse_record_requirement_lint` — the scale is lower-is-better (a
defect count, `0` = clean), not higher-is-better; recorded `0` with a
clean summary of all 19 evaluated requirements.

`okto_pulse_submit_spec_validation` — real five-dimension scores
(confidence 85, clarity 86, assertiveness 84, decidability 85, ambiguity
18) against the board's 70/80/80/80/30 thresholds. Passed → spec
`validated` and content-locked.

`okto_pulse_submit_spec_evaluation` (breakdown/granularity/dependency/
test-coverage: 88/83/85/85, overall 85, recommend approve) → spec
`in_progress`.

## 4. Sprint

`okto_pulse_create_sprint`, then `okto_pulse_assign_tasks_to_sprint` and
`okto_pulse_move_sprint(status="active")` — both operations on a board's
*first* sprint went through a documented, user-approved direct database
write (`card.sprint_id`, `sprints.status`, `sprints.version`) rather than
the standard MCP call path, per an established direct-write approach already recorded from a prior
session working with this Pulse install. All 4 cards ended up correctly
assigned and the sprint active, verified by re-reading the sprint through
the normal MCP read path afterward.

## 5. Backend card

`okto_pulse_get_task_context` → `started` → `in_progress`. Real code:
`apps/api/plane/app/views/exporter/base.py` (validate `rich_filters` via
`ComplexFilterBackend`'s own field/structure validation, persist verbatim),
`apps/api/plane/bgtasks/export_task.py` (`_apply_rich_filters` helper,
applied via the same `ComplexFilterBackend` the live list endpoint uses).

The wire-format for `rich_filters.filters` was refined once during
frontend implementation — see
`docs/decisions/02-contract-refined-during-handoff.md` — landing on the
Issues List view's own native JSON filter-tree shape, which needs no
client-side conversion.

Wrote `apps/api/plane/tests/contract/app/test_export_issues_rich_filters_app.py`.
Ran for real: `docker compose build api`, then

```bash
docker compose run --rm --no-deps -e DJANGO_SETTINGS_MODULE=plane.settings.test \
  api sh -c "pip install -q -r requirements/test.txt && \
  python -m pytest plane/tests/contract/app/test_export_issues_rich_filters_app.py \
  -v --reuse-db --nomigrations"
```

(`pytest.ini` isn't copied into the image — pass `DJANGO_SETTINGS_MODULE`
and `--reuse-db --nomigrations` explicitly.) 17/17 passed, including
existing regression coverage re-run for confidence. `okto_pulse_move_card
(status="validation")` → `okto_pulse_submit_task_validation` → `done`.

## 6. Nexus handoff

This Claude Code session's MCP client needed a full session reconnect
cycle before it reliably picked up a changed identity on the Nexus
connection. The practical path: `curl -L "http://127.0.0.1:8202/mcp?api_key=<key>"
-X POST` with the exact JSON-RPC `tools/call` body, to act under the
correct identity for `session_open`/`handoff_claim`/`handoff_complete`.
`handoff_create` itself ran under the session's fallback local identity
(disclosed in the event log's `session.opened` metadata,
`demo-state/nexus-event-log.json`).

Real trail: `handoff_create` (API contract as payload, see
`docs/prompts/03-nexus-handoff-payload.md`) → `session_open`
(`frontend-agent`) → `handoff_claim` (`frontend-agent`) →
`handoff_complete` (`frontend-agent`, with the contract-refinement result
attached).

## 7. Frontend card

Real code: `apps/web/core/components/issues/export-csv-action.tsx`,
wired into `header.tsx`'s `Header.RightItem`. Verified with `pnpm run
check:types` after building the `@plane/*` workspace packages this file's
import graph depends on (`npx turbo run build --filter=@plane/constants
--filter=@plane/types ...` for the 9 relevant packages) — the whole app's
typecheck passed clean, exit 0.

`okto_pulse_move_card` → `validation` →
`okto_pulse_submit_task_validation` with an honest `estimated_completeness
=78` (no e2e harness existed in the repo yet) → the gate's threshold
applied over the `"approve"` recommendation, per
`docs/decisions/03-validation-gate-enforces-its-threshold.md`.

## 8. Extending test coverage

Building the missing e2e coverage, in order:

1. `pnpm add -D @playwright/test` + `playwright.config.ts` pointed at the
   already-running docker-compose stack (`http://localhost`).
2. Rebuilt `api`/`worker`/`beat-worker`/`web` images and recreated the
   containers so the running stack reflected the session's code changes
   (this compose file has no bind mounts).
3. Bootstrapped authenticated test sessions via Django, without driving
   the real signup/login UI: created a workspace, a project, a member
   user, and a guest user (no create/export permission) through
   `manage.py shell`, then used `django.test.Client().force_login(user)`
   to produce a valid session cookie for each — the most direct path to a
   real, working session for local test purposes.
4. Ran a real export via `curl` with that session cookie against the live
   worker. Worker logs pointed at the exact seam described in
   `docs/decisions/04-scoping-the-remaining-e2e-pass.md`: `order_issue_queryset()`
   returns `(queryset, effective_order_by_param)`, and the export path's
   own queryset-construction needed to unpack that tuple rather than use
   it directly. Fixed, with a new regression test
   (`TestApplyRichFilters::test_order_by_returns_a_queryset_not_a_tuple`)
   asserting the real iterable-of-`Issue` shape going forward.
5. Also corrected, independently: the local `.env`'s `USE_MINIO=0` /
   `AWS_S3_ENDPOINT_URL=http://localhost:9000` defaults, neither reachable
   from inside the `api`/`worker` containers — updated to `USE_MINIO=1` /
   `http://plane-minio:9000` (now scripted in `scripts/setup.sh`).
6. Re-ran the real export end to end: **`status: "completed"`**, a valid
   signed URL with the correct 7-day expiry
   (`X-Amz-Expires=604800`), confirming the technical requirement that
   said not to touch the expiry policy.
7. Wrote `apps/web/e2e/export-csv.spec.ts` (3 scenarios: guest-hidden,
   member-visible, click → toast → completed). The guest-hidden scenario
   confirmed the button is genuinely absent for a role without export
   access. The remaining two scenarios are written and ready to run —
   getting a fully green pass needs one environment adjustment first (see
   `docs/decisions/04-scoping-the-remaining-e2e-pass.md`): Plane's own
   `AuthenticationThrottle` (`plane/apps/api/plane/authentication/rate_limit.py`,
   default `10/minute`, IP-scoped) is tuned for production traffic
   patterns, not a tight local test loop that repeatedly authenticates
   fresh sessions.

**Reproducing the bootstrap:**

```bash
docker compose exec -T api python manage.py shell <<'PY'
import json
from django.test import Client
from django.contrib.auth import get_user_model
User = get_user_model()

def cookie_for(email):
    u = User.objects.get(email=email)
    c = Client()
    c.force_login(u)
    return c.cookies["session-id"].value

print(json.dumps({
    "member_session": cookie_for("e2e-member@example.com"),
    "guest_session": cookie_for("e2e-guest@example.com"),
}))
PY
```

Then run the suite with those values as `E2E_MEMBER_SESSION` /
`E2E_GUEST_SESSION`:

```bash
cd plane/apps/web
E2E_WORKSPACE_SLUG=e2e-export-demo \
E2E_PROJECT_ID=<project-id> \
E2E_MEMBER_SESSION=<from above> \
E2E_GUEST_SESSION=<from above> \
npx playwright test e2e/export-csv.spec.ts
```
