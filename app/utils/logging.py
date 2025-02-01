from logging import Logger, FileHandler, StreamHandler, Formatter, INFO
from pathlib import Path
from datetime import datetime

from app.config import config


class CustomLogger(Logger):
    def __init__(self, name: str):
        super().__init__(name)

        # Set log level from config
        level_name = config.LOG_LEVEL.upper()
        level = getattr(self, level_name, INFO)
        self.setLevel(level)

        # Create formatter
        formatter = Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

        # Create handlers
        # 1) File handler if LOG_DIR is set
        if config.LOG_DIR:
            log_dir_path = Path(config.LOG_DIR)
            log_dir_path.mkdir(parents=True, exist_ok=True)
            log_file = (
                log_dir_path
                / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_log.log"
            )
            file_handler = FileHandler(log_file)
            file_handler.setFormatter(formatter)
            self.addHandler(file_handler)

        # 2) Stream handler
        stream_handler = StreamHandler()
        stream_handler.setFormatter(formatter)
        self.addHandler(stream_handler)

        # Store exc_info flag
        self.exc_info = config.EXC_INFO

    def error(self, msg, *args, **kwargs):
        super().error(msg, *args, exc_info=self.exc_info, **kwargs)

    def warning(self, msg, *args, **kwargs):
        super().warning(msg, *args, exc_info=self.exc_info, **kwargs)
