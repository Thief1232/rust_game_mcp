"""
Каталог справочных ресурсов — только фиксированный allowlist, без локального браузера.

convars.json / commands.json — обычные JSON-эндпоинты, тянутся напрямую.
rustlas.com/api/docs — это SPA (контент рендерится JS на клиенте), поэтому
для него используется Jina Reader (https://r.jina.ai/<url>) — бесплатный
hosted-сервис, который рендерит страницу на своей стороне и отдаёт чистый
текст. Никакой Firefox/Selenium/geckodriver локально не нужен.

Чтобы добавить новый ресурс — правьте словари ниже.
"""

import httpx

JSON_RESOURCES = {
    "carbon-convars": "https://api.carbonmod.gg/meta/rust/convars.json",
    "carbon-commands": "https://api.carbonmod.gg/meta/rust/commands.json",
}

RENDERED_RESOURCES = {
    "rustlas-docs": "https://rustlas.com/api/docs/description/introduction",
}

JINA_READER_PREFIX = "https://r.jina.ai/"

MAX_RENDERED_CHARS = 15000


async def fetch_json(resource: str) -> str:
    """Скачивает один из справочных JSON-файлов по ключу из JSON_RESOURCES."""
    if resource not in JSON_RESOURCES:
        return f"Неизвестный ресурс. Доступные: {', '.join(JSON_RESOURCES)}"

    url = JSON_RESOURCES[resource]
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        return resp.text


async def fetch_rendered(resource: str) -> str:
    """Скачивает справочную страницу через Jina Reader по ключу из RENDERED_RESOURCES."""
    if resource not in RENDERED_RESOURCES:
        return f"Неизвестный ресурс. Доступные: {', '.join(RENDERED_RESOURCES)}"

    target_url = RENDERED_RESOURCES[resource]
    reader_url = JINA_READER_PREFIX + target_url

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(reader_url)
        resp.raise_for_status()
        text = resp.text

    if len(text) > MAX_RENDERED_CHARS:
        text = text[:MAX_RENDERED_CHARS] + f"\n\n... (обрезано, всего {len(text)} символов)"
    return text
