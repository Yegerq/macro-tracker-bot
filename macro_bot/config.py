import os
from dataclasses import dataclass
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


@dataclass(frozen=True)
class Settings:
    bot_token: str
    timezone: ZoneInfo
    database_path: Path


def load_settings() -> Settings:
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not bot_token:
        raise RuntimeError("Environment variable TELEGRAM_BOT_TOKEN is required.")

    timezone_name = os.getenv("BOT_TIMEZONE", "Europe/Moscow")
    try:
        timezone = ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError as exc:
        raise RuntimeError("Unknown BOT_TIMEZONE value: {0}".format(timezone_name)) from exc

    database_path = Path(os.getenv("MACRO_BOT_DB", "data/macro_bot.sqlite3"))
    database_path.parent.mkdir(parents=True, exist_ok=True)

    return Settings(
        bot_token=bot_token,
        timezone=timezone,
        database_path=database_path,
    )
