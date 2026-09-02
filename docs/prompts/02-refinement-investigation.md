# Stage 2 — Refinement: real codebase investigation

The actual prompt dispatched to an Explore subagent before writing the
refinement's `analysis`/`decisions` fields. Refinement is defined as
"research, not paraphrasing" — this is what made it research.

```
Investigate the Plane project management repo at
/Users/apple/Infrasity/okto-plane-handoff-demo/plane for facts needed to
design a CSV export feature for the Issues List view. I need concrete,
cited findings (file path + line numbers / symbol names), not guesses.
Report on:

1. Existing issue-list endpoint: find the DRF view/viewset that serves the
   issue list for a project (apps/api), how it parses filter/sort query
   params, and what permission classes/checks it uses.
2. Existing async job pattern: find how Plane already does "queue a Celery
   task, return something the client polls" -- e.g. any existing
   export/import feature, bulk operations, or async report generation.
   Cite the Celery task definition and how the client learns the job is
   done.
3. Existing signed-URL / file-download pattern: find how Plane already
   generates a signed download link (S3/MinIO) for user-facing downloads --
   cite the exact helper/utility function and its usage site.
4. Issue model + serializer: find the Issue model fields corresponding to
   id, title, status, priority, assignee, labels, due date, created/updated
   -- cite the model file and serializer.
5. Frontend Issues List view: find the component in apps/web that renders
   the Issues List toolbar (where filters/sort controls live), so a new
   Export button has a real home. Cite the file and component name.
6. Existing toast/notification pattern in apps/web for the kind of
   "processing... then ready" UX (any existing polling+toast pattern for a
   long-running action).

For each finding, give: file path, relevant line numbers or symbol name,
and a one-sentence summary of what it does. If something doesn't exist
(e.g., no existing async export pattern), say so explicitly rather than
guessing -- that's a valid and useful finding too.
```

This single investigation found the entire pre-existing export pipeline
described in `docs/architecture.md` and directly caused
`docs/decisions/01-ideation-superseded-by-refinement.md`.
