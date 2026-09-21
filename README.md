# rust-rcon MCP server

MCP-сервер, который даёт нейронке доступ к консоли Rust dedicated server через
WebSocket RCON (полный набор админ-команд) плюс доступ к трём справочным
ресурсам без локального браузера:

- `convars.json` / `commands.json` — обычные JSON, тянутся напрямую через `httpx`.
- `rustlas.com/api/docs` — это SPA (контент рендерится JS), поэтому используется
  бесплатный hosted-рендерер [Jina Reader](https://r.jina.ai/) вместо локального
  Firefox/Selenium — он рендерит страницу на своей стороне и отдаёт чистый текст.

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

Конфигурация читается через `python-decouple` — скопируйте `.env.example` в `.env`
и заполните своими значениями:

```bash
cp .env.example .env
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

Скопируйте `claude_desktop_config.example.json` в конфиг Claude Desktop
(обычно `~/.config/Claude/claude_desktop_config.json` на Linux), поправьте
путь к `server.py` и пароль, перезапустите Claude Desktop.

После этого в обычном чате можно писать, например:

- «Покажи статус сервера» → нейронка сама вызовет `rcon_command("status")`
- «Забань игрока с id 12345» → `rcon_command("ban 12345")`
- «Какие конвары есть у Carbon для управления лутом?» →
  `fetch_json_resource("carbon-convars")`
- «Почитай введение в API Rustlas» → `fetch_rendered_resource("rustlas-docs")`

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
| `fetch_rendered_resource(resource)` | Тянет `rustlas-docs` через Jina Reader (рендерит JS за вас) |
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
  catalog.py               allowlist справочных ресурсов (JSON_RESOURCES/RENDERED_RESOURCES) и их загрузка
  tools.py                    тулы fetch_json_resource / fetch_rendered_resource / list_allowed_resources
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
- Доступ к внешним ресурсам жёстко ограничен статическими словарями
  `JSON_RESOURCES` / `RENDERED_RESOURCES` в `resources/catalog.py` —
  нейронка выбирает только по ключу (`"carbon-convars"` и т.д.), произвольный
  URL передать нельзя. Чтобы добавить ресурс, правьте эти словари там же.
- `fetch_rendered_resource` отправляет целевой URL стороннему сервису
  (r.jina.ai) для рендеринга — это публичный proxy, не гоняйте через него
  приватные/закрытые страницы.