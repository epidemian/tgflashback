import re
from dataclasses import dataclass

from dateutil import parser as dateutil_parser

FLASHBACK_RE = re.compile(
    r"Flashback for\s+(?P<date>[A-Za-z]+\.?\s+\d{1,2},\s*\d{4})"
    r".*?(?P<score>\d+)\s+points",
    re.DOTALL | re.IGNORECASE,
)


@dataclass
class FlashbackResult:
    puzzle_date: str  # ISO YYYY-MM-DD
    score: int


def parse_flashback_message(text: str) -> FlashbackResult | None:
    if not text:
        return None
    match = FLASHBACK_RE.search(text)
    if not match:
        return None
    try:
        parsed_date = dateutil_parser.parse(match.group("date"))
    except (ValueError, OverflowError):
        return None
    return FlashbackResult(
        puzzle_date=parsed_date.date().isoformat(),
        score=int(match.group("score")),
    )
