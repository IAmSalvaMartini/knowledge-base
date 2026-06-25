#!/usr/bin/env python3
"""
Scheduled content refresh — runs ingest/run.py.

Invoke directly or via Windows Task Scheduler:
  python scripts/refresh.py

Task Scheduler action:
  Program:   python
  Arguments: C:\knowledgebase\scripts\refresh.py
  Start in:  C:\knowledgebase
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ingest.run import run

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)

if __name__ == "__main__":
    summary = run()
    logging.getLogger(__name__).info("Refresh complete: %s", summary)
