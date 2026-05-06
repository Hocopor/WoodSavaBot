# Wood_Sava_Bot

`Wood_Sava_Bot` - мультиплатформенный бот для `Telegram`, `VK` и `MAX`.
Он собирает заявки, пересылает все входящие сообщения в одну `Telegram` супергруппу с темами
и позволяет менеджерам отвечать пользователям прямо из этих тем.

## Что уже реализовано

- общий движок сценариев `1 / 2 / 3`
- `long polling` для `Telegram`, `VK` и `MAX`
- создание и повторное использование тем в `Telegram` супергруппе
- пересылка сообщений пользователя в тему менеджеров
- ответы менеджеров из темы обратно пользователю
- персистентное хранение привязки `user -> platform -> Telegram topic -> flow step`
- базовая работа с вложениями
- шаблон деплоя через `systemd`

## Что ещё обязательно проверить перед боевым запуском

- реальные токены и права бота на всех платформах
- создание тем в боевой `Telegram` супергруппе
- ответы менеджеров из тем в `Telegram`, `VK` и `MAX`
- отправку и приём вложений на всех платформах
- edge-cases и ограничения `VK` и особенно `MAX`

То есть фундамент уже готов, но перед продом ещё нужны реальные интеграционные тесты и добивка найденных недочётов.

## Стек

- `Python 3.12+`
- `httpx` для запросов к API платформ
- `SQLAlchemy` + `SQLite/PostgreSQL` для устойчивого хранения состояния
- `asyncio` для `long polling`

## Быстрый запуск локально

1. Создайте виртуальное окружение и установите зависимости:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
```

2. Скопируйте шаблон переменных окружения:

```bash
cp .env.example .env
```

3. Заполните `.env` реальными токенами и ID.

4. Запустите бота:

```bash
wood-sava-bot
```

## Основные файлы

- [Спецификация](A:\DevAI\Projects\WoodSavaBot\thoughts\shared\specs\2026-05-07-wood-sava-bot.md)
- [Живой план](A:\DevAI\Projects\WoodSavaBot\LIVE_PLAN.md)
- [Правила репозитория](A:\DevAI\Projects\WoodSavaBot\AGENTS.md)

## Как деплоить на сервер, где уже есть другие проекты

Если на сервере уже лежат два сайта, это не проблема. У этого бота сейчас `long polling`, а не вебхуки, значит:

- `nginx` ему вообще не обязателен
- отдельный домен не нужен
- порт наружу открывать не нужно
- конфликтов с сайтами по HTTP почти не будет

Главное правило: держите бота изолированно как отдельный сервис.

### Рекомендуемая изоляция

- отдельная папка, например `/opt/wood-sava-bot`
- отдельный Linux-пользователь, например `woodbot`
- отдельное виртуальное окружение `.venv`
- отдельный `.env`
- отдельный `systemd` unit
- отдельная БД или отдельный файл `SQLite`

### Самый безопасный вариант

Если нужен простой старт без лишних зависимостей:

- код положить в `/opt/wood-sava-bot`
- запускать от пользователя `woodbot`
- хранить состояние в `PostgreSQL` с отдельной БД `wood_sava_bot`

Если `PostgreSQL` пока не хотите:

- можно начать с `SQLite`
- файл базы будет лежать только в папке проекта
- для одного инстанса это допустимо

## Пошаговый деплой на Ubuntu 24

### 1. Создать отдельного пользователя

```bash
sudo adduser --system --group --home /opt/wood-sava-bot woodbot
```

### 2. Скопировать проект

```bash
sudo mkdir -p /opt/wood-sava-bot
sudo chown -R woodbot:woodbot /opt/wood-sava-bot
```

Дальше положите код проекта в `/opt/wood-sava-bot`.

### 3. Установить зависимости Python

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip
```

### 4. Создать виртуальное окружение и установить проект

```bash
cd /opt/wood-sava-bot
sudo -u woodbot python3 -m venv .venv
sudo -u woodbot .venv/bin/pip install --upgrade pip
sudo -u woodbot .venv/bin/pip install -e .[dev]
```

### 5. Создать `.env`

```bash
cp .env.example .env
```

Заполните минимум:

- `TELEGRAM_BOT_TOKEN`
- `VK_GROUP_ID`
- `VK_ACCESS_TOKEN`
- `MAX_ACCESS_TOKEN`
- `DATABASE_URL`

`TELEGRAM_ADMIN_CHAT_ID` теперь необязателен.

Если его не указывать:

- бот сам определит админскую группу
- для этого он должен находиться ровно в одной `Telegram` супергруппе с включёнными темами
- если таких групп будет несколько, бот напишет ошибку и попросит удалить его из лишних групп или явно указать `TELEGRAM_ADMIN_CHAT_ID`

### 6. Настроить БД

Простой вариант с `SQLite`:

```env
DATABASE_URL=sqlite+aiosqlite:///./wood_sava_bot.db
```

Более надёжный вариант с `PostgreSQL`:

```env
DATABASE_URL=postgresql+asyncpg://wood_sava_user:strong_password@127.0.0.1:5432/wood_sava_bot
```

### 7. Установить systemd unit

В репозитории уже есть шаблон:
[wood-sava-bot.service](A:\DevAI\Projects\WoodSavaBot\deploy\systemd\wood-sava-bot.service)

Под сервер лучше поправить его так, чтобы он запускался от `woodbot`, а не от `www-data`.

Рекомендуемая версия:

```ini
[Unit]
Description=Wood_Sava_Bot service
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=woodbot
Group=woodbot
WorkingDirectory=/opt/wood-sava-bot
EnvironmentFile=/opt/wood-sava-bot/.env
ExecStart=/opt/wood-sava-bot/.venv/bin/wood-sava-bot
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Скопировать и включить:

```bash
sudo cp deploy/systemd/wood-sava-bot.service /etc/systemd/system/wood-sava-bot.service
sudo systemctl daemon-reload
sudo systemctl enable wood-sava-bot
sudo systemctl start wood-sava-bot
```

### 8. Проверить статус и логи

```bash
sudo systemctl status wood-sava-bot
sudo journalctl -u wood-sava-bot -f
```

## Почему это не конфликтует с двумя сайтами

Если сделать как выше, бот не будет конфликтовать с сайтами, потому что у него будут:

- свой пользователь
- своя директория
- своё виртуальное окружение
- свой `systemd` сервис
- свой `.env`
- своя база или свой DB schema

Конфликт возможен только если:

- использовать ту же БД и те же таблицы без разделения
- запускать под тем же пользователем и мешать правами
- класть зависимости в общее Python-окружение

Этого как раз и не нужно делать.

## Команды для обновления бота на сервере

После изменения кода:

```bash
cd /opt/wood-sava-bot
sudo -u woodbot git pull
sudo -u woodbot .venv/bin/pip install -e .
sudo systemctl restart wood-sava-bot
sudo journalctl -u wood-sava-bot -n 100 --no-pager
```

## Что я бы рекомендовал перед первым боевым запуском

1. Сначала поднять бота на `SQLite`, чтобы быстро проверить логику.
2. Прогнать реальные сценарии `Telegram -> группа -> ответ менеджера`.
3. Потом проверить `VK`.
4. Потом отдельно проверить `MAX`, потому что там выше шанс платформенных сюрпризов.
5. После этого уже решить, оставаться на `SQLite` или перейти на `PostgreSQL`.
