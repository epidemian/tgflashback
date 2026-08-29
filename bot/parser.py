import re
from dataclasses import dataclass

from dateutil import parser as dateutil_parser

FLASHBACK_RE = re.compile(
    r"Flashback for\s+(?P<date>[A-Za-z]+\.?\s+\d{1,2},\s*\d{4})"
    r".*?(?P<score>\d+)\s+points",
    re.DOTALL | re.IGNORECASE,
)

# Matches the in-app "you scored" summary card, which (unlike the share text
# above) never states a date — just "this week's Flashback" regardless of
# which week it actually is.
FLASHBACK_SCREENSHOT_RE = re.compile(
    r"scored\s+(?P<score>\d{1,3})\s+of\s+(?P<total>\d{1,3})\s+points",
    re.IGNORECASE,
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


def parse_flashback_screenshot(text: str) -> int | None:
    """Extract the score from OCR'd text of the "you scored" summary card.

    Returns None if the text doesn't look like a Flashback score screenshot
    at all, so callers can silently ignore unrelated photos.
    """
    if not text or "flashback" not in text.lower():
        return None
    match = FLASHBACK_SCREENSHOT_RE.search(text)
    if not match:
        return None
    return int(match.group("score"))
