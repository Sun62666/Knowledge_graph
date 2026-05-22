import logging
import os
from utils.config import LOG_FILE_PATH

_logger_instance = None


def get_logger(name="KnowledgeGraph"):
    global _logger_instance
    if _logger_instance is not None:
        return _logger_instance

    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    if logger.handlers:
        _logger_instance = logger
        return _logger_instance

    fmt = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    os.makedirs(os.path.dirname(LOG_FILE_PATH), exist_ok=True)

    fh = logging.FileHandler(LOG_FILE_PATH, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    logger.propagate = False
    _logger_instance = logger
    return _logger_instance

if __name__ == "__main__":
    logger = get_logger()
    logger.info("测试")