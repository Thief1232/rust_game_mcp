# rust-rcon MCP server

MCP-сервер, который даёт нейронке доступ к консоли Rust dedicated server через
WebSocket RCON (полный набор админ-команд) плюс доступ к трём справочным
ресурсам без локального браузера:

- `convars.json` / `commands.json` — обычные JSON, тянутся напрямую через `httpx`.
- `rustlas.com/api/docs` — это SPA (контент рендерится JS), поэтому используется
  бесплатный hosted-рендерер [Jina Reader](https://r.jina.ai/) вместо локального
  Firefox/Selenium — он рендерит страницу на своей стороне и отдаёт чистый текст.

## Установка (CachyOS / Arch-based)

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

## Инструменты

| Инструмент | Назначение |
|---|---|
| `rcon_command(command)` | Выполняет любую команду консоли с правами администратора |
| `fetch_json_resource(resource)` | Тянет `carbon-convars` / `carbon-commands` напрямую через httpx |
| `fetch_rendered_resource(resource)` | Тянет `rustlas-docs` через Jina Reader (рендерит JS за вас) |
| `list_allowed_resources()` | Показывает все доступные ресурсы и их URL |

## Важно про безопасность

- RCON в Rust = **полный** доступ к консоли, без разделения прав. Любая
  команда, которую вы попросите у нейронки, выполнится буквально —
  включая деструктивные (`kick`, `ban`, `quit`, изменение конвар). Здесь нет
  встроенного подтверждения перед выполнением — при желании легко добавить
  проверку/whitelist команд прямо в `rcon_command` перед вызовом
  `_send_rcon_command`.
- Доступ к внешним ресурсам жёстко ограничен статическими словарями
  `JSON_RESOURCES` / `RENDERED_RESOURCES` в коде — нейронка выбирает только
  по ключу (`"carbon-convars"` и т.д.), произвольный URL передать нельзя.
  Чтобы добавить ресурс, правьте эти словари в `server.py`.
- `fetch_rendered_resource` отправляет целевой URL стороннему сервису
  (r.jina.ai) для рендеринга — это публичный proxy, не гоняйте через него
  приватные/закрытые страницы.