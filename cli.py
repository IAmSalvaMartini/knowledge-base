#!/usr/bin/env python3
"""
kb — Knowledge Base CLI

Usage:
  kb ask "<question>"
  kb ingest [--force]
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

# Ensure project root is on sys.path when run directly
sys.path.insert(0, str(Path(__file__).resolve().parent))


def _set_cli_auth() -> None:
    """Inject CLI token into env so the retrieval stack can pick it up if needed."""
    from config import load_config
    cfg = load_config()
    if not cfg.anthropic_api_key:
        print("ERROR: ANTHROPIC_API_KEY not set. Check your .env file.", file=sys.stderr)
        sys.exit(1)


def cmd_ask(question: str) -> None:
    _set_cli_auth()
    from retrieval.generator import answer
    result = answer(question)
    print(result.text)
    if result.citations:
        print("\nSources:")
        for citation in result.citations:
            print(f"  - {citation}")


def cmd_ingest(force: bool = False) -> None:
    from ingest.run import run
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    summary = run(force=force)
    print(f"Ingest complete: {summary}")


def main() -> None:
    parser = argparse.ArgumentParser(prog="kb", description="Knowledge Base CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    ask_p = sub.add_parser("ask", help="Ask the knowledge base a question")
    ask_p.add_argument("question", help="The question to ask")

    ingest_p = sub.add_parser("ingest", help="Run the ingestion pipeline")
    ingest_p.add_argument("--force", action="store_true", help="Re-embed all pages, ignoring stored hashes")

    args = parser.parse_args()

    if args.command == "ask":
        cmd_ask(args.question)
    elif args.command == "ingest":
        cmd_ingest(force=args.force)


if __name__ == "__main__":
    main()
