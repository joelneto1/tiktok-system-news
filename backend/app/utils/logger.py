import sys

from loguru import logger

# Remove default handler so we can configure our own
logger.remove()


def setup_logger(level: str = "INFO") -> None:
    """Configure loguru sinks. Call once at application startup."""
    # Remove any previously added handlers (idempotent on repeated calls)
    logger.remove()

    # Console sink — coloured, compact timestamp
    logger.add(
        sys.stderr,
        level=level.upper(),
        format="[{time:HH:mm:ss}] [{level}] {message}",
        colorize=True,
    )

    # File sink — rotated at 10 MB, kept for 7 days
    logger.add(
        "logs/app.log",
        level=level.upper(),
        format="[{time:HH:mm:ss}] [{level}] {message}",
        rotation="10 MB",
        retention="7 days",
        encoding="utf-8",
    )


__all__ = ["logger", "setup_logger"]
