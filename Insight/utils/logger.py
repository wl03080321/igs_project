import logging
import os
from datetime import datetime
from config.settings import settings

def setup_logger():
    """設置日誌系統"""
    # 創建日誌目錄
    log_dir = settings.get("logging_settings.log_directory", "logs")
    os.makedirs(log_dir, exist_ok=True)
    
    # 設置日誌格式
    log_format = settings.get("logging_settings.format", "%(asctime)s - %(levelname)s: %(message)s")
    log_level = settings.get("logging_settings.level", "INFO")
    
    # 設置日誌檔案名稱（使用當前日期）
    current_date = datetime.now().strftime("%Y%m%d")
    log_file = os.path.join(log_dir, f"{current_date}.log")
    
    # 清除現有的處理器
    logging.getLogger().handlers.clear()
    
    # 配置日誌
    logging.basicConfig(
        level=getattr(logging, log_level),
        format=log_format,
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()  # 同時輸出到控制台
        ]
    )
    
    logger = logging.getLogger(__name__)
    logger.info(f"日誌系統初始化完成，日誌檔案：{log_file}")
    
    return logger

def get_logger(name: str = __name__):
    """獲取日誌記錄器"""
    return logging.getLogger(name)