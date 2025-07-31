"""配置檔案讀取工具"""
import yaml
import os
from typing import Any, Dict

class Settings:
    def __init__(self, config_file: str = "config.yaml"):
        """初始化設定
        
        Args:
            config_file: 配置檔案路徑
        """
        self.config_file = config_file
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """載入YAML配置檔案"""
        try:
            config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), self.config_file)
            
            with open(config_path, 'r', encoding='utf-8') as file:
                return yaml.safe_load(file)
        except FileNotFoundError:
            raise FileNotFoundError(f"配置檔案 {self.config_file} 不存在")
        except yaml.YAMLError as e:
            raise ValueError(f"配置檔案格式錯誤: {e}")
    
    def get(self, key: str, default=None):
        """獲取配置值
        
        Args:
            key: 配置鍵，支援點號分隔的層級訪問，如 'mongodb.uri'
            default: 預設值
            
        Returns:
            配置值
        """
        keys = key.split('.')
        value = self.config
        
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default
    
    def get_openai_config(self) -> Dict[str, Any]:
        """獲取OpenAI相關配置"""
        return self.get('openai', {})
    
    def get_mongodb_config(self) -> Dict[str, Any]:
        """獲取MongoDB相關配置"""
        return self.get('mongodb', {})
    
    def get_rag_config(self) -> Dict[str, Any]:
        """獲取RAG相關配置"""
        return self.get('rag', {})
    
    def get_unit_conversion_map(self) -> Dict[str, float]:
        """獲取單位轉換映射表"""
        return self.get('unit_conversion', {})
    
    def get_exchange_rates(self) -> Dict[str, float]:
        """獲取匯率設定"""
        return self.get('exchange_rates', {})
    
    def get_excel_config(self) -> Dict[str, Any]:
        """獲取Excel輸出配置"""
        return self.get('excel_output', {})