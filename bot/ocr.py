import io
import logging

import pytesseract
from PIL import Image

from bot.parser import parse_flashback_screenshot

logger = logging.getLogger(__name__)


def extract_score(image_bytes: bytes) -> int | None:
    try:
        image = Image.open(io.BytesIO(image_bytes))
        text = pytesseract.image_to_string(image)
    except Exception:
        logger.exception("OCR failed on incoming photo")
        return None
    return parse_flashback_screenshot(text)
