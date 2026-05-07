from __future__ import annotations

import logging


def configure_logging(level: str) -> None:
    resolved_level = getattr(logging, level.upper(), logging.ERROR)
    logging.basicConfig(
        level=resolved_level,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    logging.getLogger("httpx").setLevel(logging.ERROR)
    logging.getLogger("httpcore").setLevel(logging.ERROR)
