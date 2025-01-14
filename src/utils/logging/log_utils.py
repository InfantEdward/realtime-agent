import os
from logging import (
    Logger,
    FileHandler,
    StreamHandler,
    Formatter,
    INFO,
)
from pathlib import Path
from datetime import datetime


class CustomLogger(Logger):
    def __init__(self, name: str):
        super().__init__(name)

        # Get log level, log directory, and exc_info from environment variables
        log_level = os.getenv("LOG_LEVEL", "INFO").upper()
        log_dir = os.getenv("LOG_DIR", None)
        exc_info = os.getenv("EXC_INFO", "False").lower() == "true"

        # Set log level
        level = getattr(self, log_level, INFO)
        self.setLevel(level)

        # Create formatter
        formatter = Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

        # Create handlers
        if log_dir:
            log_dir_path = Path(log_dir)
            log_dir_path.mkdir(
                parents=True, exist_ok=True
            )  # Create directory if it does not exist
            log_file = (
                log_dir_path
                / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_log.log"
            )
            file_handler = FileHandler(log_file)
            file_handler.setFormatter(formatter)
            self.addHandler(file_handler)

        stream_handler = StreamHandler()
        stream_handler.setFormatter(formatter)
        self.addHandler(stream_handler)

        # Store exc_info flag
        self.exc_info = exc_info

    def error(self, msg, *args, **kwargs):
        super().error(msg, *args, exc_info=self.exc_info, **kwargs)

    def warning(self, msg, *args, **kwargs):
        super().warning(msg, *args, exc_info=self.exc_info, **kwargs)


def get_custom_logger(name: str) -> CustomLogger:
    return CustomLogger(name)
