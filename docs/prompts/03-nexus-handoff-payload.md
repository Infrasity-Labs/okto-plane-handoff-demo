# Stage 3 — Nexus handoff: the actual artifact sent backend → frontend

The real `handoff_create` payload (`backend-agent` → `frontend-agent`,
target strategy `direct`, visibility `public`), verbatim except for
truncation noted:

```json
{
  "summary": "Backend done: ExportIssuesEndpoint now accepts rich_filters. Implement the Export CSV toolbar action against this contract.",
  "pulse_board_id": "d72390b0-43d9-4448-883b-e5937f8e4454",
  "pulse_spec_id": "e4720b70-f539-44fa-8f2f-b4cf140d9f3a",
  "pulse_backend_card_id": "20960449-5812-4e63-a3c6-f31b76996396",
  "pulse_frontend_card_id": "bb89c680-ce53-4638-8d0c-ee7e3253fa90",
  "api_contract": {
    "method": "POST",
    "path": "/api/workspaces/{slug}/export-issues/",
    "request_body": {
      "provider": "csv",
      "project": ["<project_uuid>"],
      "multiple": false,
      "rich_filters": {
        "project_id": "<project_uuid>",
        "filters": { "priority": ["urgent", "high"], "state": ["<state_uuid>"] },
        "order_by": "-priority"
      }
    },
    "response_success": { "status": 200, "body": { "message": "Once the export is ready you will be able to download it" } },
    "response_errors": [
      { "status": 400, "condition": "unrecognized filter key in rich_filters.filters", "body": { "error": "invalid_filter_key", "detail": "string" } }
    ]
  },
  "notes": "rich_filters.filters uses the SAME legacy field names the Issues List filter UI already has in its local filter state ... no new mapping needed on the frontend, just forward the view's existing filter object. Async only (no sync path): poll ExporterHistory via the existing PrevExports 3000ms interval pattern for status completed/failed.",
  "commit": "8b12340acf",
  "files_changed": [
    "apps/api/plane/app/views/exporter/base.py",
    "apps/api/plane/bgtasks/export_task.py",
    "apps/api/plane/tests/contract/app/test_export_issues_rich_filters_app.py"
  ]
}
```

The `notes` field's description of `rich_filters.filters`' shape was
refined during frontend implementation — see
`docs/decisions/02-contract-refined-during-handoff.md` for what was
actually simplest, and how the `handoff_complete` result carried that
refinement forward in the same audit trail.
