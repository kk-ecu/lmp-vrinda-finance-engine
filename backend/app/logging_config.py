"""Centralized logging setup.

Gives the app a single, consistent logger that writes structured, timestamped
lines to stdout (captured by `docker logs`). Use get_logger(__name__) anywhere
to emit step-level diagnostics so failures are localizable.
"""
from __future__ import annotations

import logging
import os
import sys

_CONFIGURED = False


def setup_logging() -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return
    level = os.getenv("LOG_LEVEL", "INFO").upper()
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s %(levelname)-7s [%(name)s] %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
        )
    )
    root = logging.getLogger("lmp")
    root.setLevel(level)
    root.handlers.clear()
    root.addHandler(handler)
    root.propagate = False
    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    setup_logging()
    # Namespacing under "lmp" so our logs are easy to grep and separate from uvicorn.
    short = name.replace("app.", "").replace("extraction_engine.", "ee.")
    return logging.getLogger(f"lmp.{short}")
