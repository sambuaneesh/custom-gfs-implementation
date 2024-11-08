import logging
import os
import sys
from datetime import datetime

class GFSLogger:
    _loggers = {}

    @staticmethod
    def get_logger(name: str) -> logging.Logger:
        if name not in GFSLogger._loggers:
            logger = logging.getLogger(name)
            logger.setLevel(logging.DEBUG)

            # Create logs directory if it doesn't exist
            os.makedirs('logs', exist_ok=True)

            # Create formatters
            detailed_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s - [%(filename)s:%(lineno)d]'
            )
            console_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )

            # File handler for detailed logging
            current_date = datetime.now().strftime('%Y-%m-%d')
            file_handler = logging.FileHandler(
                f'logs/{name}_{current_date}.log'
            )
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(detailed_formatter)

            # Console handler for basic logging
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(logging.INFO)
            console_handler.setFormatter(console_formatter)

            # Add handlers to logger
            logger.addHandler(file_handler)
            logger.addHandler(console_handler)

            GFSLogger._loggers[name] = logger

        return GFSLogger._loggers[name] 