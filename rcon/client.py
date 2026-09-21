"""
WebSocket RCON клиент для Rust dedicated server.

Ничего не знает про MCP — только протокол RCON: соединение, аутентификация
паролем в URI, отправка команды и сбор ответа консоли.

Запуск сервера Rust (пример):
  ./RustDedicated -batchmode \
    +server.ip 127.0.0.1 +server.port 28015 \
    +rcon.ip 127.0.0.1 +rcon.port 28016 \
    +rcon.password "СЕКРЕТНЫЙ_ПАРОЛЬ" +rcon.web true
"""

import asyncio
import itertools
import json
from urllib.parse import quote

import websockets
from decouple import config

RCON_HOST = config("RCON_HOST", default="127.0.0.1")
RCON_PORT = config("RCON_PORT", default="28016")
RCON_PASSWORD = config("RCON_PASSWORD", default=None)
RCON_TIMEOUT = config("RCON_TIMEOUT", default=5, cast=float)

_id_counter = itertools.count(1)

# После первого пришедшего фрагмента ответа даём консоли ещё немного
# времени: некоторые команды (status, playerlist, вывод плагинов) могут
# присылать несколько сообщений с одним и тем же Identifier, и ответ
# нельзя обрезать по первому же сообщению, иначе часть вывода потеряется.
IDLE_GRACE = 0.5


async def send_command(command: str, timeout: float = RCON_TIMEOUT) -> str:
    """Отправляет команду на Rust WebSocket RCON и возвращает ответ консоли."""
    if not RCON_PASSWORD:
        raise RuntimeError(
            "RCON_PASSWORD не задан. Установите переменную окружения RCON_PASSWORD "
            "(должна совпадать с +rcon.password на сервере)."
        )

    uri = f"ws://{RCON_HOST}:{RCON_PORT}/{quote(RCON_PASSWORD, safe='')}"
    ident = next(_id_counter)

    try:
        async with websockets.connect(uri, open_timeout=timeout) as ws:
            await ws.send(
                json.dumps({"Identifier": ident, "Message": command, "Name": "mcp-rust"})
            )

            loop = asyncio.get_running_loop()
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
                    deadline = min(deadline, loop.time() + IDLE_GRACE)

            return "\n".join(collected) if collected else "(сервер не ответил за отведённое время)"
    except (OSError, asyncio.TimeoutError, websockets.exceptions.WebSocketException) as exc:
        return f"Не удалось подключиться к RCON ({RCON_HOST}:{RCON_PORT}): {exc}"
