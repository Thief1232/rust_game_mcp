"""
MCP-сервер для управления локальным Rust dedicated server через WebSocket RCON,
плюс безопасный доступ к справочным ресурсам (allowlist), без локального браузера.

Запуск сервера Rust (пример):
  ./RustDedicated -batchmode \
    +server.ip 127.0.0.1 +server.port 28015 \
    +rcon.ip 127.0.0.1 +rcon.port 28016 \
    +rcon.password "СЕКРЕТНЫЙ_ПАРОЛЬ" +rcon.web true

Конфигурация читается через python-decouple: из .env-файла в корне проекта
(см. .env.example) либо из переменных окружения — что найдётся первым.

  RCON_HOST     - хост RCON (по умолчанию 127.0.0.1)
  RCON_PORT     - порт RCON (по умолчанию 28016)
  RCON_PASSWORD - пароль RCON (обязателен, без значения по умолчанию)
  RCON_TIMEOUT  - таймаут ожидания ответа в секундах (по умолчанию 5)
"""

import asyncio
import itertools
import json

import httpx
import websockets
from decouple import config

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("rust-rcon")

# ---------------------------------------------------------------------------
# Конфигурация RCON
# ---------------------------------------------------------------------------

RCON_HOST = config("RCON_HOST", default="127.0.0.1")
RCON_PORT = config("RCON_PORT", default="28016")
RCON_PASSWORD = config("RCON_PASSWORD", default=None)
RCON_TIMEOUT = config("RCON_TIMEOUT", default=5, cast=float)

_id_counter = itertools.count(1)


async def _send_rcon_command(command: str, timeout: float = RCON_TIMEOUT) -> str:
    """Отправляет команду на Rust WebSocket RCON и возвращает ответ консоли."""
    if not RCON_PASSWORD:
        raise RuntimeError(
            "RCON_PASSWORD не задан. Установите переменную окружения RCON_PASSWORD "
            "(должна совпадать с +rcon.password на сервере)."
        )

    uri = f"ws://{RCON_HOST}:{RCON_PORT}/{RCON_PASSWORD}"
    ident = next(_id_counter)

    async with websockets.connect(uri, open_timeout=timeout) as ws:
        await ws.send(
            json.dumps({"Identifier": ident, "Message": command, "Name": "mcp-rust"})
        )

        loop = asyncio.get_event_loop()
        deadline = loop.time() + timeout
        collected = []

        while True:
            remaining = deadline - loop.time()
            if remaining <= 0:
                break
            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=remaining)
            except asyncio.TimeoutError:
                break

            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                continue

            # Сервер может присылать broadcast-сообщения (чат, логи) с чужим
            # Identifier — нас интересует ответ именно на наш запрос.
            if data.get("Identifier") == ident:
                collected.append(data.get("Message", ""))
                break

        return "\n".join(collected) if collected else "(сервер не ответил за отведённое время)"


@mcp.tool()
async def rcon_command(command: str) -> str:
    """
    Выполняет ЛЮБУЮ административную команду на консоли Rust-сервера через RCON.

    Полный доступ администратора: status, playerlist, serverinfo, say,
    console.tail 50, kick <id>, ban <id>, giveall <item>, изменение конвар
    (например server.maxplayers 20), saveall, quit и т.д.

    Аргументы:
      command: строка команды ровно в том виде, как она вводится в консоли сервера.
    """
    return await _send_rcon_command(command)


# ---------------------------------------------------------------------------
# Справочные ресурсы — только из фиксированного allowlist, без локального браузера
# ---------------------------------------------------------------------------
#
# convars.json / commands.json — обычные JSON-эндпоинты, тянутся напрямую.
# rustlas.com/api/docs — это SPA (контент рендерится JS на клиенте), поэтому
# для него используется Jina Reader (https://r.jina.ai/<url>) — бесплатный
# hosted-сервис, который рендерит страницу на своей стороне и отдаёт чистый
# текст. Никакой Firefox/Selenium/geckodriver локально не нужен.

JSON_RESOURCES = {
    "carbon-convars": "https://api.carbonmod.gg/meta/rust/convars.json",
    "carbon-commands": "https://api.carbonmod.gg/meta/rust/commands.json",
}

RENDERED_RESOURCES = {
    "rustlas-docs": "https://rustlas.com/api/docs/description/introduction",
}

JINA_READER_PREFIX = "https://r.jina.ai/"


@mcp.tool()
async def fetch_json_resource(resource: str) -> str:
    """
    Скачивает один из справочных JSON-файлов Carbon по конварам/командам Rust.

    Аргументы:
      resource: "carbon-convars" (список конвар) или "carbon-commands" (список команд).
    """
    if resource not in JSON_RESOURCES:
        return f"Неизвестный ресурс. Доступные: {', '.join(JSON_RESOURCES)}"

    url = JSON_RESOURCES[resource]
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        return resp.text


@mcp.tool()
async def fetch_rendered_resource(resource: str) -> str:
    """
    Скачивает справочную документацию, которая рендерится через JS (SPA),
    используя внешний сервис-рендерер (Jina Reader), без локального браузера.

    Аргументы:
      resource: "rustlas-docs" — введение в API Rustlas.
    """
    if resource not in RENDERED_RESOURCES:
        return f"Неизвестный ресурс. Доступные: {', '.join(RENDERED_RESOURCES)}"

    target_url = RENDERED_RESOURCES[resource]
    reader_url = JINA_READER_PREFIX + target_url

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(reader_url)
        resp.raise_for_status()
        text = resp.text

    max_chars = 15000
    if len(text) > max_chars:
        text = text[:max_chars] + f"\n\n... (обрезано, всего {len(text)} символов)"
    return text


@mcp.tool()
def list_allowed_resources() -> str:
    """Возвращает список всех справочных ресурсов, доступных инструментам fetch_*."""
    lines = ["JSON-ресурсы (fetch_json_resource):"]
    lines += [f"  - {k}: {v}" for k, v in JSON_RESOURCES.items()]
    lines.append("Рендерящиеся ресурсы (fetch_rendered_resource):")
    lines += [f"  - {k}: {v}" for k, v in RENDERED_RESOURCES.items()]
    return "\n".join(lines)


if __name__ == "__main__":
    mcp.run()