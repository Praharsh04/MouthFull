"""Structured logging setup using Loguru.

Call `setup_logging()` once during application startup to configure
console and (optionally) file sinks. All other modules should import
logger from here:

    from voiceflow.core.logger import logger
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING

from loguru import logger

if TYPE_CHECKING:
    from voiceflow.core.config import AppConfig

# Remove the default Loguru sink so we control all output.
logger.remove()


def setup_logging(config: AppConfig) -> None:
    """Configure logging sinks based on application configuration.

    Parameters
    ----------
    config:
        The validated application configuration. The ``logging`` section
        controls log level, file path, rotation, and retention.
    """
    log_cfg = config.logging

    # Console sink — always enabled.
    logger.add(
        sys.stderr,
        level=log_cfg.level.upper(),
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level>"
        ),
        colorize=True,
    )

    # File sink — optional.
    if log_cfg.log_file:
        log_path = Path(log_cfg.log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        logger.add(
            str(log_path),
            level=log_cfg.level.upper(),
            format=(
                "{time:YYYY-MM-DD HH:mm:ss.SSS} | "
                "{level: <8} | "
                "{name}:{function}:{line} | "
                "{message}"
            ),
            rotation=log_cfg.rotation,
            retention=log_cfg.retention,
            encoding="utf-8",
        )

    logger.info("Logging initialised (level={})", log_cfg.level)
