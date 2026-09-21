"""
MCP-сервер для управления локальным Rust dedicated server через WebSocket RCON,
плюс безопасный доступ к справочным ресурсам (allowlist), без локального браузера.

Конфигурация читается через python-decouple: из .env-файла в корне проекта
(см. .env.example) либо из переменных окружения — что найдётся первым.

  RCON_HOST     - хост RCON (по умолчанию 127.0.0.1)
  RCON_PORT     - порт RCON (по умолчанию 28016)
  RCON_PASSWORD - пароль RCON (обязателен, без значения по умолчанию)
  RCON_TIMEOUT  - таймаут ожидания ответа в секундах (по умолчанию 5)
  ACCESS_LEVEL  - уровень доступа к rcon_command: safe / basic / full (по умолчанию safe)
  MCP_TRANSPORT     - stdio (по умолчанию, для Claude Desktop) / streamable-http (для ChatGPT)
  MCP_HOST          - хост HTTP-эндпоинта при MCP_TRANSPORT=streamable-http (по умолчанию 127.0.0.1)
  MCP_PORT          - порт HTTP-эндпоинта при MCP_TRANSPORT=streamable-http (по умолчанию 8000)
  MCP_BEARER_TOKEN  - обязателен при MCP_TRANSPORT=streamable-http: общий секрет,
                       которым клиент должен представиться в заголовке
                       Authorization: Bearer <token> (см. http_auth.py)

Этот файл — только composition root: он собирает общий экземпляр FastMCP
и модули с тулами, реальная логика лежит в:

  mcp_app.py              - общий экземпляр FastMCP, на который регистрируются тулы
  http_auth.py             - bearer-токен для streamable-http (не нужен для stdio)
  rcon/client.py            - протокол WebSocket RCON (ничего не знает про MCP)
  rcon/access_control.py     - классификация RCON-команд по уровням доступа
  rcon/tools.py               - тулы rcon_command / get_access_level
  resources/catalog.py         - allowlist справочных ресурсов и их загрузка
  resources/tools.py            - тулы fetch_json_resource / fetch_rendered_resource /
                                  list_allowed_resources
"""

from mcp_app import mcp, TRANSPORT

# Импорт нужен ради побочного эффекта: модули регистрируют свои тулы на
# общем `mcp` через декоратор @mcp.tool().
import rcon.tools  # noqa: F401
import resources.tools  # noqa: F401


def _run_streamable_http() -> None:
    import uvicorn

    from http_auth import secured_streamable_http_app

    app = secured_streamable_http_app(mcp)
    uvicorn.run(app, host=mcp.settings.host, port=mcp.settings.port, log_level=mcp.settings.log_level.lower())


if __name__ == "__main__":
    if TRANSPORT == "streamable-http":
        # mcp.run() не даёт подставить свою ASGI-мидлварю, поэтому для этого
        # транспорта собираем и запускаем приложение сами, обернув его
        # проверкой bearer-токена.
        _run_streamable_http()
    else:
        mcp.run(transport=TRANSPORT)
