# Prompts

The actual prompt used at each stage of the real run, in order. Not
reconstructed after the fact — these are what was typed to drive the Pulse
and Nexus MCP tool calls that produced `demo-state/`.

| # | Prompt | Stage | Agent |
|---|---|---|---|
| 01 | [`01-ideation-ambiguity-killer.md`](01-ideation-ambiguity-killer.md) | Ideate — resolve sync/async threshold, CSV column set, signed-URL expiry via Q&A before writing anything down | Spec Agent |
| 02 | [`02-refinement-investigation.md`](02-refinement-investigation.md) | Refine — real codebase investigation of the existing export pipeline, informing the design | Spec Agent |
| 03 | [`03-nexus-handoff-payload.md`](03-nexus-handoff-payload.md) | Handoff — the API contract as the artifact passed backend → frontend through Nexus | Backend Agent → Frontend Agent |

Only three stages produced a standalone prompt worth keeping as an
artifact — the rest of the run (spec authoring, sprint creation, card
implementation, task validation) followed Pulse's and Nexus's own MCP
tool-call protocol directly rather than a scripted prompt. See
[`../walkthrough.md`](../walkthrough.md) for the full stage-by-stage trace,
including those.
