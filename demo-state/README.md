# Demo State

Real exports from the completed run — not mockups, not hand-written
fixtures. Each file is a direct export of live Pulse/Nexus state at the
point the run was captured (`2026-09-02`, roughly the halfway point — see
the root [README's What's Next](../README.md#whats-next)).

| File | What it is |
|---|---|
| [`board-export.json`](board-export.json) | The Pulse board: ideation/refinement/spec/sprint lineage and all 4 cards with their real statuses |
| [`spec-export.json`](spec-export.json) | The full validated spec — 8 functional requirements, 5 technical requirements, 6 acceptance criteria, 6 business rules, 1 API contract, and the formal Decision entity, every one linked to a real task card |
| [`nexus-event-log.json`](nexus-event-log.json) | The real Nexus handoff: `handoff_create` → `handoff_claim` → `handoff_complete`, with the actual result payload the frontend agent reported back |
| [`nexus-workspace-config.json`](nexus-workspace-config.json) | The registered Nexus agent roster (`spec-agent`, `backend-agent`, `frontend-agent`, `validator-agent`, plus the session's fallback `local-agent` identity) |

## How to view it

No login, key, or running server needed — these are plain JSON. Open them
directly, or:

```bash
python3 -m json.tool demo-state/board-export.json
```

## Reproducing this state on a fresh install

These files are a read-only **export**, not an importable snapshot —
Pulse has no "import a board" tool, so a fresh `okto-pulse serve` boots
with an empty default board and a fresh Nexus has no registered agents or
event log. To get a fresh install's *own* Pulse board to this same
visible state, run [`scripts/01_seed_pulse_board.py`](../scripts/01_seed_pulse_board.py)
— see the root README's [Quickstart](../README.md#quickstart) for the
exact command. It replays the same final field values captured here
through the real Pulse MCP tool calls.

The Nexus side (agent registration, the handoff event log) is not
scripted — register your own agents and run the real handoff yourself per
[`docs/walkthrough.md`](../docs/walkthrough.md), the same as the original
run did. A scripted replay of a handoff between agents that were never
actually connected wouldn't be a real one.
