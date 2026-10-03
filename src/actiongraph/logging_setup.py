"""Logging configuration shared by the CLI and the API server.

Modules never call ``print``; they do ``logger = logging.getLogger(__name__)``
and log. This function decides *where* those logs go and how they look.
"""

import logging


def configure_logging(level: str = "INFO") -> None:
    logging.basicConfig(
        level=level.upper(),
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    # Third-party libraries are chatty at INFO; keep them at WARNING.
    for noisy in ("httpx", "httpx2", "anthropic", "faster_whisper"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
