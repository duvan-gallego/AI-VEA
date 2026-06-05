import logging


def configure_logging(log_level: str) -> None:
    logging.basicConfig(
        level=_resolve_log_level(log_level),
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )


def _resolve_log_level(log_level: str) -> int:
    resolved_level = getattr(logging, log_level.upper(), None)
    return resolved_level if isinstance(resolved_level, int) else logging.INFO
