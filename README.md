# rust-rcon MCP server

MCP-сервер, который даёт нейронке доступ к консоли Rust dedicated server через
WebSocket RCON (полный набор админ-команд) плюс доступ к справочным JSON-файлам
Carbon по конварам/командам (`convars.json` / `commands.json`, тянутся напрямую
через `httpx`).

## Установка (Arch-based)

```bash
sudo pacman -S --needed python python-pip

cd rust-mcp-server
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Настройка

Сервер Rust должен быть запущен с включённым WebSocket RCON:

```bash
+rcon.ip 127.0.0.1 +rcon.port 28016 +rcon.password "dev_secret_password" +rcon.web true
```

Конфигурация читается через `python-decouple` — скопируйте `example/.env.example`
в `.env` и заполните своими значениями:

```bash
cp example/.env.example .env
# отредактируйте .env своим паролем
```

## Проверка вручную

```bash
python server.py
```

Сервер стартует по протоколу MCP (stdio) и ждёт подключения клиента —
запускать напрямую в терминале для "просто посмотреть, что выводит" смысла
нет, нужен MCP-клиент (Claude Desktop, либо `mcp dev server.py` для отладочного UI).

Быстрая отладка с встроенным инспектором MCP:

```bash
mcp dev server.py
```

Откроется веб-интерфейс, где можно вручную вызвать `rcon_command("status")`
и увидеть сырой ответ сервера.

## Подключение в Claude Desktop

Скопируйте `example/claude_desktop_config.example.json` в конфиг Claude Desktop
(обычно `~/.config/Claude/claude_desktop_config.json` на Linux — **только если
это у вас именно отдельное классическое приложение Claude Desktop**; если вы
используете Claude Code, этот файл вам не подходит, см. следующий раздел). В
нём нужно поправить два абсолютных пути на свои (`.venv/bin/python` —
специально не просто `python`, чтобы Claude Desktop использовал интерпретатор
из venv проекта со всеми зависимостями, а не системный) и при желании —
`RCON_PASSWORD` в `env` (необязательно, если он уже есть в `.env`:
`python-decouple` находит `.env` рядом с исходниками проекта независимо от
того, откуда Claude Desktop запустил процесс). После правки перезапустите
Claude Desktop.

После этого в обычном чате можно писать, например:

- «Покажи статус сервера» → нейронка сама вызовет `rcon_command("status")`
- «Забань игрока с id 12345» → `rcon_command("ban 12345")`
- «Какие конвары есть у Carbon для управления лутом?» →
  `fetch_json_resource("carbon-convars")`

## Подключение в Claude Code

Claude Code не читает `claude_desktop_config.json` — это формат отдельного
классического приложения Claude Desktop. У Claude Code свой механизм
регистрации MCP-серверов: команда `claude mcp add`.

Зарегистрировать сервер глобально для пользователя (доступен из любой сессии
Claude Code, независимо от того, в какой папке вы находитесь):

```bash
claude mcp add rust-rcon --scope user -- \
  /ABSOLUTE/PATH/TO/rust_game_mcp/.venv/bin/python \
  /ABSOLUTE/PATH/TO/rust_game_mcp/server.py
```

Как и в случае с Claude Desktop, `RCON_PASSWORD` отдельно передавать не нужно
(флагом `-e`) — `python-decouple` сам найдёт `.env` рядом с исходниками
проекта. Проверить, что подключение прошло:

```bash
claude mcp list
# rust-rcon: ... - ✔ Connected
```

Другие доступные scope у `claude mcp add`:

- `--scope local` (по умолчанию, если флаг не указан) — сервер виден только
  вам и только в текущем проекте;
- `--scope project` — пишет в `.mcp.json` в корне репозитория, который можно
  закоммитить и раздать команде (тогда пароль лучше не прописывать флагом
  `-e`, чтобы не закоммитить секрет вместе с файлом, — пусть остаётся в
  локальном `.env` у каждого).

Дальше в чате Claude Code тулы работают так же, как в Claude Desktop — можно
писать те же запросы, что в примерах выше.

## Подключение из ChatGPT

Claude Desktop сам запускает `server.py` как локальный подпроцесс (транспорт
`stdio`). ChatGPT так не умеет — ему нужен MCP-сервер, доступный по сети через
HTTP (транспорт `streamable-http`). Порядок действий:

1. Сгенерируйте токен и пропишите транспорт в `.env`:
   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```
   ```
   MCP_TRANSPORT=streamable-http
   MCP_HOST=0.0.0.0
   MCP_PORT=8000
   MCP_BEARER_TOKEN=<сгенерированное значение>
   ```
   Без `MCP_BEARER_TOKEN` сервер откажется запускаться в этом режиме —
   `MCP_TRANSPORT=streamable-http` выставляет его в сеть, и без токена
   `rcon_command` был бы доступен любому, кто узнает URL.
2. Запустите сервер как обычно — `python server.py`. Он поднимет HTTP-эндпоинт
   на `http://<host>:<port>/mcp` (путь `/mcp` — значение по умолчанию в
   библиотеке `mcp`), защищённый проверкой заголовка
   `Authorization: Bearer <MCP_BEARER_TOKEN>` (см. `http_auth.py`).
3. ChatGPT обращается к серверу из облака, поэтому `127.0.0.1` ему не виден —
   нужен адрес, доступный из интернета:
   - для быстрой проверки — временный туннель, например
     `cloudflared tunnel --url http://localhost:8000` или `ngrok http 8000`
     (оба выдают публичный `https://...` URL, но он меняется при каждом
     перезапуске туннеля, если не платный статический);
   - для регулярного использования — сервер должен крутиться там, где есть
     постоянный публичный адрес (VPS, домашняя машина с проброшенным портом
     на роутере и т.д.).
4. В ChatGPT: **Settings → Connectors → Add custom connector** (формулировка
   в интерфейсе может немного отличаться в зависимости от версии), укажите
   публичный URL вида `https://ваш-адрес/mcp` и передайте `MCP_BEARER_TOKEN`
   в поле аутентификации коннектора (Bearer/API-токен). После подключения
   тулы (`rcon_command`, `fetch_json_resource` и т.д.) становятся доступны в
   чате так же, как в Claude Desktop.

Это простой статический токен (общий секрет), а не полноценный OAuth —
достаточно для одного доверенного клиента, но не подходит, если токеном
нужно будет делиться с несколькими независимыми пользователями. Держите его
в секрете так же, как `RCON_PASSWORD`.

## Инструменты

| Инструмент | Назначение |
|---|---|
| `rcon_command(command)` | Выполняет команду консоли в пределах текущего `ACCESS_LEVEL` |
| `get_access_level()` | Показывает текущий уровень доступа и что разрешено на каждом |
| `fetch_json_resource(resource)` | Тянет `carbon-convars` / `carbon-commands` напрямую через httpx |
| `list_allowed_resources()` | Показывает все доступные ресурсы и их URL |

## Структура проекта

```
mcp_app.py              общий экземпляр FastMCP, на который регистрируются тулы
http_auth.py             bearer-токен для streamable-http (не используется для stdio)
server.py                composition root: собирает mcp_app + rcon.tools + resources.tools, mcp.run()
rcon/
  client.py               протокол WebSocket RCON (соединение, отправка, сбор ответа)
  access_control.py         классификация команд по уровням доступа (safe/basic/full)
  tools.py                    тулы rcon_command / get_access_level
resources/
  catalog.py               allowlist справочных ресурсов (JSON_RESOURCES) и их загрузка
  tools.py                    тулы fetch_json_resource / list_allowed_resources
```

## Важно про безопасность

- RCON в Rust = **полный** доступ к консоли, без разделения прав на своей
  стороне — поэтому ограничение прав сделано на уровне MCP-сервера:
  `rcon/access_control.py` классифицирует каждую команду (`safe` / `basic` /
  `full`) и `rcon_command` отклоняет то, что выше уровня, заданного
  переменной окружения `ACCESS_LEVEL` (по умолчанию — самый строгий, `safe`).
  Чтобы разрешить деструктивные команды (`kick`, `ban`, `quit`, изменение
  конвар), явно поднимите `ACCESS_LEVEL=full` в `.env`. Чтобы изменить,
  какие команды к какому уровню относятся, правьте `COMMAND_RULES` в
  `rcon/access_control.py`.
- Доступ к внешним ресурсам жёстко ограничен статическим словарём
  `JSON_RESOURCES` в `resources/catalog.py` — нейронка выбирает только по
  ключу (`"carbon-convars"` и т.д.), произвольный URL передать нельзя. Чтобы
  добавить ресурс, правьте этот словарь там же.