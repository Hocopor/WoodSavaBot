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
python3 -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
```

2. Скопируйте шаблон переменных окружения:

```bash
cp .env.example .env
```

3. Заполните `.env` реальными токенами и ID.

4. Запустите приложение:

```bash
python -m wood_sava_bot.main
```

Либо так:

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

- отдельная папка, например `/srv/wood/WoodSavaBot`
- отдельное виртуальное окружение `.venv`
- отдельный `.env`
- отдельный `systemd` unit
- отдельная БД или отдельный файл `SQLite`

### Самый безопасный вариант

Если нужен простой старт без лишних зависимостей:

- код положить в `/srv/wood/WoodSavaBot`
- запускать как отдельный сервис
- хранить состояние в `PostgreSQL` с отдельной БД `wood_sava_bot`

Если `PostgreSQL` пока не хотите:

- можно начать с `SQLite`
- файл базы будет лежать только в папке проекта
- для одного инстанса это допустимо

## Пошаговый деплой на Ubuntu 24

### 1. Скопировать проект

```bash
mkdir -p /srv/wood/WoodSavaBot
```

Дальше положите код проекта в `/srv/wood/WoodSavaBot`.

### 2. Установить зависимости Python

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip
```

### 3. Создать виртуальное окружение и установить проект

```bash
cd /srv/wood/WoodSavaBot
python3 -m venv .venv
./.venv/bin/pip install --upgrade pip
./.venv/bin/pip install -e .[dev]
```

### 4. Создать `.env`

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

### 5. Настроить БД

Простой вариант с `SQLite`:

```env
DATABASE_URL=sqlite+aiosqlite:///./wood_sava_bot.db
```

Более надёжный вариант с `PostgreSQL`:

```env
DATABASE_URL=postgresql+asyncpg://wood_sava_user:strong_password@127.0.0.1:5432/wood_sava_bot
```

Важно: если вы выбрали `PostgreSQL`, на сервере должен быть не только установлен пакет `asyncpg` в `.venv`, но и запущен сам сервер `PostgreSQL` на `127.0.0.1:5432`.

Если в логах видно такое:

```text
ConnectionRefusedError: [Errno 111] Connect call failed ('127.0.0.1', 5432)
```

это значит, что приложение не может подключиться к `PostgreSQL`, потому что:

- `PostgreSQL` не установлен
- `PostgreSQL` не запущен
- база/пользователь ещё не созданы

Минимальный копипаст для установки `PostgreSQL`:

```bash
apt update
apt install -y postgresql postgresql-contrib
systemctl enable postgresql
systemctl start postgresql
systemctl status postgresql
```

Создать пользователя и базу:

```bash
sudo -u postgres psql <<'EOF'
CREATE USER wood_sava_user WITH PASSWORD 'strong_password';
CREATE DATABASE wood_sava_bot OWNER wood_sava_user;
GRANT ALL PRIVILEGES ON DATABASE wood_sava_bot TO wood_sava_user;
EOF
```

Потом перезапустить бота:

```bash
systemctl restart wood-sava-bot
systemctl status wood-sava-bot
journalctl -u wood-sava-bot -f
```

Если хотите сначала просто запустить бота без возни с `PostgreSQL`, используйте `SQLite`.

### 6. Установить systemd unit

В репозитории уже есть шаблон:
[wood-sava-bot.service](A:\DevAI\Projects\WoodSavaBot\deploy\systemd\wood-sava-bot.service)

Под сервер лучше поправить его так, чтобы он запускался от `root`.

Рекомендуемая версия:

```ini
[Unit]
Description=Wood_Sava_Bot service
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=root
WorkingDirectory=/srv/wood/WoodSavaBot
EnvironmentFile=/srv/wood/WoodSavaBot/.env
ExecStart=/srv/wood/WoodSavaBot/.venv/bin/python -m wood_sava_bot.main
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

Если у вас путь проекта именно `/root/WoodSavaBot`, вот готовый копипаст-блок целиком:

```bash
cat > /etc/systemd/system/wood-sava-bot.service <<'EOF'
[Unit]
Description=Wood_Sava_Bot service
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/WoodSavaBot
EnvironmentFile=/root/WoodSavaBot/.env
ExecStart=/root/WoodSavaBot/.venv/bin/python -m wood_sava_bot.main
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable wood-sava-bot
systemctl start wood-sava-bot
systemctl status wood-sava-bot
journalctl -u wood-sava-bot -f
```

### 7. Проверить статус и логи

```bash
sudo systemctl status wood-sava-bot
sudo journalctl -u wood-sava-bot -f
```

## Почему это не конфликтует с двумя сайтами

Если сделать как выше, бот не будет конфликтовать с сайтами, потому что у него будут:

- своя директория
- своё виртуальное окружение
- свой `systemd` сервис
- свой `.env`
- своя база или свой DB schema

Конфликт возможен только если:

- использовать ту же БД и те же таблицы без разделения
- класть зависимости в общее Python-окружение

Этого как раз и не нужно делать.

## Команды для обновления бота на сервере

После изменения кода:

```bash
cd /srv/wood/WoodSavaBot
git pull
./.venv/bin/pip install -e .
sudo systemctl restart wood-sava-bot
sudo journalctl -u wood-sava-bot -n 100 --no-pager
```

## Ручной запуск на сервере

Если хотите сначала проверить всё вручную, без `systemd`:

```bash
cd /srv/wood/WoodSavaBot
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e .
cp .env.example .env
nano .env
python -m wood_sava_bot.main
```

Если всё установлено, можно короче:

```bash
cd /srv/wood/WoodSavaBot
source .venv/bin/activate
python -m wood_sava_bot.main
```

Если `TELEGRAM_ADMIN_CHAT_ID` не нужен, его можно не указывать в `.env` совсем.

## Что я бы рекомендовал перед первым боевым запуском

1. Сначала поднять бота на `SQLite`, чтобы быстро проверить логику.
2. Прогнать реальные сценарии `Telegram -> группа -> ответ менеджера`.
3. Потом проверить `VK`.
4. Потом отдельно проверить `MAX`, потому что там выше шанс платформенных сюрпризов.
5. После этого уже решить, оставаться на `SQLite` или перейти на `PostgreSQL`.
