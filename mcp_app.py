"""
Общий экземпляр FastMCP, на который остальные модули регистрируют тулы.

TRANSPORT определяет, как клиент подключается к серверу:

  stdio            - сервер запускается как локальный подпроцесс клиента
                     (так работает Claude Desktop). Используется по умолчанию.
  streamable-http  - сервер поднимает HTTP-эндпоинт и ждёт подключений по сети.
                     Нужен для ChatGPT (и любого другого клиента, который не
                     умеет сам запускать процесс, а обращается по адресу) —
                     см. README, раздел "Подключение из ChatGPT".

MCP_HOST / MCP_PORT имеют значение только при MCP_TRANSPORT=streamable-http
(или sse) — для stdio они игнорируются.
"""

from decouple import config

from mcp.server.fastmcp import FastMCP

TRANSPORT = config("MCP_TRANSPORT", default="stdio")
MCP_HOST = config("MCP_HOST", default="127.0.0.1")
MCP_PORT = config("MCP_PORT", default=8000, cast=int)

mcp = FastMCP("rust-rcon", host=MCP_HOST, port=MCP_PORT)
