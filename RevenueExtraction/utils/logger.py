"""日誌工具"""
import logging
import os
from datetime import datetime
from config.settings import Settings

def setup_logger(settings: Settings = None):
    """設定系統日誌
    
    Args:
        settings: 設定物件
    """
    if settings is None:
        settings = Settings()
    
    # 創建logs目錄
    logs_dir = "logs"
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)
    
    # 設定日誌檔案名稱（以日期命名）
    log_filename = datetime.now().strftime("%Y%m%d.log")
    log_filepath = os.path.join(logs_dir, log_filename)
    
    # 獲取日誌配置
    log_level = settings.get('logging.level', 'INFO')
    log_format = settings.get('logging.format', '%(asctime)s - %(levelname)s: %(message)s')
    
    # 設定日誌
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format=log_format,
        handlers=[
            logging.FileHandler(log_filepath, encoding='utf-8'),
            logging.StreamHandler()  # 同時輸出到控制台
        ]
    )
    
    logging.info(f"日誌系統已初始化，日誌檔案: {log_filepath}")

def get_logger(name: str):
    """獲取日誌記錄器
    
    Args:
        name: 記錄器名稱
        
    Returns:
        logging.Logger: 日誌記錄器
    """
    return logging.getLogger(name)