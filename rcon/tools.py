"""MCP-тулы для управления Rust-сервером через RCON, с учётом уровня доступа."""

from decouple import config

from mcp_app import mcp

from . import access_control, client

# Уровень доступа этого развёртывания MCP-сервера: safe / basic / full.
# По умолчанию — самый строгий ("safe"), чтобы случайный запуск без .env
# не давал нейронке полный доступ к серверу.
ACCESS_LEVEL = config("ACCESS_LEVEL", default="safe")
if ACCESS_LEVEL not in access_control.ACCESS_LEVELS:
    raise RuntimeError(
        f"Некорректный ACCESS_LEVEL={ACCESS_LEVEL!r}. "
        f"Допустимые значения: {', '.join(access_control.ACCESS_LEVELS)}"
    )


@mcp.tool()
async def rcon_command(command: str) -> str:
    """
    Выполняет административную команду на консоли Rust-сервера через RCON —
    в пределах текущего уровня доступа этого развёртывания (см. get_access_level).

    На уровне "safe" разрешены только команды чтения (status, playerlist,
    console.tail и т.д.). На "basic" — плюс взаимодействие с миром/постройками.
    На "full" — вообще всё, включая kill/kick/ban/giveall/quit.

    Аргументы:
      command: строка команды ровно в том виде, как она вводится в консоли сервера.
    """
    if not access_control.is_allowed(command, ACCESS_LEVEL):
        required = access_control.required_level(command)
        return (
            f"Команда отклонена: она требует уровень доступа '{required}', "
            f"а текущий уровень этого сервера — '{ACCESS_LEVEL}'.\n"
            f"Чтобы выполнить такую команду, перезапустите MCP-сервер с "
            f"ACCESS_LEVEL={required} (или выше) в .env."
        )
    return await client.send_command(command)


@mcp.tool()
def get_access_level() -> str:
    """
    Возвращает текущий уровень доступа этого MCP-сервера и что он разрешает.
    Полезно вызвать перед тем, как объяснять пользователю, почему команда
    была отклонена, или что вообще доступно прямо сейчас.
    """
    lines = [f"Текущий уровень доступа: {ACCESS_LEVEL}"]
    lines.append(f"  Разрешено: {access_control.describe_level(ACCESS_LEVEL)}")
    lines.append("")
    lines.append("Все уровни (от строгого к полному):")
    for level in access_control.ACCESS_LEVELS:
        marker = " <- текущий" if level == ACCESS_LEVEL else ""
        lines.append(f"  {level}: {access_control.describe_level(level)}{marker}")
    return "\n".join(lines)
