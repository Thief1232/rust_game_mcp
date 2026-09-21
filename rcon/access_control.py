"""
Классификация RCON-команд Rust по уровням доступа.

RCON сам по себе не разделяет права — любая команда через него выполняется
с полными правами администратора. Поэтому ограничение реализовано на уровне
MCP-сервера: команда перехватывается ДО отправки в сокет и сверяется с тем,
что разрешено на текущем уровне доступа этого конкретного развёртывания.

Три уровня, от самого ограниченного к самому широкому:

  safe  - только чтение: статистика, статус, логи. Никакого влияния на игру.
  basic - взаимодействие с миром (постройки, сущности, окружение),
          но не напрямую с игроками.
  full  - полный доступ: игроки, бан/кик, любые команды без ограничений.

Каждый уровень включает в себя все более низкие (full умеет всё, что basic
и safe; basic умеет всё, что safe).
"""

import re

ACCESS_LEVELS = ["safe", "basic", "full"]
_LEVEL_RANK = {level: rank for rank, level in enumerate(ACCESS_LEVELS)}

# Если текст команды не совпал ни с одним паттерном ниже, ей присваивается
# этот уровень. Специально выбран самый строгий ("full") — неизвестная
# команда по умолчанию считается потенциально опасной, а не безопасной.
DEFAULT_LEVEL_FOR_UNKNOWN = "full"

# Порядок проверки важен — берётся первое совпадение сверху вниз.
# Каждая запись: (регулярное выражение, требуемый уровень доступа)
COMMAND_RULES: list[tuple[str, str]] = [
    # --- safe: только просмотр, никакого влияния на игру -------------------
    (r"^(status|serverinfo|playerlist|players)\b", "safe"),
    (r"^console\.tail\b", "safe"),
    (r"^server\.(fps|url|hostname|description|headerimage)\b", "safe"),
    (r"^global\.stats\b", "safe"),

    # --- basic: мир/постройки/окружение, но не игроки -----------------------
    (r"^spawn\b", "basic"),
    (r"^entity\.despawn\b", "basic"),
    (r"^(weather|env)\.", "basic"),
    (r"^server\.(save|writecfg)\b", "basic"),
    # kill/remove НЕ-игровых сущностей (постройки, животные, NPC, деплойки)
    (r"^kill\s+(npc|animal|deployed|entity)\b", "basic"),
    (r"^removalTool\b", "basic"),

    # --- full: напрямую влияет на игроков или на сам процесс сервера -------
    (r"^kill\b", "full"),          # kill <playerId> без уточнения — считаем игроком
    (r"^(kick|ban|banid|unban)\b", "full"),
    (r"^giveall\b", "full"),
    (r"^(quit|restart|shutdown)\b", "full"),
    (r"^oxide\.(grant|revoke|group)\b", "full"),  # управление правами плагинов
]


# Некоторые консольные реализации (в духе Source-движка) позволяют склеивать
# несколько команд в одной строке через ';' или перевод строки. Проверка
# только префикса позволила бы протащить опасную команду после безопасной
# (например "status; ban 123" совпало бы с правилом "status" -> safe).
# Поэтому строка сначала бьётся на сегменты, и берётся максимальный уровень
# среди них — это не даёт снизить итоговый уровень безопасным префиксом.
_COMMAND_SEPARATORS = re.compile(r"[;\n]")


def _required_level_single(command: str) -> str:
    cmd = command.strip()
    for pattern, level in COMMAND_RULES:
        if re.match(pattern, cmd, re.IGNORECASE):
            return level
    return DEFAULT_LEVEL_FOR_UNKNOWN


def required_level(command: str) -> str:
    """Определяет минимальный уровень доступа, необходимый для команды.

    Если строка содержит несколько команд, разделённых ';' или переводом
    строки, возвращается максимальный (самый строгий) уровень среди всех
    сегментов.
    """
    segments = [seg for seg in _COMMAND_SEPARATORS.split(command) if seg.strip()]
    if not segments:
        return DEFAULT_LEVEL_FOR_UNKNOWN
    return max((_required_level_single(seg) for seg in segments), key=_LEVEL_RANK.__getitem__)


def is_allowed(command: str, current_level: str) -> bool:
    """Проверяет, разрешена ли команда на заданном уровне доступа."""
    return _LEVEL_RANK[required_level(command)] <= _LEVEL_RANK[current_level]


def describe_level(level: str) -> str:
    """Человекочитаемое описание того, что разрешено на уровне."""
    descriptions = {
        "safe": "только чтение: статус, статистика, логи. Никакого влияния на игру.",
        "basic": "взаимодействие с миром (постройки, сущности, окружение), но не с игроками напрямую.",
        "full": "полный доступ: игроки, бан/кик, любые команды консоли без ограничений.",
    }
    return descriptions[level]