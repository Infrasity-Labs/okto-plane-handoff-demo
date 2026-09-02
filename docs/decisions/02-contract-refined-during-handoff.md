# Decision: rich_filters wire format refined during frontend implementation

**Stage:** Backend implementation → Frontend implementation (post-handoff)
**Status:** Adopted, both sides reconciled

## Context

The Backend card's first implementation routed `rich_filters.filters`
through Plane's existing `LegacyToRichFiltersConverter`, assuming the
Issues List view's filter state used Plane's legacy flat filter-key
vocabulary (`state`, `priority`, `assignees`, ...). This shipped, was
tested (6 passing tests at the time), and the Backend card reached `done`.
The API contract — including this assumption — was sent to
`frontend-agent` as the Nexus handoff artifact.

While implementing the Frontend card against that contract, investigation
of the Issues List view's actual filter store
(`packages/shared-state/src/store/work-item-filters/adapter.ts`) found it
already produces the JSON filter-*tree* shape `ComplexFilterBackend`
natively consumes (e.g. `{"and": [{"priority__in": "urgent,high"}]}`).

## Decision

Refine the backend to consume the tree shape directly. The
`LegacyToRichFiltersConverter` step was removed; `_apply_rich_filters` now
validates and applies the tree via the same `ComplexFilterBackend` call the
live Issues List endpoint already uses.

## Consequence

- The backend implementation was updated in place (see
  `docs/walkthrough.md` for the exact commit references).
- The frontend needs **zero client-side mapping** — it forwards
  `issueFilters.richFilters` unmodified.
- The refinement was reported back through the real Nexus handoff result
  (`handoff_complete`'s payload), so the audit trail reflects what was
  actually agreed and delivered, not only what was originally proposed —
  a live example of Nexus's handoff record staying accurate as
  understanding improves mid-implementation.
