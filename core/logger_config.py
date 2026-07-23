import os
import sys
import logging

def setup_logger(name: str = "dit_copy_pro") -> logging.Logger:
    """
    Sets up a application-wide logger configured for console and file output.
    """
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s")

    # Console Handler
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    # File Handler
    try:
        cache_dir = os.path.expanduser("~/.cache/dit_copy_pro")
        os.makedirs(cache_dir, exist_ok=True)
        log_file = os.path.join(cache_dir, "app.log")
        fh = logging.FileHandler(log_file, encoding="utf-8")
        fh.setLevel(logging.INFO)
        fh.setFormatter(formatter)
        logger.addHandler(fh)
    except Exception:
        pass

    return logger

logger = setup_logger()
