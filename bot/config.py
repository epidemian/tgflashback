import os

from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]

_admin_id = os.getenv("ADMIN_TELEGRAM_ID")
ADMIN_TELEGRAM_ID = int(_admin_id) if _admin_id else None

DB_PATH = os.getenv("DB_PATH", "flashback.db")

PLAYER_CODES = ["Se", "Mb", "Na", "Ra", "²H"]

# Alt spellings players might type for /soy, normalized to lowercase without
# accents/superscripts since "²H" is awkward to type on a phone keyboard.
CODE_ALIASES = {
    "se": "Se",
    "mb": "Mb",
    "na": "Na",
    "ra": "Ra",
    "²h": "²H",
    "2h": "²H",
    "h2": "²H",
    "hh": "²H",
}


def normalize_code(text: str) -> str | None:
    if text is None:
        return None
    return CODE_ALIASES.get(text.strip().lower())
