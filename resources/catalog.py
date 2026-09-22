"""
Каталог справочных ресурсов — только фиксированный allowlist, без локального браузера.

convars.json / commands.json — обычные JSON-эндпоинты, тянутся напрямую.

Чтобы добавить новый ресурс — правьте словарь ниже.
"""

import httpx

JSON_RESOURCES = {
    "carbon-convars": "https://api.carbonmod.gg/meta/rust/convars.json",
    "carbon-commands": "https://api.carbonmod.gg/meta/rust/commands.json",
}


async def fetch_json(resource: str) -> str:
    """Скачивает один из справочных JSON-файлов по ключу из JSON_RESOURCES."""
    if resource not in JSON_RESOURCES:
        return f"Неизвестный ресурс. Доступные: {', '.join(JSON_RESOURCES)}"

    url = JSON_RESOURCES[resource]
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        return resp.text
