"""MCP-тулы для доступа к справочным ресурсам из catalog.py."""

from mcp_app import mcp

from . import catalog


@mcp.tool()
async def fetch_json_resource(resource: str) -> str:
    """
    Скачивает один из справочных JSON-файлов Carbon по конварам/командам Rust.

    Аргументы:
      resource: "carbon-convars" (список конвар) или "carbon-commands" (список команд).
    """
    return await catalog.fetch_json(resource)


@mcp.tool()
async def fetch_rendered_resource(resource: str) -> str:
    """
    Скачивает справочную документацию, которая рендерится через JS (SPA),
    используя внешний сервис-рендерер (Jina Reader), без локального браузера.

    Аргументы:
      resource: "rustlas-docs" — введение в API Rustlas.
    """
    return await catalog.fetch_rendered(resource)


@mcp.tool()
def list_allowed_resources() -> str:
    """Возвращает список всех справочных ресурсов, доступных инструментам fetch_*."""
    lines = ["JSON-ресурсы (fetch_json_resource):"]
    lines += [f"  - {k}: {v}" for k, v in catalog.JSON_RESOURCES.items()]
    lines.append("Рендерящиеся ресурсы (fetch_rendered_resource):")
    lines += [f"  - {k}: {v}" for k, v in catalog.RENDERED_RESOURCES.items()]
    return "\n".join(lines)
