# Wood_Sava_Bot

`Wood_Sava_Bot` is a multi-platform intake bot for `Telegram`, `VK`, and `MAX`.
It collects leads, forwards all inbound traffic to one `Telegram` forum supergroup,
and lets managers reply to customers from topic threads.

## Stack

- `Python 3.12+`
- `httpx` for platform APIs
- `SQLAlchemy` + `SQLite/PostgreSQL` for durable routing state
- `asyncio` long polling workers

## Quick Start

1. Create a virtual environment and install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
```

2. Copy the environment template:

```bash
cp .env.example .env
```

3. Fill in all tokens and IDs.

4. Start the bot:

```bash
wood-sava-bot
```

## Main Files

- [spec](A:\DevAI\Projects\WoodSavaBot\thoughts\shared\specs\2026-05-07-wood-sava-bot.md)
- [live plan](A:\DevAI\Projects\WoodSavaBot\LIVE_PLAN.md)
- [agents rules](A:\DevAI\Projects\WoodSavaBot\AGENTS.md)

## Deployment

`Ubuntu 24` deployment notes and `systemd` unit live in `deploy/systemd/`.
