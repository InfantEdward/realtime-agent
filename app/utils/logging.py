from logging import Logger, FileHandler, StreamHandler, Formatter
from pathlib import Path
from datetime import datetime
from app.config import get_app_config


class CustomLogger(Logger):
    def __init__(self, name: str):
        super().__init__(name)

        app_config = get_app_config()
        # Set log level from AppConfigModel
        level = app_config.LOG_LEVEL if app_config else "INFO"
        self.setLevel(level)

        # Create formatter
        formatter = Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

        # Create handlers
        # 1) File handler if LOG_DIR is set
        if app_config and app_config.LOG_DIR:
            log_dir_path = Path(app_config.LOG_DIR)
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
        self.exc_info = app_config.EXC_INFO if app_config else False

    def error(self, msg, *args, **kwargs):
        super().error(msg, *args, exc_info=self.exc_info, **kwargs)

    def warning(self, msg, *args, **kwargs):
        super().warning(msg, *args, exc_info=self.exc_info, **kwargs)
