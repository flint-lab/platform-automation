import logging
import os
import sys
from datetime import datetime

def get_logger(name="AutomationLogger"):
    logger = logging.getLogger(name)

    # Prevent duplicate handlers
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)

    # Reports directory
    log_dir = "artifacts/reports"
    os.makedirs(log_dir, exist_ok=True)

    # Date-wise log file (e.g. 17_06_2026.log)
    current_date = datetime.now().strftime("%d_%m_%Y")
    log_file = os.path.join(log_dir, f"{current_date}.log")

    # Formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # File handler
    file_handler = logging.FileHandler(
        log_file,
        mode="a",
        encoding="utf-8"
    )
    file_handler.setFormatter(formatter)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    logger.propagate = False

    return logger
