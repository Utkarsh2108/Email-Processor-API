import logging
import os
from logging.handlers import RotatingFileHandler

def setup_logging():
    """Configures logging to output to both console and a rotating file."""
    
    # --- Create Logger Directory ---
    log_dir = "logger"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    log_file_path = os.path.join(log_dir, "app.log")

    # --- Create Logger ---
    logger = logging.getLogger()
    logger.setLevel(logging.INFO) 

    # --- Prevent duplicate handlers ---
    if logger.hasHandlers():
        logger.handlers.clear()

    # --- Formatter ---
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # --- Console Handler ---
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    # --- File Handler ---
    fh = RotatingFileHandler(
        log_file_path,
        maxBytes=5*1024*1024,  # 5 MB
        backupCount=3
    )
    fh.setLevel(logging.INFO)
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    logging.info("Logging configured successfully.")