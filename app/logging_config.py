from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


LOG_DIR = Path("logs")


def configure_logging() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    root = logging.getLogger()
    root.setLevel(logging.INFO)

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        "%Y-%m-%d %H:%M:%S",
    )

    console = logging.StreamHandler()
    console.setFormatter(formatter)

    app_file = RotatingFileHandler(LOG_DIR / "app.log", maxBytes=2_000_000, backupCount=5, encoding="utf-8")
    app_file.setFormatter(formatter)

    error_file = RotatingFileHandler(LOG_DIR / "errors.log", maxBytes=2_000_000, backupCount=5, encoding="utf-8")
    error_file.setLevel(logging.ERROR)
    error_file.setFormatter(formatter)

    admin_file = RotatingFileHandler(LOG_DIR / "admin_actions.log", maxBytes=2_000_000, backupCount=5, encoding="utf-8")
    admin_file.setFormatter(formatter)

    booking_file = RotatingFileHandler(LOG_DIR / "bookings.log", maxBytes=2_000_000, backupCount=5, encoding="utf-8")
    booking_file.setFormatter(formatter)

    if not root.handlers:
        root.addHandler(console)
        root.addHandler(app_file)
        root.addHandler(error_file)

    admin_logger = logging.getLogger("admin_actions")
    admin_logger.setLevel(logging.INFO)
    if not admin_logger.handlers:
        admin_logger.addHandler(admin_file)

    booking_logger = logging.getLogger("booking_events")
    booking_logger.setLevel(logging.INFO)
    if not booking_logger.handlers:
        booking_logger.addHandler(booking_file)
