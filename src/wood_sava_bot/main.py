from __future__ import annotations

import asyncio
import logging

from wood_sava_bot.app import Application
from wood_sava_bot.config import get_settings
from wood_sava_bot.log_config import configure_logging


def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    app = Application(settings)

    try:
        asyncio.run(app.run())
    except KeyboardInterrupt:
        logging.getLogger(__name__).info("Shutdown requested by user")


if __name__ == "__main__":
    main()
