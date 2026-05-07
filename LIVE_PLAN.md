# LIVE_PLAN

## Phase 0 - Alignment And Control
- [x] Confirm and lock the product specification, including mandatory persistent binding `user -> platform -> topic -> flow step`
- [x] Add repository-wide implementation rules so future work always follows the approved specification
- [x] Record durable architecture and sequencing decisions for the full implementation

## Phase 1 - Project Bootstrap
- [x] Choose implementation stack and dependency set for `Ubuntu 24`
- [x] Create base project structure for adapters, domain, storage, config, and tests
- [x] Add environment configuration template for all platform tokens and IDs
- [x] Add structured logging, startup validation, and health-oriented bootstrap checks

## Phase 2 - Persistent State And Domain Core
- [x] Design the runtime persistence model for `UserSession` and routing metadata
- [x] Implement durable storage for `user -> platform -> topic -> flow step`
- [x] Implement conversation state machine for flows `1`, `2`, and `3`
- [x] Implement shared message normalization model for text, photos, documents, and service events
- [x] Implement idempotent state transitions for start, cancel, home, and completion

## Phase 3 - Telegram Admin Hub
- [x] Implement admin supergroup integration
- [x] Implement forum-topic creation and topic reuse
- [x] Implement inbound forwarding into customer topics
- [x] Implement manager-to-customer routing from topic messages
- [~] Implement service notices for unsupported content, delivery failures, and operator-facing flow context

## Phase 4 - Telegram Customer Bot
- [x] Implement `Telegram` polling intake
- [x] Implement pre-start guidance text strategy and `/start` behavior
- [x] Implement welcome message, main menu, and visible `Cancel` / `Home` controls
- [x] Implement full customer flows with `Вопрос: ответ` forwarding
- [x] Implement customer attachment intake and forwarding

- [x] Add persistent `Back` / `Next` questionnaire navigation with answer previews and admin-topic cleanup for replaced answers
- [x] Reduce Telegram customer-chat visual noise by replacing repeated welcome messages with a single rotating `На главную` action message during operator dialogue

## Phase 5 - VK Adapter
- [x] Implement `VK` long poll intake
- [x] Implement platform-specific start UX with the approved first-interaction behavior
- [x] Implement the same menu and flow logic through the shared engine
- [~] Implement inbound attachment handling and outbound manager replies
- [~] Verify edge cases caused by `VK` platform limitations

## Phase 6 - MAX Adapter
- [~] Confirm approved-bot capabilities in the active `MAX` environment
- [x] Implement `MAX` polling or equivalent supported intake path
- [x] Implement start behavior, flows, attachments, and manager reply routing
- [~] Verify fallback behavior for unsupported message and media combinations

## Phase 7 - Cross-Platform Reliability
- [~] Add retry strategy for transient API failures
- [~] Add restart-safe resume behavior for all pollers
- [] Add duplicate-event protection and idempotent delivery guards
- [~] Add explicit operator-visible error reporting into Telegram topics
- [] Verify that no restart loses `user -> topic -> step` binding

## Phase 8 - Testing
- [~] Add unit tests for flow engine, persistent state transitions, and operator-facing flow notices
- [x] Add regression coverage for questionnaire backtracking, answer replacement, and admin-topic cleanup
- [] Add adapter-level tests for topic routing and delivery mapping
- [] Add integration checks for `Telegram`, `VK`, and `MAX` critical paths
- [] Add restart/recovery test coverage for durable routing state
- [] Run acceptance verification against the approved specification


## Phase 9 - Deployment And Operations
- [~] Prepare `Ubuntu 24` deployment layout
- [x] Add `systemd` service files and restart policy
- [x] Add `.env` example and production configuration checklist
- [~] Add runbook for initial bring-up, permissions, and smoke tests
- [~] Add operational notes for polling, logs, and troubleshooting

## Phase 10 - Final Acceptance
- [] Validate all acceptance criteria from the specification
- [] Validate manager reply behavior from Telegram topics to every supported platform
- [] Validate attachment behavior and graceful degradation per platform
- [] Document remaining external risks, especially `MAX` approval/capability constraints
- [] Prepare the project for production launch

## Blockers
- [] `MAX` bot approval status and exact API/media capabilities must be verified at implementation time

## Next Steps
- [x] Update `AGENTS.md` so all future implementation follows the approved specification and this live plan
- [~] Deepen reliability, adapter verification, operator-visible context, and production hardening on top of the implemented core
- [x] Notify Telegram managers which menu branch the customer selected before the first flow question

## Durable Notes
- The source of truth for requirements is [2026-05-07-wood-sava-bot.md](A:\DevAI\Projects\WoodSavaBot\thoughts\shared\specs\2026-05-07-wood-sava-bot.md).
- No full chat archive is required as a product feature.
- Minimal persistent runtime state is mandatory.
- The mandatory durable binding is `user -> source platform -> Telegram topic -> current flow step`.
- The admin workspace is a single `Telegram` supergroup with forum topics.
- Any manager message in a customer topic is treated as a reply to that customer.
- When a customer chooses flow `1`, `2`, or `3`, the admin topic should receive an explicit notice about that selection so managers can immediately see the chosen branch.
- The branch-selection notice is now emitted before the first question and covered by automated tests.
- Telegram topic self-healing now also treats "accepted but delivered outside the requested topic" as a broken-topic condition.
- Backtracking UX requires persistent per-step answer state plus admin-message IDs so replaced answers can be deleted from Telegram topics after edits.
- Default runtime logging is now intentionally reduced to `ERROR`, including `httpx` and `httpcore`, to keep production journals focused on failures.
- During free-form customer-to-operator dialogue in Telegram, repeated welcome messages should be avoided; instead the bot should keep at most one active `На главную` helper message and refresh it as new customer messages arrive.
- Telegram free-form dialogue now uses a rotating inline `На главную` helper instead of re-sending the full welcome text after every arbitrary customer message.
- Current codebase now includes a runnable Python service skeleton with polling adapters for `Telegram`, `VK`, and `MAX`.
- Remaining highest-risk area is real API verification for uploads, media edge cases, and production-specific platform quirks.
