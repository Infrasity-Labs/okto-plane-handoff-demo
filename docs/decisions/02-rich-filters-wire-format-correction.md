# Decision: rich_filters wire format corrected mid-implementation

**Stage:** Backend implementation → Frontend implementation (post-handoff)
**Status:** Adopted, both sides reconciled

## Context

The Backend card's first implementation assumed `rich_filters.filters` used
Plane's *legacy* flat filter-key vocabulary (`state`, `priority`,
`assignees`, ...) and routed it through the existing
`LegacyToRichFiltersConverter` before applying it. This shipped, was tested
(6 passing tests), and the Backend card was marked `done`. The real API
contract — including this assumption — was then sent to `frontend-agent` as
the Nexus handoff artifact.

While implementing the Frontend card against that contract, investigation of
the Issues List view's actual filter store
(`packages/shared-state/src/store/work-item-filters/adapter.ts`) found it
already produces the JSON filter-*tree* shape `ComplexFilterBackend` natively
consumes (e.g. `{"and": [{"priority__in": "urgent,high"}]}`) — not the legacy
flat shape the backend assumed.

## Decision

Reopen and correct the backend rather than force the frontend to convert
tree-shaped data back into a legacy shape it doesn't natively have. The
`LegacyToRichFiltersConverter` step was removed; `_apply_rich_filters` now
validates and applies the tree directly via the same `ComplexFilterBackend`
call the live Issues List endpoint already uses.

## Consequence

- Backend commit amended (not a new commit rewriting history — see
  `docs/walkthrough.md` for the exact commit hashes).
- The frontend needs **zero client-side mapping** — it forwards
  `issueFilters.richFilters` unmodified.
- The correction was reported back through the real Nexus handoff result
  (`handoff_complete`'s payload), not just in a commit message — so the
  audit trail reflects what was actually agreed and delivered, not only
  what was originally promised.
