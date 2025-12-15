# cisco_config_manager/core/utils.py
import logging
import os
from datetime import datetime
from logging.handlers import RotatingFileHandler


class AppLogger:
    """애플리케이션 전역 로깅 클래스"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AppLogger, cls).__new__(cls)
            cls._instance._setup_logger()
        return cls._instance

    def _setup_logger(self):
        """로거 설정 (콘솔 + 파일)"""
        self.utils = logging.getLogger("CiscoConfigManager")
        self.utils.setLevel(logging.DEBUG)

        # 로그 저장 디렉토리 생성
        log_dir = os.path.expanduser("~/.cisco_config_manager/logs")
        os.makedirs(log_dir, exist_ok=True)

        # 로그 파일명 (날짜별)
        log_file = os.path.join(log_dir, f"app_{datetime.now().strftime('%Y%m%d')}.log")

        # 포맷 설정
        formatter = logging.Formatter(
            '[%(asctime)s] [%(levelname)s] [%(module)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        # 1. 파일 핸들러 (10MB 단위, 최대 5개 백업)
        file_handler = RotatingFileHandler(
            log_file, maxBytes=10 * 1024 * 1024, backupCount=5, encoding='utf-8'
        )
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(formatter)

        # 2. 콘솔 핸들러 (개발용)
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(formatter)

        # 핸들러 추가
        if not self.utils.handlers:
            self.utils.addHandler(file_handler)
            self.utils.addHandler(console_handler)

    def log_info(self, message: str):
        self.utils.info(message)

    def log_warning(self, message: str):
        self.utils.warning(message)

    def log_error(self, message: str):
        self.utils.error(message)

    def log_exception(self, message: str):
        self.utils.exception(message)


# 전역 사용을 위한 인스턴스
app_logger = AppLogger()