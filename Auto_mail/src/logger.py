import logging
from logging.handlers import RotatingFileHandler
import os
from datetime import datetime
from pathlib import Path

class Logger:
    def __init__(self, name="AutoMailLogger"):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)
        # 建立 logs 目錄（如果不存在）
        if not self.logger.hasHandlers():
            if not os.path.exists('logs'):
                os.makedirs('logs')
            # 設定日誌檔案名稱（包含日期）
            log_filename = Path(__file__).parent.parent / f"logs/{datetime.now().strftime('%Y-%m-%d')}.log"
            # 設定檔案處理器（RotatingFileHandler，最大 5MB，保留 5 個備份）
            file_handler = RotatingFileHandler(
                log_filename,
                maxBytes=5*1024*1024,  # 5MB
                backupCount=5,
                encoding='utf-8'
            )
            
            file_handler.setLevel(logging.INFO)
            # 設定控制台處理器
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)
            # 設定日誌格式
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            file_handler.setFormatter(formatter)
            console_handler.setFormatter(formatter)
            # 添加處理器到 logger
            self.logger.addHandler(file_handler)
            self.logger.addHandler(console_handler)
    
    def info(self, message):
        """記錄資訊級別的日誌"""
        self.logger.info(message)

    def warning(self, message):
        """記錄警告級別的日誌"""
        self.logger.warning(message)

    def error(self, message):
        """記錄錯誤級別的日誌"""
        self.logger.error(message)

    def debug(self, message):
        """記錄除錯級別的日誌"""
        self.logger.debug(message)

    def critical(self, message):
        """記錄重大錯誤級別的日誌"""
        self.logger.critical(message)
