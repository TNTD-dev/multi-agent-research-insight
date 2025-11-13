"""
Logging utilities for the Multi-Agent Research System.
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Optional


def setup_logger(
    name: str = "multi_agent_research",
    log_level: str = "INFO",
    log_file: Optional[str] = "logs/research_pipeline.log",
    console_output: bool = True,
) -> logging.Logger:
    """
    Configure and return a logger instance.

    Args:
        name: Name of the logger.
        log_level: Logging level string.
        log_file: Optional log file path for detailed logs.
        console_output: Whether to output logs to stdout.
    """

    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    logger.handlers.clear()

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(funcName)s:%(lineno)d | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, log_level.upper(), logging.INFO))
        console_handler.setFormatter(
            logging.Formatter("%(levelname)s | %(message)s")
        )
        logger.addHandler(console_handler)

    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_path, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    logger.debug("Logger initialised: %s", name)
    return logger


default_logger = setup_logger()

