#!/usr/bin/env python3
"""Seed a freshly-installed Okto Pulse instance with the exact board state
this demo ships in a "captured mid-flight, halfway point" configuration —
1 ideation, 1 refinement, 1 spec (validated, in_progress), 1 active sprint,
4 cards (2 done, 1 rejected, 1 not_started).

Why this exists: demo-state/*.json is a read-only *export* of what the real
run produced — Pulse has no "import a board" tool, so a fresh `okto-pulse
serve` boots with an empty default board. This script replays the same
final field values (requirements, rules, contract, decision, test
scenarios, mockup, card statuses) through the real Pulse MCP tool calls so
a fresh clone reaches the same visible board state without redoing the
actual ideation/refinement/investigation work.

What this does NOT do: register or connect Nexus agents (spec-agent,
backend-agent, frontend-agent, validator-agent) — do that yourself per
docs/walkthrough.md, the same as the original run did. It also does not
replay the real Nexus handoff event log — that needs live, connected agent
sessions to be genuine, not something a seed script should fake.

Usage:
    pip install -r scripts/requirements.txt
    python3 scripts/01_seed_pulse_board.py --api-key dash_xxxxx [--host 127.0.0.1] [--port 8101]

Run this once, right after `okto-pulse serve` has completed its first-boot
setup (which prints the API key) and before you start working the board
yourself — it edits the board's *own* default "My Board", assuming it is
still empty. Running it twice creates a second copy of every entity; there
is no idempotency across runs.

Known Pulse quirks this script works around (see okto-pulse's own issue
tracker, not bugs in this demo):
  - Ideation `done` requires Architecture/Mockup resources attached (or
    marked N/A) while in `draft` — reachable only via a review/approved/
    evaluating -> draft round-trip after the ambiguity-killer Q&A.
  - Technical-requirement and API-contract task-card links are rejected by
    `link_task` while the spec is `approved` ("only available for
    content-locked specs"); a `technical_requirement` needs the same
    draft round-trip. Business-rule and decision links work directly.
  - `okto_pulse_assign_tasks_to_sprint` and `okto_pulse_move_sprint` both
    fail on a board's *first* sprint with `policy_subject_versioning_
    transaction_missing` — a documented okto-pulse-core bug. This script
    works around it with a direct, WAL-safe SQLite write to `pulse.db`,
    exactly like the original run did (see the repo's own postmortem
    notes) — flip `SPRINT_DB_WORKAROUND = False` below once this is fixed
    upstream and confirm the normal MCP calls succeed instead.
"""
import argparse
import json
import sqlite3
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import requests

SPRINT_DB_WORKAROUND = True


class Pulse:
    def __init__(self, host, port, api_key):
        self.base = f"http://{host}:{port}/mcp?api_key={api_key}"
        self.headers = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}
        self.session_id = None
        self._id = 0
        self._init()

    def _init(self):
        r = requests.post(self.base, headers=self.headers, json={
            "jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {"protocolVersion": "2024-11-05", "capabilities": {},
                       "clientInfo": {"name": "seed-pulse-board", "version": "1.0"}},
        })
        r.raise_for_status()
        self.session_id = r.headers["mcp-session-id"]
        h = dict(self.headers); h["Mcp-Session-Id"] = self.session_id
        requests.post(self.base, headers=h, json={"jsonrpc": "2.0", "method": "notifications/initialized"})

    def call(self, tool, args, _retries=5):
        self._id += 1
        h = dict(self.headers); h["Mcp-Session-Id"] = self.session_id
        r = requests.post(self.base, headers=h, json={
            "jsonrpc": "2.0", "id": self._id, "method": "tools/call",
            "params": {"name": tool, "arguments": args},
        })
        r.raise_for_status()
        for line in r.text.splitlines():
            if line.startswith("data: "):
                payload = json.loads(line[6:])
                if "error" in payload:
                    raise RuntimeError(f"{tool}: {payload['error']}")
                text = payload["result"]["content"][0]["text"]
                try:
                    data = json.loads(text)
                except json.JSONDecodeError:
                    # Pulse's own background writers (metrics/KG) occasionally
                    # collide with a foreground SQLite write ("database is
                    # locked") under WAL mode — transient, retry with backoff.
                    if "database is locked" in text and _retries > 0:
                        time.sleep(2)
                        return self.call(tool, args, _retries=_retries - 1)
                    raise RuntimeError(f"{tool}: {text}")
                if data.get("outcome") == "error":
                    raise RuntimeError(f"{tool}: {json.dumps(data)}")
                return data
        raise RuntimeError(f"{tool}: no data line in response: {r.text[:300]}")


def step(label):
    print(f"==> {label}", file=sys.stderr)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--api-key", required=True, help="dash_... key printed on first boot, or from an agent's API-key page")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8101, help="Pulse MCP port")
    ap.add_argument("--data-dir", default=None,
                     help="Pulse's DATA_DIR, for the sprint DB workaround (default: $DATA_DIR or ~/.okto-pulse)")
    args = ap.parse_args()

    p = Pulse(args.host, args.port, args.api_key)

    boards = p.call("okto_pulse_list_my_boards", {})["data"]["boards"]
    if not boards:
        sys.exit("No board found — is this really a fresh instance?")
    board = boards[0]["id"]
    print(f"Seeding board {board!r} ({boards[0]['name']!r})", file=sys.stderr)

    # ---------------------------------------------------------------- IDEATION
    step("Creating ideation")
    problem_statement = (
        "Users viewing a filtered/sorted Issues List in Plane have no way to get "
        "that exact view out of the app as a file. They currently resort to manual "
        "copy-paste or third-party scraping to share issue data with stakeholders "
        "who don't have Plane access, or to build reports outside the tool. This is "
        "a gap versus comparable project-management tools, which almost universally "
        "offer list export.\n\nScope is bounded to CSV export of the Issues List "
        "view, respecting whatever filter/sort state is currently applied — not a "
        "general data-export/reporting feature, not other entity types (cycles, "
        "modules, pages), and not other formats (XLSX, PDF) for v1."
    )
    proposed_approach = (
        "Backend (apps/api): new export endpoint reusing the existing issue-list "
        "endpoint's filter/sort query-param handling and project-member view "
        "permissions.\n\nFrontend (apps/web): filter-aware \"Export\" action on the "
        "Issues List view, with toast/progress state and polling for async exports.\n\n"
        "Test/Validator card: backend pytest coverage across filter combinations and "
        "permission boundaries; frontend Playwright test for the export flow; "
        "validator confirms both against the spec's acceptance criteria."
    )
    ideation = p.call("okto_pulse_create_ideation", dict(
        board_id=board, title="CSV export for filtered issue views",
        problem_statement=problem_statement, proposed_approach=proposed_approach,
        labels=["feature", "csv-export", "issues"],
    ))["data"]["ideation"]["id"]

    for status in ["review", "approved", "evaluating"]:
        p.call("okto_pulse_move_ideation", dict(board_id=board, ideation_id=ideation, status=status))

    p.call("okto_pulse_evaluate_ideation", dict(
        board_id=board, ideation_id=ideation,
        domains="2", domains_justification="Backend export pipeline + frontend toolbar action.",
        ambiguity="2", ambiguity_justification="Sync/async threshold, CSV column set, and signed-URL expiry needed resolving.",
        dependencies="1", dependencies_justification="Extends Plane's own existing export pipeline; no external service dependency.",
    ))

    # Round-trip through draft to attach the mandatory resource gate (Architecture
    # N/A + a real Mockup), then back to evaluating for the ambiguity gate.
    for status in ["approved", "review", "draft"]:
        p.call("okto_pulse_move_ideation", dict(board_id=board, ideation_id=ideation, status=status))

    p.call("okto_pulse_mark_resource_not_applicable", dict(
        board_id=board, entity_type="ideation", entity_id=ideation, resource_type="architecture",
        justification="No architectural change — extends an existing pipeline within one existing service."))

    mockup_html = (
        '<div style="font-family:-apple-system,sans-serif;max-width:640px;padding:24px;'
        'border:1px solid #e2e2e2;border-radius:8px;">'
        '<h3 style="margin:0 0 16px;font-size:14px;color:#666;">Issues List — toolbar '
        '(existing filters/sort applied)</h3>'
        '<div style="display:flex;gap:8px;align-items:center;margin-bottom:24px;">'
        '<span style="padding:6px 12px;border:1px solid #ccc;border-radius:6px;font-size:13px;">'
        'Filters: Status = In Progress</span>'
        '<span style="padding:6px 12px;border:1px solid #ccc;border-radius:6px;font-size:13px;">'
        'Sort: Priority ↓</span><span style="flex:1"></span>'
        '<button style="padding:6px 14px;border-radius:6px;background:#3b6;color:#fff;'
        'border:none;font-size:13px;">⬇ Export CSV</button></div></div>'
    )
    p.call("okto_pulse_add_screen_mockup", dict(
        board_id=board, entity_id=ideation, entity_type="ideation",
        title="Issues List — Export action (sync + async states)",
        description="Export action on the Issues List toolbar. Filter-aware.",
        screen_type="page", html_content=mockup_html,
    ))

    for status in ["review", "approved", "evaluating"]:
        p.call("okto_pulse_move_ideation", dict(board_id=board, ideation_id=ideation, status=status))

    ideation_state = p.call("okto_pulse_get_ideation", dict(board_id=board, ideation_id=ideation))["data"]
    ideation_state = ideation_state.get("ideation", ideation_state)
    p.call("okto_pulse_record_ambiguity_assessment", dict(
        board_id=board, subject_type="ideation", subject_id=ideation,
        idempotency_key=f"seed-ideation-ambiguity-{uuid.uuid4().hex[:12]}",
        expected_subject_version=ideation_state["version"], expected_subject_edition=ideation_state["edition"],
        expected_head_revision=0, score=0,
        summary="Sync/async threshold, CSV column set, and signed-URL expiry were resolved via Q&A before this "
                "ideation was written. No residual ambiguity.",
    ))
    p.call("okto_pulse_move_ideation", dict(board_id=board, ideation_id=ideation, status="done"))
    print(f"Ideation done: {ideation}", file=sys.stderr)

    # -------------------------------------------------------------- REFINEMENT
    step("Creating refinement")
    analysis = (
        "Investigated the actual plane/ fork (branch feature/issue-csv-export) before "
        "assuming any new endpoint was needed. Key finding: Plane already ships a "
        "complete CSV/XLSX/JSON export system — this is not a greenfield addition, it "
        "is an extension of existing, working infrastructure.\n\nExisting async export "
        "pipeline: ExportIssuesEndpoint (apps/api/plane/app/views/exporter/base.py) — "
        "creates an ExporterHistory row, calls issue_export_task.delay(...). "
        "issue_export_task (apps/api/plane/bgtasks/export_task.py) builds the Issue "
        "queryset with the same membership/role scoping as the list endpoints. "
        "upload_to_s3 generates the presigned download URL, ExpiresIn = 7 days — an "
        "established convention. ExporterHistory already has a rich_filters JSONField "
        "present on the model but unused: ExportForm has a WorkspaceLevelWorkItemFiltersHOC "
        "block stubbed out/commented, meaning Plane's own developers scaffolded "
        "filter-aware export but never wired it up.\n\nToolbar integration point: "
        "IssuesHeader (apps/web/core/components/issues/header.tsx), Header.RightItem, "
        "where the 'Add work item' button already lives."
    )
    decisions_list = [
        "SUPERSEDES ideation decision (sync/async 500-issue threshold): adopt Plane's existing always-async "
        "ExportIssuesEndpoint/issue_export_task pattern instead of building a new synchronous fast path.",
        "SUPERSEDES ideation decision (24h signed-URL expiry): adopt the existing 7-day presigned-URL expiry.",
        "SUPERSEDES ideation decision (fixed core CSV column set): reuse the existing IssueExportSerializer.",
        "NEW decision: wire the existing ExportIssuesEndpoint/issue_export_task to the Issues List view's active "
        "filter/sort state via the already-present-but-unused ExporterHistory.rich_filters field, plus add an "
        "Export action to IssuesHeader's Header.RightItem.",
    ]
    in_scope = [
        "Extend ExportIssuesEndpoint / issue_export_task to accept and apply the Issues List view's active "
        "filter/sort state via the existing (currently unused) ExporterHistory.rich_filters field",
        "Export action on the IssuesHeader toolbar (Header.RightItem), filter-aware, reusing the existing "
        "ExportForm/PrevExports toast+polling UX pattern",
        "Reuse existing IssueExportSerializer column set as-is (no new serializer)",
        "Reuse existing always-async ExportIssuesEndpoint/Celery/7-day-signed-URL pattern as-is",
        "Permission scoping consistent with the existing exporter's WORKSPACE-level role check",
    ]
    out_of_scope = [
        "A new/separate export endpoint independent of the existing ExportIssuesEndpoint",
        "A new CSV column set or new serializer",
        "A new synchronous (non-Celery) export path",
        "A new signed-URL expiry policy",
        "Other entity types (cycles, modules, pages)",
        "Configurable CSV column selection",
    ]
    refinement = p.call("okto_pulse_create_refinement", dict(
        board_id=board, ideation_id=ideation, title="CSV export — backend/frontend integration points",
        delivery_context="brownfield", analysis=analysis, decisions=decisions_list,
        in_scope=in_scope, out_of_scope=out_of_scope, labels=["feature", "csv-export", "issues"],
    ))["data"]
    refinement = (refinement.get("refinement") or refinement)["id"]
    for status in ["review", "approved", "done"]:
        p.call("okto_pulse_move_refinement", dict(board_id=board, refinement_id=refinement, status=status))
    print(f"Refinement done: {refinement}", file=sys.stderr)

    # ------------------------------------------------------------------- SPEC
    step("Deriving spec")
    spec_r = p.call("okto_pulse_derive_spec_from_refinement", dict(board_id=board, refinement_id=refinement))["data"]
    spec = (spec_r.get("spec") or spec_r)["id"]

    def add_entity(entity_type, payload):
        return p.call("okto_pulse_update_spec_entity", dict(
            board_id=board, spec_id=spec, entity_type=entity_type, operation="create",
            payload_json=payload))["data"]["entity_id"]

    fr_texts = [
        "The workspace export endpoint (POST /api/workspaces/<slug>/export-issues/, ExportIssuesEndpoint) accepts "
        "an optional `rich_filters` object mirroring the Issues List view's active filter/sort state; when "
        "present, issue_export_task applies these filters to the Issue queryset before serialization.",
        "When `rich_filters` is omitted from the request, the endpoint behaves exactly as it does today (full "
        "workspace export) — fully backward compatible.",
        "The ExporterHistory row persists the submitted `rich_filters` verbatim in its existing `rich_filters` "
        "JSONField for audit/replay.",
        "The Issues List toolbar (IssuesHeader, Header.RightItem) renders an 'Export CSV' action, visible only to "
        "a user whose role satisfies the existing exporter's WORKSPACE-level role check.",
        "Clicking the Export CSV action submits a POST to /api/workspaces/<slug>/export-issues/ with "
        "provider='csv' and a `rich_filters` payload built from the current Issues List view's active project, "
        "filter, and sort state.",
        "On submission, the frontend shows a toast confirming the export was queued, reusing the existing "
        "ExportForm success-toast pattern.",
        "The frontend polls the ExporterHistory list via the existing PrevExports interval mechanism and "
        "surfaces a download action once the matching entry's status becomes 'completed'.",
        "If the matching export job's status becomes 'failed', the frontend surfaces the failure via a distinct "
        "error/toast state rather than continuing to poll indefinitely.",
    ]
    fr_ids = [add_entity("functional_requirement", {"text": t}) for t in fr_texts]

    tr_texts = [
        "`rich_filters` MUST be validated server-side against the same filter vocabulary as `IssueFilterSet` — "
        "an unrecognized filter key is rejected with HTTP 400, never silently ignored.",
        "`issue_export_task` MUST apply `rich_filters` via the same ComplexFilterBackend/`IssueFilterSet`-"
        "compatible queryset construction already used by `IssueListEndpoint`.",
        "The existing membership/role scoping already present in `issue_export_task` remains the outer bound on "
        "every export: `rich_filters` may narrow the exported set but must never expand it.",
        "No change to `upload_to_s3`'s presigned-URL expiry (7 days) or to `IssueExportSerializer`'s field set.",
        "The Export button's visible/disabled state on the frontend MUST be derived from the same role/"
        "permission data the Issues List toolbar already uses for the adjacent 'Add work item' button.",
    ]
    tr_ids = [add_entity("technical_requirement", {"text": t}) for t in tr_texts]

    ac_texts = [
        "Given an Issues List view with an active filter and a chosen sort order, when the user clicks Export "
        "CSV, then the downloaded CSV contains only issues matching that filter, in the chosen sort order.",
        "Given a user whose role has no view access to a project's issues, when that project's Issues List is "
        "rendered, then the Export CSV action is not rendered or is disabled for that project.",
        "Given a rich_filters payload containing an unrecognized filter key, when the export request is "
        "submitted, then the server responds HTTP 400 with a structured error identifying the invalid key.",
        "Given an export job that reaches status='completed', when the frontend's next poll observes it, then "
        "the UI displays a working download action that resolves to the CSV via the presigned URL.",
        "Given an export job that reaches status='failed', when the frontend's next poll observes it, then the "
        "UI displays a failure indication visibly distinct from the in-progress/polling state.",
        "Given a request with no rich_filters field (a legacy caller), when processed, then the endpoint's "
        "behavior is identical to its pre-feature behavior (full workspace export, no regression).",
    ]
    ac_ids = [add_entity("acceptance_criterion", {"text": t}) for t in ac_texts]

    step("Adding business rules, API contract, decision, test scenarios, mockup")
    brs = [
        dict(title="rich_filters can only narrow the exported set, never widen it",
             rule="The exported issue set after applying rich_filters must always be a subset of the issues the "
                  "requesting user's role already has view access to.",
             when="A request to POST /api/workspaces/<slug>/export-issues/ includes a rich_filters payload",
             then="issue_export_task applies rich_filters as an additional AND-ed constraint on top of the "
                  "existing role-scoped queryset.",
             fr_idx=[0, 2]),
        dict(title="Unknown filter keys reject the request rather than degrading silently",
             rule="The server must not silently drop, ignore, or apply a best-effort interpretation of an "
                  "unrecognized filter key",
             when="rich_filters contains one or more keys outside the IssueFilterSet-compatible vocabulary",
             then="The endpoint responds HTTP 400 identifying the invalid key(s); no ExporterHistory row "
                  "advances past queued.",
             fr_idx=[0]),
        dict(title="Omitting rich_filters is fully backward compatible",
             rule="The absence of rich_filters must never be interpreted as an empty/zero-match filter",
             when="A request has no rich_filters field at all",
             then="The endpoint and issue_export_task behave exactly as they did before this feature.",
             fr_idx=[1]),
        dict(title="Export button visibility mirrors the existing 'Add work item' permission check",
             rule="The Export CSV action must not introduce a second, independently-maintained permission check",
             when="The Issues List toolbar (Header.RightItem) is rendered for a given user and project",
             then="Export CSV's visible/disabled state is derived from the same role/permission data source as "
                  "the adjacent 'Add work item' button.",
             fr_idx=[3]),
        dict(title="Submitted export request always reflects the current view state",
             rule="The rich_filters payload must be built from the view's live filter/project/sort state at the "
                  "moment of the click",
             when="The user clicks Export CSV on the Issues List toolbar",
             then="The request always includes provider='csv' and a rich_filters object matching the screen, and "
                  "a queued-confirmation toast is shown immediately.",
             fr_idx=[4, 5]),
        dict(title="Polling terminates on a terminal job status, never spins forever",
             rule="Polling for a specific job must stop once that job reaches a terminal status",
             when="A submitted export job is being polled via the existing PrevExports interval mechanism",
             then="On completed the UI shows a download action; on failed a distinct failure indication; either "
                  "way polling for that job ends.",
             fr_idx=[6, 7]),
    ]
    br_ids = []
    for br in brs:
        fr_idx = br.pop("fr_idx")
        r = p.call("okto_pulse_add_business_rule", dict(
            board_id=board, spec_id=spec, linked_requirements="|".join(fr_ids[i] for i in fr_idx), **br))["data"]
        br_ids.append((r.get("business_rule") or {}).get("id") or r.get("entity_id"))

    contract_r = p.call("okto_pulse_add_api_contract", dict(
        board_id=board, spec_id=spec, method="POST", path="/api/workspaces/{slug}/export-issues/",
        description="Extends the existing ExportIssuesEndpoint with an optional rich_filters payload that scopes "
                    "the export to the Issues List view's active filter/sort state.",
        request_body_json={"provider": "csv", "project": "<project_uuid>",
                            "rich_filters": {"project_id": "<project_uuid>",
                                              "filters": {"priority": ["urgent", "high"]},
                                              "order_by": "-priority"}},
        response_success_json={"status": 200, "body": {"message": "Once the export is ready you will be able to download it"}},
        response_errors_json=[{"status": 400, "condition": "rich_filters contains an unrecognized filter key"},
                               {"status": 403, "condition": "role check fails"}],
    ))["data"]
    contract_id = (contract_r.get("api_contract") or {}).get("id") or contract_r.get("entity_id")

    decision_r = p.call("okto_pulse_add_decision", dict(
        board_id=board, spec_id=spec,
        title="Extend the existing ExportIssuesEndpoint via rich_filters rather than build a new endpoint",
        rationale="Wiring the Issues List view's active filter/sort state through the existing rich_filters field "
                  "reuses working, tested infrastructure — permission scoping, Celery job lifecycle, signed-URL "
                  "generation, and the CSV serializer.",
        context="Refinement investigation found a complete, working CSV/XLSX/JSON export pipeline already "
               "exists, including an unused rich_filters JSONField and a stubbed-out filter HOC block.",
        alternatives_considered=[
            "A wholly separate view-scoped endpoint — rejected: duplicates permission scoping, Celery task, and "
            "signed-URL logic that already exists.",
            "A new synchronous fast-path for small exports — rejected: diverges from the app's one established "
            "async-export convention.",
        ],
    ))["data"]
    decision_id = (decision_r.get("decision") or {}).get("id") or decision_r.get("entity_id")

    ts_defs = [
        dict(title="Export respects active filter and sort", scenario_type="integration",
             given="A project with 10 issues, 4 of which have priority=urgent, and an Issues List view with "
                   "filter priority=urgent and sort=-created_at active",
             when="The user clicks Export CSV",
             then="The completed export's CSV contains exactly the 4 urgent issues, ordered by created_at "
                  "descending, and zero non-urgent issues"),
        dict(title="Export action hidden for a role without view access", scenario_type="negative",
             given="A user whose workspace role does not satisfy ROLE.ADMIN or ROLE.MEMBER for the target project",
             when="That user's Issues List view for the project is rendered",
             then="The Export CSV action is not present in Header.RightItem (or is rendered disabled)"),
        dict(title="Unrecognized filter key rejects the request", scenario_type="negative",
             given="A POST with rich_filters.filters containing the key \"not_a_real_filter\"",
             when="The request is processed",
             then="The server responds HTTP 400 with error=invalid_filter_key naming \"not_a_real_filter\""),
        dict(title="Completed export surfaces a working download link", scenario_type="integration",
             given="An export job in status=processing that the frontend is polling",
             when="The job transitions to status=completed with a presigned url set",
             then="The next poll surfaces a download action in the UI, downloading the CSV before the presigned "
                  "URL's 7-day expiry"),
        dict(title="Failed export surfaces a distinct error state", scenario_type="negative",
             given="An export job in status=processing that the frontend is polling",
             when="The job transitions to status=failed",
             then="The next poll surfaces a failure indication distinct from the processing/spinner state, and "
                  "polling for that job stops"),
        dict(title="Legacy request without rich_filters is unaffected", scenario_type="integration",
             given="The existing workspace-level ExportForm submits a POST with no rich_filters field",
             when="The request is processed by the modified endpoint and issue_export_task",
             then="The resulting export contains the full workspace issue set exactly as before — no regression"),
    ]
    ts_ids = []
    for i, ts in enumerate(ts_defs):
        r = p.call("okto_pulse_add_test_scenario", dict(
            board_id=board, spec_id=spec, linked_criteria=ac_ids[i], **ts))["data"]
        ts_ids.append(r.get("entity_id") or (r.get("scenario") or {}).get("id"))

    p.call("okto_pulse_add_screen_mockup", dict(
        board_id=board, entity_id=spec, entity_type="spec",
        title="Issues List — Export action (sync + async states)",
        description="Export action on the Issues List toolbar. Filter-aware.",
        screen_type="page", html_content=mockup_html,
    ))

    for status in ["review", "approved"]:
        p.call("okto_pulse_move_spec", dict(board_id=board, spec_id=spec, status=status))

    # --------------------------------------------------------------- CARDS
    step("Creating cards")
    card_backend = p.call("okto_pulse_create_card", dict(
        board_id=board, spec_id=spec, card_type="normal",
        title="Backend: wire rich_filters into ExportIssuesEndpoint / issue_export_task",
        description="Extend the existing ExportIssuesEndpoint and issue_export_task Celery task to accept, "
                    "validate, persist, and apply an optional rich_filters payload.",
        labels=["backend", "apps/api"], functional_requirement_ids=fr_ids[0:3],
    ))["data"]["card"]["id"]

    card_frontend = p.call("okto_pulse_create_card", dict(
        board_id=board, spec_id=spec, card_type="normal",
        title="Frontend: Export CSV action on Issues List toolbar",
        description="Add an Export CSV action to IssuesHeader's Header.RightItem, permission-gated, that submits "
                    "rich_filters built from the view's live state.",
        labels=["frontend", "apps/web"], functional_requirement_ids=fr_ids[3:8],
    ))["data"]["card"]["id"]

    card_backend_test = p.call("okto_pulse_create_card", dict(
        board_id=board, spec_id=spec, card_type="test",
        title="Test: backend filter/permission/compat coverage",
        description="pytest coverage for filter application, invalid-key rejection, and legacy backward "
                    "compatibility on the extended export endpoint.",
        labels=["backend", "test", "pytest"],
        test_scenario_ids=[ts_ids[0], ts_ids[2], ts_ids[5]],
    ))["data"]["card"]["id"]

    card_frontend_test = p.call("okto_pulse_create_card", dict(
        board_id=board, spec_id=spec, card_type="test",
        title="Test: frontend permission gating + polling UX",
        description="Playwright coverage for Export button visibility and the completed/failed polling states.",
        labels=["frontend", "test", "playwright"],
        test_scenario_ids=[ts_ids[1], ts_ids[3], ts_ids[4]],
    ))["data"]["card"]["id"]

    # Link business rules and the decision to their owning cards — these
    # don't get linked_task_ids at creation time the way FR/TR/AC do.
    br_card_map = [card_backend, card_backend, card_backend, card_frontend, card_frontend, card_frontend]
    for br_id, card_id in zip(br_ids, br_card_map):
        if br_id:
            p.call("okto_pulse_link_task", dict(board_id=board, target_type="rule", target_id=br_id,
                                                 card_id=card_id, spec_id=spec))
    # Technical requirements, the API contract, and the decision can only be
    # linked to a card while the spec is in draft (link_task/update_spec_entity
    # reject them on an approved-but-not-yet-content-locked spec — only the
    # business-rule link worked directly at approved).
    step("Linking TRs, API contract, and decision (draft round-trip)")
    for status in ["review", "draft"]:
        p.call("okto_pulse_move_spec", dict(board_id=board, spec_id=spec, status=status))
    tr_card_map = [card_backend, card_backend, card_backend, card_backend, card_frontend]
    for tr_id, card_id in zip(tr_ids, tr_card_map):
        p.call("okto_pulse_update_spec_entity", dict(
            board_id=board, spec_id=spec, entity_type="technical_requirement", operation="update",
            entity_id=tr_id, payload_json={"linked_task_ids": [card_id]}))
    if contract_id:
        p.call("okto_pulse_link_task", dict(board_id=board, target_type="contract", target_id=contract_id,
                                             card_id=card_backend, spec_id=spec))
    if decision_id:
        p.call("okto_pulse_link_task", dict(board_id=board, target_type="decision", target_id=decision_id,
                                             card_id=card_backend, spec_id=spec))
    for status in ["review", "approved"]:
        p.call("okto_pulse_move_spec", dict(board_id=board, spec_id=spec, status=status))

    # Both spec mockups (the one propagated from the ideation, and the one
    # added directly to the spec) must be copied onto a task card.
    mockups = p.call("okto_pulse_list_screen_mockups", dict(board_id=board, entity_id=spec, entity_type="spec"))["data"]["screens"]
    p.call("okto_pulse_copy_mockups_to_card", dict(
        board_id=board, spec_id=spec, card_id=card_frontend, screen_ids=[m["id"] for m in mockups]))

    # ---------------------------------------------------- VALIDATE + EVALUATE
    step("Validating spec")
    pf = p.call("okto_pulse_get_requirement_lint_preflight", dict(board_id=board, spec_id=spec))["data"]
    fence = pf["submission_fence"]
    p.call("okto_pulse_record_requirement_lint", dict(
        board_id=board, spec_id=spec, idempotency_key=f"seed-lint-{uuid.uuid4().hex[:12]}",
        expected_subject_version=fence["expected_subject_version"],
        expected_subject_edition=fence["expected_subject_edition"],
        expected_head_revision=fence["expected_head_revision"],
        ruleset_digest=pf["ruleset_digest"], score=0, evaluated_rule_count=19,
        summary="0 defects across all 19 evaluated requirements — clean.",
    ))

    sp = p.call("okto_pulse_get_spec", dict(board_id=board, spec_id=spec))["data"]
    p.call("okto_pulse_submit_spec_validation", dict(
        board_id=board, spec_id=spec,
        expected_validation_edition=sp["edition"], expected_spec_version=sp["version"], expected_head_revision=0,
        confidence=85, confidence_justification="Every requirement traces to a real codebase citation.",
        clarity=86, clarity_justification="Requirements are concrete with exact file:line references.",
        assertiveness=84, assertiveness_justification="Requirements state MUST/MUST NOT constraints unambiguously.",
        decidability=85, decidability_justification="Every AC has a concrete Given/When/Then with observable outcome.",
        ambiguity=18, ambiguity_justification="One minor non-blocking residue in the filters schema.",
        recommendation="approve",
    ))

    p.call("okto_pulse_submit_spec_evaluation", dict(
        board_id=board, spec_id=spec,
        breakdown_completeness=88, breakdown_justification="Every FR, TR, BR, the API contract, and the Decision "
                                                             "is traceable to the implementation cards.",
        granularity=83, granularity_justification="Backend and Frontend cards are each independently executable "
                                                    "units of work.",
        dependency_coherence=85, dependency_justification="Frontend depends on Backend; test cards depend on "
                                                            "their implementation card.",
        test_coverage_quality=85, test_coverage_justification="All 6 test scenarios have concrete Given/When/Then "
                                                                "with observable outcomes.",
        overall_score=85, overall_justification="The spec is ready for execution.",
        recommendation="approve",
    ))
    p.call("okto_pulse_move_spec", dict(board_id=board, spec_id=spec, status="in_progress"))
    print(f"Spec in_progress: {spec}", file=sys.stderr)

    # ----------------------------------------------------------------- SPRINT
    step("Creating and activating sprint")
    sprint = p.call("okto_pulse_create_sprint", dict(
        board_id=board, spec_id=spec, title="CSV export — filter-aware exporter extension",
        objective="Wire the existing ExportIssuesEndpoint/issue_export_task to the Issues List view's active "
                  "filters via rich_filters, and add the Export CSV toolbar action, per the validated spec.",
        expected_outcome="Both implementation cards and both test cards done; validator confirms real evidence "
                         "against the spec's acceptance criteria.",
        lane_type="normal",
    ))["data"]["sprint"]["id"]

    card_ids = [card_backend, card_frontend, card_backend_test, card_frontend_test]
    try:
        p.call("okto_pulse_assign_tasks_to_sprint", dict(board_id=board, sprint_id=sprint, card_ids=card_ids))
        p.call("okto_pulse_move_sprint", dict(board_id=board, sprint_id=sprint, status="active"))
    except RuntimeError as e:
        if not SPRINT_DB_WORKAROUND or "policy_subject_versioning_transaction_missing" not in str(e):
            raise
        print("    (hit the known first-sprint bug — applying the documented direct-DB workaround)", file=sys.stderr)
        data_dir = Path(args.data_dir) if args.data_dir else Path.home() / ".okto-pulse"
        db_path = data_dir / "data" / "pulse.db"
        conn = sqlite3.connect(str(db_path), timeout=10)
        conn.execute("PRAGMA busy_timeout=10000")
        cur = conn.cursor()
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        for card_id in card_ids:
            cur.execute("UPDATE cards SET sprint_id=?, updated_at=? WHERE id=?", (sprint, now, card_id))
        cur.execute("UPDATE sprints SET status=?, version = version + 1, updated_at=? WHERE id=?",
                    ("active", now, sprint))
        conn.commit()
        conn.close()

    print(f"Sprint active: {sprint}", file=sys.stderr)

    # ------------------------------------------------------------------ CARDS
    step("Completing backend + backend-test cards")
    for status in ["started", "in_progress"]:
        p.call("okto_pulse_move_card", dict(board_id=board, card_id=card_backend, status=status))
        p.call("okto_pulse_move_card", dict(board_id=board, card_id=card_backend_test, status=status))

    backend_card = p.call("okto_pulse_move_card", dict(
        board_id=board, card_id=card_backend, status="validation",
        conclusion="Implemented rich_filters validation and application in ExportIssuesEndpoint/issue_export_task. "
                   "17/17 pytest passed.",
        completeness=100, completeness_justification="All FRs/TRs for the backend card implemented and tested.",
        drift=0, drift_justification="Implementation matches the spec exactly, no deviation from plan.",
    ))["data"]["card"]

    p.call("okto_pulse_submit_task_validation", dict(
        board_id=board, card_id=card_backend, expected_subject_version=backend_card["subject_version"],
        idempotency_key=f"seed-tv-backend-{uuid.uuid4().hex[:12]}",
        confidence=92, confidence_justification="Real pytest run against the actual endpoint, 17/17 passed.",
        estimated_completeness=100, completeness_justification="All linked FRs/TRs/BRs implemented and verified.",
        estimated_drift=0, drift_justification="No deviation from the validated spec.",
        general_justification="Backend implementation matches the contract; tests pass against real infrastructure.",
        recommendation="approve",
    ))

    p.call("okto_pulse_move_card", dict(board_id=board, card_id=card_backend_test, status="validation"))
    for tid in [ts_ids[0], ts_ids[2], ts_ids[5]]:
        p.call("okto_pulse_update_test_scenario_status", dict(
            board_id=board, spec_id=spec, scenario_id=tid, status="passed",
            evidence=json.dumps({"evidence_class": "automated_test_pointer",
                                  "test_file_path": "apps/api/plane/tests/contract/app/test_export_issues_rich_filters_app.py",
                                  "test_function": "TestApplyRichFilters"})))
    p.call("okto_pulse_move_card", dict(
        board_id=board, card_id=card_backend_test, status="done",
        conclusion="Wrote apps/api/plane/tests/contract/app/test_export_issues_rich_filters_app.py covering filter "
                   "application, invalid-key rejection, and legacy backward compatibility. 17/17 pytest passed. All "
                   "3 linked test scenarios marked passed with automated_test_pointer evidence.",
        completeness=100, completeness_justification="All 3 linked test scenarios implemented and passing.",
        drift=0, drift_justification="Test coverage matches the spec exactly.",
    ))

    step("Submitting frontend card at honest under-threshold completeness (expects rejection)")
    for status in ["started", "in_progress"]:
        p.call("okto_pulse_move_card", dict(board_id=board, card_id=card_frontend, status=status))
    frontend_card = p.call("okto_pulse_move_card", dict(
        board_id=board, card_id=card_frontend, status="validation",
        conclusion="Frontend Export CSV action implemented against the contract, with one real refinement made "
                   "during implementation (rich_filters.filters uses the Issues List view's native JSON filter-tree "
                   "shape). Full workspace pnpm run check:types passes clean. E2E coverage is the next step.",
        completeness=78, completeness_justification="No e2e harness existed in the repo yet at submission time; "
                                                     "typecheck-only verification.",
        drift=5, drift_justification="Minor contract refinement during implementation, otherwise matches plan.",
    ))["data"]["card"]

    p.call("okto_pulse_submit_task_validation", dict(
        board_id=board, card_id=card_frontend, expected_subject_version=frontend_card["subject_version"],
        idempotency_key=f"seed-tv-frontend-{uuid.uuid4().hex[:12]}",
        confidence=80, confidence_justification="Typecheck passes clean; e2e evidence not yet captured at this "
                                                 "point in the run.",
        estimated_completeness=78, completeness_justification="No e2e harness existed in the repo yet — honest "
                                                               "estimate below the 80 threshold.",
        estimated_drift=5, drift_justification="One real contract refinement during implementation, otherwise "
                                               "on-plan.",
        general_justification="Implementation is real and typechecked, but e2e evidence for the two remaining "
                              "test scenarios does not exist yet at submission time.",
        recommendation="approve",
    ))
    # frontend-test card (card_frontend_test) is left `not_started` — this is
    # the "halfway point" the demo captures; see README's "What's Next".

    print("\nDone. Board reached the halfway-point state:", file=sys.stderr)
    print(f"  ideation={ideation} refinement={refinement} spec={spec} sprint={sprint}", file=sys.stderr)
    print(f"  cards: backend={card_backend} (done) backend_test={card_backend_test} (done) "
          f"frontend={card_frontend} (rejected) frontend_test={card_frontend_test} (not_started)", file=sys.stderr)


if __name__ == "__main__":
    main()
