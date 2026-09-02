# Decision: three ideation assumptions superseded after real codebase investigation

**Stage:** Refinement
**Status:** Adopted (user-confirmed)

## Context

The ideation (`CSV export for filtered issue views`) was written before any
code was read, and assumed:

1. A new synchronous export path for small result sets
2. A 24-hour signed download-link expiry
3. A new, fixed core CSV column set

The refinement's mandatory investigation step read the actual forked
`plane/` source and found Plane already ships a complete async CSV/XLSX/JSON
export pipeline (`ExportIssuesEndpoint` → `issue_export_task` → presigned
S3/MinIO URL → `PrevExports` polling UI) — including an **unused
`rich_filters` field** on `ExporterHistory` and a stubbed-out filter-picker
block (`WorkspaceLevelWorkItemFiltersHOC`) in the frontend's `ExportForm`.
Clear evidence Plane's own team scaffolded this exact integration and never
finished it.

## Decision

All three assumptions were surfaced to the user as an explicit either/or
choice rather than silently overridden. The user chose, in all three cases,
to adopt Plane's existing convention instead of the ideation's assumption:

| Ideation assumed | Adopted instead | Why |
|---|---|---|
| New sync export path for small results | Always-async, matching the existing pipeline | A small export still completes within the existing 3s polling interval; a second code path duplicates a working one for no user benefit |
| 24h signed-URL expiry | Existing 7-day expiry (`upload_to_s3`) | Consistency with the one signed-URL convention already used elsewhere; a queued export may sit unopened for a while |
| New fixed core column set | Existing `IssueExportSerializer` as-is | Already richer (identifier, project/state names, assignee/label names, dates, estimates, cycles, modules) and already CSV-wired |

## Consequence

The feature's real scope shrank from "build a new export system" to "wire
the Issues List view's live filter state into the existing exporter via the
already-present `rich_filters` field." Less new code, more brownfield-correct.
