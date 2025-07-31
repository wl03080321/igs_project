"""單位轉換處理"""
import re
import logging
from typing import Union
from config.settings import Settings

class UnitConverter:
    def __init__(self, settings: Settings):
        """初始化單位轉換器
        
        Args:
            settings: 設定物件
        """
        self.settings = settings
        self.unit_conversion_map = settings.get_unit_conversion_map()
        self.exchange_rates = settings.get_exchange_rates()
    
    def normalize_unit_name(self, unit_str: Union[str, None]) -> str:
        """標準化單位名稱
        
        Args:
            unit_str: 原始單位字串
            
        Returns:
            str: 標準化後的單位名稱
        """
        if not unit_str:
            return ''
        
        # 轉換為小寫並去除空格
        unit_str = str(unit_str).lower().strip()
        
        # 去除常見的前後綴
        unit_str = unit_str.replace('in ', '').replace('($)', '').replace('(', '').replace(')', '')
        unit_str = unit_str.replace('$', '').replace('usd', '').replace('krw', '').replace('원', '')
        
        # 處理常見的變體
        unit_str = unit_str.replace('mln', 'million')
        unit_str = unit_str.replace('bln', 'billion')
        unit_str = unit_str.replace('tln', 'trillion')
        
        return unit_str.strip()
    
    def convert_to_million_usd(self, value: Union[str, float, int], unit: str, currency: str) -> float:
        """將數值轉換為百萬美元單位
        
        Args:
            value: 原始數值
            unit: 單位
            currency: 幣別
            
        Returns:
            float: 轉換後的數值（百萬美元）
        """
        try:
            # 確保 value 是數字
            if isinstance(value, str):
                # 去除逗號和其他非數字字符（保留小數點和負號）
                value = re.sub(r'[^\d.-]', '', value)
                value = float(value)
            else:
                value = float(value)
            
            # 標準化單位名稱
            normalized_unit = self.normalize_unit_name(unit)
            
            # 獲取單位轉換係數，如果不在映射表中則保持原值
            unit_multiplier = self.unit_conversion_map.get(normalized_unit, 1.0)
            
            # 轉換為百萬單位
            value_in_millions = value * unit_multiplier
            
            # 轉換貨幣為美元
            exchange_rate_key = f"{currency}_to_USD"
            exchange_rate = self.exchange_rates.get(exchange_rate_key, 1.0)
            
            if currency == "KRW":
                value_in_millions_usd = value_in_millions * self.exchange_rates.get('KRW_to_USD', 0.000714)
            elif currency == "USD":
                value_in_millions_usd = value_in_millions
            else:
                logging.warning(f"未知幣別: {currency}，假設為美元")
                value_in_millions_usd = value_in_millions
            
            logging.info(f"單位轉換: {value} {unit} {currency} -> {value_in_millions_usd:.2f} Million USD")
            
            return value_in_millions_usd
            
        except Exception as e:
            logging.error(f"單位轉換錯誤: {e}")
            # 如果轉換失敗，回退到原始邏輯
            try:
                if currency == "KRW":
                    return float(value) / 1400
                else:
                    return float(value)
            except:
                return 0.0