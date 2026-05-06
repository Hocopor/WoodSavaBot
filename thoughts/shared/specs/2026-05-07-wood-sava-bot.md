# Wood_Sava_Bot Specification

## Executive Summary
`Wood_Sava_Bot` is a multi-platform lead intake bot for `Telegram`, `VK` community messages, and `MAX`. It collects customer requests through fixed conversational flows, forwards all user traffic into a single admin `Telegram` supergroup with forum topics, and lets managers reply to users from that supergroup on behalf of the bot.

The bot will run on `Ubuntu 24` and initially use `long polling` instead of webhooks because there is no domain yet. The core business goal is to capture incoming furniture requests from three platforms, keep the customer experience simple, and unify manager work in one place.

## Problem Statement
The business needs a single bot system that:
- accepts incoming customer requests from `Telegram`, `VK`, and `MAX`
- guides customers through one of three predefined request scenarios
- forwards all customer messages, answers, and attachments into one manager workspace
- allows managers to respond to customers without exposing personal manager accounts

Today, without this system, requests from different platforms would be fragmented, harder to process, and easier to lose. A unified intake and operator workflow reduces response friction and simplifies lead handling.

## Success Criteria
- A customer from any supported platform can start the bot and complete one of the three flows.
- Every started conversation creates one dedicated topic in the admin `Telegram` supergroup.
- All customer messages during and after the questionnaire are forwarded into that topic.
- Any manager message written inside the customer topic is sent back to the correct customer on the original platform.
- The bot always shows a path back to the main menu through `Cancel` during flows and `Home` after completion.
- The system works on `Ubuntu 24` using `long polling` for all supported platforms that allow it.

## Stakeholders
- Customers requesting furniture calculation or consultation
- Managers answering customers from the admin `Telegram` supergroup
- Group administrators maintaining the supergroup and bot permissions
- Business owner monitoring lead handling

## User Personas
### Customer
- Non-technical or low-technical user
- May not know how bots work
- Needs a highly visible and obvious start action
- May send plain text, photos, or files instead of perfectly formatted answers

### Manager
- Works inside a single `Telegram` supergroup
- Needs all inbound requests in one place
- Replies directly inside the customer topic
- Should not need to know the customer's original platform-specific technical details

### Administrator
- Configures bot tokens, polling, and group permissions
- Ensures the bot has access to the admin supergroup and forum topics

## Core Product Decisions
- This is a new project built from scratch.
- No full conversation archive is required as a business feature.
- The system must store minimal persistent technical state required for operation, such as platform user ID, current flow step, and `Telegram` topic ID.
- The persistent binding `user -> source platform -> Telegram topic -> current scenario step` is mandatory and must survive service restarts and deployments.
- Any user message during a questionnaire is treated as the answer to the current question.
- Any manager message in the customer's `Telegram` topic is treated as a reply to that customer.
- Access control for manager replies is based on membership in the admin supergroup; no separate manager list is required.
- No explicit "close request" workflow is required.
- Texts should remain as provided by the customer, with only obvious spelling and punctuation fixes allowed.

## Supported Platforms
### Telegram
- Customer-facing bot in private chat
- Uses `long polling`
- Must show onboarding text in the pre-start chat screen telling the user to press `Start` or send `/start`
- Uses `Telegram` Bot API

### VK
- Customer-facing bot in `VK` community messages
- Uses `Bots Long Poll`
- The platform startup experience differs from `Telegram`; after the user opens the community dialog and sends the first allowed interaction, the bot should show the `Start` button and continue with the same flow

### MAX
- Customer-facing bot in `MAX`
- Must follow current `MAX` bot platform rules and moderation requirements
- Uses the platform's available polling-based intake if supported for the approved bot setup
- Startup should rely on the platform's native `Start/Begin` affordance where available

## Research Findings
- `Telegram` Bot API supports forum topics in supergroups, including topic creation via `createForumTopic` and message sending into a topic using `message_thread_id`. The bot must be an admin in the supergroup and have rights to manage topics.
- `MAX` bot availability currently depends on registration and moderation for eligible Russian legal entities or sole proprietors, so production launch depends on this organizational prerequisite in addition to technical implementation.
- `VK` community messaging startup UX is platform-specific and cannot perfectly mirror `Telegram`; the approved product decision is to show the bot's start keyboard at the first available interaction point.

Sources:
- `Telegram Bot API`: https://core.telegram.org/bots/api
- `MAX` user help: https://help.max.ru/help/bots/kak-najti-i-dobavit-sebe-chat-bota-v-max
- `MAX` developer docs: https://dev.max.ru/docs/chatbots/bots-create

## User Journey
### First Contact
1. User opens the bot or community dialog on `Telegram`, `VK`, or `MAX`.
2. User sees the platform-appropriate start affordance.
3. User presses `Start` or sends `/start` where supported.
4. Bot creates or reuses the admin-side topic for this user.
5. Bot sends the welcome message and shows three main buttons: `1️⃣`, `2️⃣`, `3️⃣`.

### Welcome Message
```text
Здравствуйте! Рады видеть вас в Wood - Sava.👩‍💻
1️⃣ - Вы хотите рассчитать стоимость готового изделия
2️⃣ - У Вас готовый проект от дизайнера
3️⃣ - Сделать мебель по индивидуальным размерам
```

### Flow 1: Ready-Made Product Cost Calculation
Bot asks, in order:
1. `Артикул / название модели и фото (если есть).`
2. `Какие размеры (длина×ширина×высота).`
3. `Материал корпуса и фасада (лдсп, мдф, массив).`
4. `Цвет / декор.`
5. `Фурнитура (ручки, доводчики, подсветка).`
6. `Нужна ли доставка и сборка.`
7. `Пожалуйста, напишите имя и номер телефона для связи, менеджер с Вами свяжется в ближайшее время.😊`

After final answer:
- bot sends `Спасибо, ожидайте звонка😊`
- bot shows a `Home` button that returns the user to the welcome message

### Flow 2: Designer Project
Bot asks, in order:
1. `В каком формате проект (PDF, SketchUp, развертки)?`
2. `Есть ли спецификация материалов и фурнитуры?`
3. `Размеры по месту (погрешности стен/пола).`
4. `Нужны ли изменения в раскрое или фурнитуре?`
5. `Требуется ли авторский надзор за сборкой.`
6. `Пожалуйста, напишите имя и номер телефона для связи, менеджер с Вами свяжется в ближайшее время.😊`

After final answer:
- bot sends `Спасибо, ожидайте звонка😊`
- bot shows a `Home` button that returns the user to the welcome message

### Flow 3: Custom Furniture by Individual Dimensions
Bot sends:
`Пожалуйста, напишите имя и номер телефона для связи, менеджер с Вами свяжется в ближайшее время.`

After answer:
- bot sends `Спасибо, ожидайте звонка😊`
- bot shows a `Home` button that returns the user to the welcome message

### Cancel Behavior
- During every active questionnaire step, the user must always have a visible `Cancel` button.
- Pressing `Cancel` returns the user to the welcome message and resets the current flow state.

### Free-Form User Messages
- If the user sends arbitrary text during a flow, it is treated as the answer to the current question.
- If the user sends arbitrary text outside a flow after starting, it must still be forwarded to the admin topic as a general inbound message.

## Admin Supergroup Workflow
### Topic Creation
- One dedicated topic must be created in the admin `Telegram` supergroup for each unique user conversation after the user starts the bot.
- Topic title format:
  - `Платформа,ник,имя пользователя`
  - Example: `ТГ,Олег,@mako`

### Topic Naming Rules
- Platform prefix must be abbreviated:
  - `ТГ` for `Telegram`
  - `ВК` for `VK`
  - `МАКС` for `MAX`
- If a username is unavailable on the source platform, the bot should substitute the best available identifier, such as display name or a service placeholder like `без_ника`.
- If both nickname and display name are incomplete, the bot should still create a stable readable title using available platform metadata.

### Inbound Forwarding
The bot must send into the user's topic:
- every questionnaire answer in `Вопрос: ответ` format
- any plain user message sent after start
- supported attachments such as photos and documents
- service notices when the source platform limits the original attachment format

### Outbound Manager Replies
- Any manager message posted in the user's topic is treated as a customer reply.
- The bot sends that reply to the customer on the original platform on behalf of the bot.
- The customer must not see which manager wrote the message.
- If multiple managers participate, the user still sees only the bot.
- Outbound sending should support whatever the target platform supports for that content type.
- If a specific attachment type cannot be delivered to the target platform, the bot must post a service error message back into the topic.

## Functional Requirements
### Must Have (P0)
- Support `Telegram`, `VK`, and `MAX` inbound customer conversations.
- Run on `Ubuntu 24`.
- Use `long polling` instead of webhooks for the initial release.
- Show a clear start action on each platform within platform limits.
- Send the welcome message and main menu after start.
- Implement flows `1`, `2`, and `3` exactly as defined.
- Always show a `Cancel` button during active flows.
- Show a `Home` button after successful completion.
- Create one `Telegram` forum topic per started user conversation.
- Forward every user answer into the topic in `Вопрос: ответ` format.
- Forward all additional user messages into the same topic.
- Forward supported attachments into the same topic.
- Allow managers to reply from the topic and have replies delivered to the correct platform user.
- Preserve platform origin in the topic name.
- Keep minimal persistent runtime state needed for routing and flow progress.
- Preserve the binding `user -> topic -> flow step` across process restarts, server reboots, and redeployments.
- Provide startup instruction text for `Telegram` pre-start view, explaining that the bot starts via the `Start` button or `/start`.

### Should Have (P1)
- Reuse an existing topic for repeat interactions from the same user instead of creating duplicates.
- Post service messages into the topic when delivery to or from a platform fails.
- Normalize obvious spelling and punctuation issues in fixed bot texts while preserving business meaning and tone.
- Gracefully handle users who send files instead of text where a text answer was expected.

### Nice to Have (P2)
- Add lightweight operator service commands later, such as diagnostics or delivery status.
- Add migration path from polling to webhooks after a domain becomes available.

## Conversation Logic
### State Handling
The bot needs minimal persistent state for:
- source platform
- source user ID
- current active flow
- current step index
- linked admin `Telegram` topic ID
- user-facing display metadata needed for topic naming
- delivery/routing metadata required to send manager replies back to the correct customer

This persistent state is mandatory and cannot live only in process memory.
The system must restore routing and questionnaire progress after service restart without recreating topics or losing the active step.

This is operational state, not a business archive.

### Start and Restart Rules
- `/start` or platform-equivalent start action resets the user to the welcome message.
- If the user already has a topic, the existing topic should be reused.
- If the user starts again mid-flow, the flow resets.

### Completion Rules
- Once a flow completes, the questionnaire state clears.
- The topic remains available for future manager-customer communication.

## Attachments and Media
### Inbound
- The bot must accept text, photos, and documents from users where supported by the source platform.
- All supported inbound attachments must be forwarded into the corresponding admin topic.
- If a platform exposes only a link or limited metadata, the bot forwards the best available representation plus a service note if needed.

### Outbound
- Manager replies from the admin topic must be delivered with the richest compatible format supported by the target platform.
- If a manager sends unsupported content for a specific platform, the bot must not silently drop it; it must report the failure in the topic.

## Error Handling
- If topic creation fails, the bot must log the failure and notify administrators through a service message path if available.
- If a manager message cannot be delivered to the user, the bot must write a service error into the same topic.
- If a user sends content before platform start conditions are satisfied, the bot should guide them through the platform's start path where technically possible.
- If polling temporarily fails, the service should resume without losing the routing state stored for active users.

## Technical Architecture
### High-Level Design
One backend service on `Ubuntu 24` will:
- run polling consumers for `Telegram`, `VK`, and `MAX`
- normalize incoming events from all three platforms into a shared internal message format
- manage questionnaire state per user
- route normalized inbound content to the admin `Telegram` supergroup
- route manager replies from `Telegram` topics back to the correct platform adapter

### Recommended Components
- `Platform adapters`
  - `telegram-customer-adapter`
  - `vk-adapter`
  - `max-adapter`
  - `telegram-admin-adapter`
- `Conversation state manager`
- `Topic router`
- `Attachment handler`
- `Outbound delivery service`
- `Configuration and secrets manager`

### Data Model
Minimal entities:
- `UserSession`
  - platform
  - platform_user_id
  - username
  - display_name
  - telegram_topic_id
  - current_flow
  - current_step
  - flow_status
  - created_at
  - updated_at
- `PlatformMessageRef`
  - optional mapping for platform-specific message IDs when needed for delivery tracing

Recommended uniqueness and integrity rules:
- unique key on `platform + platform_user_id`
- unique key on linked `telegram_topic_id`
- non-null persistent mapping once a topic is created
- updates to `current_flow` and `current_step` must be atomic with topic binding updates when relevant

No full chat history is required by the product specification.

### Storage Recommendation
Use a small persistent database for runtime state, for example:
- `PostgreSQL` if the team wants robust persistence and future growth
- `SQLite` if the deployment is intentionally lightweight and single-instance

Given three platforms, durable routing requirements, and mandatory recovery after restart, `PostgreSQL` is the recommended default for implementation even though a full archive is not needed.

### Integration Boundaries
- `Telegram customer bot API`
- `Telegram admin supergroup/forum topic API`
- `VK community messaging API / long poll`
- `MAX bot API`

### Routing Rules
- Inbound from any platform -> normalize -> create/reuse topic -> send to topic
- Inbound from admin topic -> identify linked user -> send through source platform adapter

## Security Model
- Store all platform tokens securely in environment variables or a secret store.
- Restrict reply authority to members of the admin supergroup.
- Do not expose manager identities to end users.
- Log operational failures carefully without leaking tokens or sensitive data.
- Phone numbers and names are personal data; protect database access and server access accordingly.

## Non-Functional Requirements
- Performance: normal bot responses should appear within a few seconds under typical load.
- Scalability: initial version is suitable for a small-to-medium lead flow on one server; architecture should allow later horizontal decomposition by platform adapter.
- Reliability: polling workers should auto-restart under a process manager such as `systemd`.
- Maintainability: platform-specific logic should be isolated to adapters because `Telegram`, `VK`, and `MAX` capabilities differ.
- Compatibility: implementation must account for per-platform feature limitations for keyboards, files, and start UX.

## Operational Requirements
- Deploy on `Ubuntu 24`.
- Run as a background service.
- Use environment-based configuration for all tokens and IDs.
- Required admin-side `Telegram` setup:
  - bot added to the admin supergroup
  - supergroup configured with forum topics enabled
  - bot granted permission to manage topics and send messages

## Telegram Start Instruction Requirement
When the user opens the `Telegram` bot before starting it, the visible onboarding text should clearly explain how to begin. Recommended wording:

```text
Здравствуйте! Чтобы начать работу с ботом, нажмите кнопку «Старт» внизу экрана или отправьте команду /start.
```

This text is intended for the `Telegram` pre-start experience and any bot description/about field where applicable.

## Acceptance Criteria
1. A new `Telegram` user opens the bot, sees start guidance, presses `Start`, receives the welcome message, completes a flow, and all answers appear in a dedicated admin topic.
2. A new `VK` user opens the community dialog, gets the available start path, completes a flow, and all answers appear in a dedicated admin topic.
3. A new `MAX` user starts the bot through the platform's supported start action, completes a flow, and all answers appear in a dedicated admin topic.
4. A manager writes in the customer's topic, and the customer receives the reply from the bot on the original platform.
5. User attachments and manager attachments are delivered wherever the target platform supports them.
6. Unsupported delivery attempts produce a visible service error in the admin topic.
7. Pressing `Cancel` during a flow returns the user to the welcome message.
8. Pressing `Home` after completion returns the user to the welcome message.

## Out of Scope
- Webhooks in the first release
- CRM integration
- Dedicated operator dashboard outside `Telegram`
- Explicit case closing workflow
- Full reporting and analytics
- Full chat archive as a product feature
- Separate manager role directory beyond supergroup membership

## Risks and Constraints
- `MAX` production availability depends on external platform approval/moderation requirements.
- `VK`, `Telegram`, and `MAX` differ in startup UX, file handling, and keyboard behavior; a perfect one-to-one UX match is not always possible.
- Without durable state storage, topic routing would break after restart; therefore minimal persistence is mandatory even though a chat archive is not required.
- Polling is simpler for launch but less efficient than webhooks for future scaling.

## Open Questions for Implementation
- Confirm the exact `MAX` polling and outbound media capabilities available to the approved bot account at implementation time.
- Confirm whether repeated future contact from the same user should always append to the original topic or ever create a new topic after long inactivity.
- Confirm the preferred transliteration/fallback scheme for missing usernames in topic titles.
- Confirm whether the admin topic should receive structured service labels like `[USER MESSAGE]`, `[FLOW ANSWER]`, or only raw `Вопрос: ответ` formatting plus plain relayed messages.

## Recommended Implementation Plan
1. Build the common conversation engine and runtime state storage.
2. Integrate the `Telegram` admin supergroup topic router first.
3. Implement `Telegram` customer bot flow end-to-end.
4. Add `VK` adapter with platform-specific keyboard/start behavior.
5. Add `MAX` adapter according to current approved bot capabilities.
6. Add attachment routing and delivery error reporting.
7. Package as a `systemd` service for `Ubuntu 24`.
