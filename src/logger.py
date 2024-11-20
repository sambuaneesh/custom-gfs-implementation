import logging
import os
import sys
from datetime import datetime
from colorama import init, Fore, Style, Back

# Initialize colorama for Windows compatibility
init(autoreset=True)

class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors"""
    COLORS = {
        'DEBUG': Fore.CYAN,
        'INFO': Fore.GREEN,
        'WARNING': Fore.YELLOW,
        'ERROR': Fore.RED,
        'CRITICAL': Fore.RED + Style.BRIGHT,
        # Custom levels for transaction stages
        'START': Back.WHITE + Fore.BLACK,
        'PREPARE': Back.MAGENTA + Fore.WHITE,
        'COMMIT': Back.BLUE + Fore.WHITE,
        'ROLLBACK': Back.RED + Fore.WHITE,
        'REPLICATE': Back.YELLOW + Fore.BLACK,
    }

    def format(self, record):
        # Get the appropriate color
        if hasattr(record, 'transaction_stage'):
            color = self.COLORS.get(record.transaction_stage, '')
        else:
            color = self.COLORS.get(record.levelname, '')

        # Format timestamp
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        
        # Create the colored message
        colored_msg = (
            f"{color}[{timestamp}] "
            f"{record.levelname} - "
            f"{record.getMessage()}{Style.RESET_ALL}"
        )
        
        return colored_msg

class GFSLogger:
    _loggers = {}

    @staticmethod
    def log_transaction(logger: logging.Logger, transaction_id: str, phase: str, message: str):
        """Log a transaction event with proper formatting and colors."""
        colors = {
            'START': Back.WHITE + Fore.BLACK,
            'PREPARE': Back.MAGENTA + Fore.WHITE,
            'COMMIT': Back.BLUE + Fore.WHITE,
            'ROLLBACK': Back.RED + Fore.WHITE,
            'REPLICATE': Back.YELLOW + Fore.BLACK
        }
        
        color = colors.get(phase, '')
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        
        formatted_message = (
            f"{color}[{timestamp}] "
            f"Transaction {transaction_id} - {phase}: "
            f"{message}{Style.RESET_ALL}"
        )
        
        # Print immediately to console
        print(formatted_message, flush=True)
        
        # Also log to file
        logger.info(message, extra={
            'transaction_id': transaction_id,
            'phase': phase
        })

    @staticmethod
    def get_logger(name: str) -> logging.Logger:
        if name not in GFSLogger._loggers:
            logger = logging.getLogger(name)
            logger.setLevel(logging.DEBUG)
            
            # Ensure the logger doesn't propagate to the root logger
            logger.propagate = False
            
            # Remove any existing handlers
            for handler in logger.handlers[:]:
                logger.removeHandler(handler)

            # Create logs directory if it doesn't exist
            os.makedirs('logs', exist_ok=True)

            # File handler for detailed logging
            current_date = datetime.now().strftime('%Y-%m-%d')
            file_handler = logging.FileHandler(
                f'logs/{name}_{current_date}.log',
                encoding='utf-8'
            )
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(logging.Formatter(
                '%(asctime)s.%(msecs)03d - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            ))

            # Console handler with colors
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(logging.INFO)
            console_handler.setFormatter(ColoredFormatter())

            # Add handlers to logger
            logger.addHandler(file_handler)
            logger.addHandler(console_handler)

            GFSLogger._loggers[name] = logger

        return GFSLogger._loggers[name]

    @staticmethod
    def get_transaction_logger(name: str) -> logging.Logger:
        """Get a special logger for transaction details."""
        logger_name = f"{name}_transactions"
        if logger_name not in GFSLogger._loggers:
            logger = logging.getLogger(logger_name)
            logger.setLevel(logging.DEBUG)
            logger.propagate = False
            
            # Remove any existing handlers
            for handler in logger.handlers[:]:
                logger.removeHandler(handler)

            # Create transaction logs directory
            os.makedirs('logs/transactions', exist_ok=True)

            # File handler for transaction logging
            current_date = datetime.now().strftime('%Y-%m-%d')
            file_handler = logging.FileHandler(
                f'logs/transactions/{name}_transactions_{current_date}.log',
                encoding='utf-8'
            )
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(logging.Formatter(
                '%(asctime)s.%(msecs)03d - %(transaction_id)s - %(phase)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            ))

            logger.addHandler(file_handler)
            GFSLogger._loggers[logger_name] = logger

        return GFSLogger._loggers[logger_name]