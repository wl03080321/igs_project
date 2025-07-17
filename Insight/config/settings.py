import yaml
import os
from typing import Dict, Any

class Settings:
    """系統設定管理類別"""
    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = config_path
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """載入YAML設定檔"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as file:
                config = yaml.safe_load(file)
            return config
        except FileNotFoundError:
            raise FileNotFoundError(f"設定檔 {self.config_path} 不存在")
        except yaml.YAMLError as e:
            raise ValueError(f"設定檔格式錯誤: {e}")
    
    def get(self, key_path: str, default=None):
        """
        獲取設定值，支援點號分隔的路徑
        例如: get("mongodb_settings.database_name")
        """
        keys = key_path.split('.')
        value = self.config
        
        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default
    
    def validate_required_settings(self) -> bool:
        """驗證必要設定是否完整"""
        required_settings = [
            "openai_settings.api_key",
            "mongodb_settings.uri",
            "mongodb_settings.database_name",
            "file_processing.base_directory"
        ]
        
        missing_settings = []
        
        for setting in required_settings:
            value = self.get(setting)
            if not value or "your-" in str(value):
                missing_settings.append(setting)
        
        if missing_settings:
            print("錯誤：以下必要設定缺失或未正確設定：")
            for setting in missing_settings:
                print(f"  - {setting}")
            return False
        
        return True
    
    # 便捷方法：直接獲取常用設定
    @property
    def openai_api_key(self) -> str:
        return self.get("openai_settings.api_key")
    
    @property
    def mongodb_uri(self) -> str:
        return self.get("mongodb_settings.uri")
    
    @property
    def database_name(self) -> str:
        return self.get("mongodb_settings.database_name")
    
    @property
    def collection_name(self) -> str:
        return self.get("mongodb_settings.collection_name")
    
    @property
    def analysis_collection_name(self) -> str:
        return self.get("mongodb_settings.analysis_collection_name")
    
    @property
    def base_directory(self) -> str:
        return self.get("file_processing.base_directory")
    
    @property
    def embedding_model(self) -> str:
        return self.get("vector_search.embedding_model")
    
    @property
    def llm_model(self) -> str:
        return self.get("openai_settings.llm_model")
    
    @property
    def vision_model(self) -> str:
        return self.get("openai_settings.vision_model")

# 全域設定實例
settings = Settings()