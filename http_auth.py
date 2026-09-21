"""
Bearer-токен для HTTP-транспорта (streamable-http).

Нужен только когда сервер слушает сеть (например, для подключения из ChatGPT) —
у stdio-транспорта (Claude Desktop) нет HTTP-заголовков, поэтому там токен не
применяется и не проверяется.

Это не полноценный OAuth из mcp.server.auth (тому нужен issuer_url, сервер
выдачи токенов и т.д. — избыточно для одного доверенного клиента с общим
секретом). Здесь просто статический токен, сверяемый по заголовку
`Authorization: Bearer <token>`.
"""

import hmac

from decouple import config
from starlette.applications import Starlette
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

MCP_BEARER_TOKEN = config("MCP_BEARER_TOKEN", default=None)


class _BearerTokenMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, token: str):
        super().__init__(app)
        self._token = token

    async def dispatch(self, request: Request, call_next):
        scheme, _, value = request.headers.get("authorization", "").partition(" ")
        if scheme.lower() != "bearer" or not hmac.compare_digest(value, self._token):
            return JSONResponse({"error": "unauthorized"}, status_code=401)
        return await call_next(request)


def secured_streamable_http_app(mcp) -> Starlette:
    """
    Собирает Starlette-приложение mcp.streamable_http_app(), защищённое
    bearer-токеном. Требует, чтобы MCP_BEARER_TOKEN был задан — без токена
    HTTP-эндпоинт был бы открыт для любого, кто узнает URL.
    """
    if not MCP_BEARER_TOKEN:
        raise RuntimeError(
            "MCP_BEARER_TOKEN не задан, а MCP_TRANSPORT=streamable-http выставляет "
            "сервер в сеть. Сгенерируйте токен, например:\n"
            '  python -c "import secrets; print(secrets.token_urlsafe(32))"\n'
            "и добавьте его в .env как MCP_BEARER_TOKEN."
        )

    app = mcp.streamable_http_app()
    app.add_middleware(_BearerTokenMiddleware, token=MCP_BEARER_TOKEN)
    return app
