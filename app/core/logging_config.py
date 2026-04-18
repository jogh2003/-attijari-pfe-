"""
logging_config.py — Configuration Loguru centralisée
PFE Attijari bank — Sujet 21

Usage dans chaque module :
    from app.core.logging_config import logger
"""
import os
import sys
from loguru import logger


def setup_logging(debug: bool = False) -> None:
    """Configure loguru pour stdout + fichier rotatif."""
    logger.remove()

    # ── Console (stdout) ──────────────────────────────────────
    level_console = "DEBUG" if debug else "INFO"
    logger.add(
        sys.stdout,
        level=level_console,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{line}</cyan> — "
            "<level>{message}</level>"
        ),
        colorize=True,
    )

    # ── Fichier rotatif (logs/) ───────────────────────────────
    os.makedirs("logs", exist_ok=True)
    logger.add(
        "logs/attijari_api_{time:YYYY-MM-DD}.log",
        level="DEBUG",
        rotation="00:00",          # nouveau fichier chaque jour
        retention="30 days",
        compression="zip",
        encoding="utf-8",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{line} — {message}",
        enqueue=True,              # thread-safe
    )

    logger.info("Logging initialisé — niveau console : {}", level_console)


# Exposer directement pour import simple
__all__ = ["logger", "setup_logging"]
