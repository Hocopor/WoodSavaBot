# AGENTS

## Specification Authority

- The primary implementation specification is [2026-05-07-wood-sava-bot.md](A:\DevAI\Projects\WoodSavaBot\thoughts\shared\specs\2026-05-07-wood-sava-bot.md).
- All architecture, code generation, refactors, tests, and deployment work must follow that specification unless the user explicitly changes it.
- If implementation details conflict with assumptions, update the specification or ask the user before diverging.
- Treat the persistent binding `user -> source platform -> Telegram topic -> current flow step` as mandatory.
- Do not replace this with in-memory-only state.
- The product does not require a full chat archive, but it does require durable routing and flow state across restarts.

## Live Plan

- The live plan file is always `LIVE_PLAN.md`.
- Do not create alternative live plan files.
- `LIVE_PLAN.md` must exist at all times during active work.
- Before substantial work, update `LIVE_PLAN.md`.
- After each substantial completed step, update `LIVE_PLAN.md` again.

## Live Plan Format

- Use these status markers everywhere in `LIVE_PLAN.md`:
  - `[x]` completed
  - `[~]` in progress or partially completed
  - `[]` not completed
- Keep phases, tasks, blockers, next steps, and durable notes in `LIVE_PLAN.md`.
- The file must always show the real current state of work.

## Long-Lived Rules

- Do not delete or replace `LIVE_PLAN.md` unless the user explicitly says to do so.
- If the user changes topic, extend the existing plan instead of replacing it.
- If the user says `otmenyaem` or `ubiraem iz plana`, remove that item or mark it canceled.
- Temporary topic switches are not cancelation.

## Durable Notes

- Record critical findings, priorities, blockers, sequencing decisions, and architecture decisions in `LIVE_PLAN.md`.
- Preserve the difference between:
  - stabilizing the current implementation
  - future redesign work
- Re-check `LIVE_PLAN.md` before implementation so work follows the latest agreed direction.
