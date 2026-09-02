# okto-plane-handoff-demo

One real feature. Two agent roles. A spec-gated pipeline that decides what's
built and what "done" means, plus a coordination layer that decides who gets
to touch it, and when.

A small real feature, built on a real codebase, governed end-to-end by Okto
Pulse and Okto Nexus together.

**Status: ~50% done, real, and left mid-flight on purpose.** This is a
genuine live-run trace, not a staged demo — see [Known gaps](#known-gaps--what-a-next-session-should-do)
for exactly where it stops and what's left to finish it.

## About Okto Pulse + Okto Nexus

**Okto Pulse** is a spec-gated SDLC pipeline for AI coding agents — it
doesn't just track tasks, it governs the path from a raw idea to a
validated, evidence-backed "done": ideation → refinement → spec →
validation gate → sprint → cards → task validation.

**Okto Nexus** is a local-first coordination layer for teams running
multiple AI coding agents — it doesn't write code or specs, it governs how
agents claim work, hand it to each other, and leave an auditable trail of
who did what and when.

Independently, either product answers half the question "what does it look
like when AI agents build real software." Together: a spec-gated card,
hand off between two independently-running agents, with an audit trail
proving the handoff happened and the evidence that satisfied the validation
gate.

## The Problem

Teams evaluating "AI agents for software delivery" get stuck choosing
between two half-answers:

1. **Governance tools track work but don't touch coordination** — a backlog
   of AI-generated tickets with no structural guarantee two agents don't
   collide, or that a handoff between them is real and auditable.
2. **Coordination tools let agents talk but have no gated proof of "done"**
   — agents can pass work to each other, but nothing stops a spec-gap or an
   untested claim from shipping.
3. **Ambiguity gets silently absorbed into code** — an agent's first
   reading of a feature request becomes an assumption, and the assumption
   becomes a bug, discovered only when a human reads the diff.
4. **"It works" claims aren't verified against running infrastructure** —
   unit tests that mock the interesting part pass while the real system,
   run end-to-end, does not.

## How It Works

The feature: wire Plane's Issues List view to its own already-existing
(but unused) async CSV export pipeline, filtered to whatever the view's
active filters/sort currently show.

- **Pulse** owns *what to build*: the ideation's assumptions get corrected
  by a real refinement investigation, the spec is validated against five
  deterministic quality dimensions before any code is trusted, and every
  card's completion claim goes through an independent task-validation gate.
- **Nexus** owns *who's allowed to act and when*: the backend agent hands
  off to the frontend agent with the real API contract as the artifact,
  and the handoff's claim/complete trail is a real, replayable event log —
  not a chat message.

The workflow, as it actually ran:

1. Spec Agent ideates in Pulse, runs ambiguity-killer Q&A before writing
   anything down
2. Refinement investigates the real forked codebase — finds Plane already
   has the export pipeline, supersedes 3 of the ideation's assumptions
3. Spec is authored, KG-checked, and pushed through Pulse's real five-
   dimension validation gate (confidence/clarity/assertiveness/
   decidability/ambiguity) — passes at 85/86/84/85/18
4. Sprint created, 4 cards (Backend, Frontend, 2 Test), dependency-linked
5. Backend Agent implements, runs 17 real tests inside the project's own
   docker-compose stack, card reaches `done`
6. Backend Agent hands off to Frontend Agent through Nexus — the API
   contract as the artifact, a real `handoff_create` → `handoff_claim` →
   `handoff_complete` trail
7. Frontend Agent implements against the contract, **finds and reports a
   real correction** to what the contract claimed, in the handoff result
8. Frontend card is **honestly rejected** by Pulse's task-validation gate —
   no e2e harness existed yet, so completeness (78) came in under the
   board's 80% threshold, and the gate enforced that over the reviewer's
   own "approve" recommendation
9. Closing the gap for real: Playwright added from scratch, a genuine bug
   found and fixed running the pipeline end-to-end against live
   infrastructure (not mocks) — then the run stops on a real, unresolved
   environment blocker (see [Known gaps](#known-gaps--what-a-next-session-should-do))

## Prerequisites

- Python 3.11+, `pip install okto-pulse` and `pip install "okto-nexus[serve]"`
- Docker + Docker Compose (for Plane's own stack: Postgres, Redis, MinIO,
  RabbitMQ)
- Node.js 18+, `pnpm`
- Two separate agent connections (or one client holding both MCP server
  URLs simultaneously, as this run did)

## Quickstart

```bash
git clone <this-repo>
cd okto-plane-handoff-demo
./scripts/setup.sh
```

This brings up Plane's own docker-compose stack, then starts Pulse and
Nexus pointed at the embedded `plane/` checkout. See `docs/walkthrough.md`
for the exact commands used to reproduce the bootstrap test data and the
(currently blocked) e2e run.

## Stages (as actually run)

0. **Setup** — fork, scaffold, bring up Plane's stack, register Pulse/Nexus
   agent identities
1. **Ideate** (Pulse) — ambiguity-killer Q&A before writing anything down
   (`docs/prompts/01-ideation-ambiguity-killer.md`)
2. **Refine** (Pulse) — real codebase investigation, 3 assumptions
   superseded (`docs/prompts/02-refinement-investigation.md`,
   `docs/decisions/01-ideation-superseded-by-refinement.md`)
3. **Spec** (Pulse) — authored, validated (5-dimension gate), evaluated
4. **Sprint** (Pulse) — 4 cards created and dependency-linked
5. **Backend implementation** — real code, real tests, real `done`
6. **Handoff** (Nexus) — backend → frontend, contract artifact
   (`docs/prompts/03-nexus-handoff-payload.md`)
7. **Frontend implementation** — real code, one real contract correction
   reported back through the handoff
   (`docs/decisions/02-rich-filters-wire-format-correction.md`)
8. **Validation gate: honest rejection** — completeness 78 < 80
   (`docs/decisions/03-pulse-gate-rejection-accepted-not-bypassed.md`)
9. **Closing the gap** — real bug found + fixed running e2e; stopped on an
   unresolved 429 (`docs/decisions/04-e2e-blocker-accepted-unresolved.md`)

## Where to Find Artifacts

- `demo-state/board-export.json`, `demo-state/spec-export.json` — real
  Pulse board/spec state (FRs, TRs, ACs, BRs, API contract, decisions, card
  status)
- `demo-state/nexus-event-log.json`,
  `demo-state/nexus-workspace-config.json` — the real Nexus handoff trail
- `docs/walkthrough.md` — stage-by-stage instructions and the full, honest
  MCP call trace, including dead ends
- `docs/prompts/` — the actual prompt for each stage
- `docs/decisions/` — real decisions made, including the ones that didn't
  go as planned
- `plane/` — the forked app itself (branch `feature/issue-csv-export`,
  4 real commits, also pushed standalone to
  [yuvicodesgit/plane](https://github.com/yuvicodesgit/plane))

## Known gaps / what a next session should do

This is deliberately not finished — pick any of these up:

- [ ] **Clear the stuck 429** (`plane/apps/api/plane/authentication/rate_limit.py`,
      `AuthenticationThrottle`, cache-backed via Redis) and get
      `plane/apps/web/e2e/export-csv.spec.ts` actually green against the
      live stack.
- [ ] Move the Frontend card (`bb89c680-ce53-4638-8d0c-ee7e3253fa90`) back
      to `in_progress` in Pulse, resubmit task validation once real e2e
      evidence exists.
- [ ] Update the 2 frontend test scenarios with real Playwright evidence,
      then move the Frontend test card to `done`.
- [ ] Move the Sprint and Spec to `done` once both cards are closed.
- [ ] Consider the stretch goal: open the real PR to `makeplane/plane` —
      the feature work, plus two independent upstream `docker-compose.yml`
      fixes found along the way (see `docs/architecture.md`), once the
      above is closed out.

## Conclusion

Built on [Okto Pulse](https://github.com/OktoLabsAI/okto-pulse) and
[Okto Nexus](https://github.com/OktoLabsAI/okto-nexus), both OktoLabs
products. Structural separation between what gets built, what counts as
proof it works, and who's allowed to touch it next — enforced by the tools
themselves, not by trusting the agent's own account of its work.
