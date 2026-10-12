import logging
import re
import sys
from typing import Any

class SensitiveDataFilter(logging.Filter):
    """
    Redacts sensitive tokens, API keys (e.g. gsk_*, passwords) from logs.
    """
    PATTERNS = [
        re.compile(r'gsk_[a-zA-Z0-9]{30,}'),
        re.compile(r'password["\']?\s*[:=]\s*["\']?[^"\'\s,]+["\']?', re.IGNORECASE),
        re.compile(r'authorization:\s*bearer\s+[^\s]+', re.IGNORECASE),
    ]

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            for pattern in self.PATTERNS:
                record.msg = pattern.sub("[REDACTED_SECRET]", record.msg)
        if record.args:
            if isinstance(record.args, dict):
                redacted = {}
                for k, v in record.args.items():
                    if any(secret_kw in k.lower() for secret_kw in ["key", "pass", "token", "secret", "auth"]):
                        redacted[k] = "[REDACTED]"
                    else:
                        redacted[k] = v
                record.args = redacted
            elif isinstance(record.args, tuple):
                record.args = tuple(
                    "[REDACTED]" if isinstance(arg, str) and any(p.search(arg) for p in self.PATTERNS) else arg
                    for arg in record.args
                )
        return True

def setup_logging(level: str = "INFO") -> logging.Logger:
    logger = logging.getLogger("meta_graph")
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    
    # Avoid duplicate handlers
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        handler.setFormatter(formatter)
        handler.addFilter(SensitiveDataFilter())
        logger.addHandler(handler)
        logger.propagate = False

    return logger

logger = setup_logging()
