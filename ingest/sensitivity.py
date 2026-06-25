from __future__ import annotations

import logging
import re

from ingest.models import Page

logger = logging.getLogger(__name__)

_SENSITIVITY_RE = re.compile(r"sensitivity\s*:\s*restricted", re.IGNORECASE)


def is_ingestable(page: Page) -> bool:
    """Return False (and log) for pages marked sensitivity: restricted in front matter."""
    if _SENSITIVITY_RE.search(page.body[:500]):
        logger.warning("Skipping restricted page: %s", page.path)
        return False
    return True
