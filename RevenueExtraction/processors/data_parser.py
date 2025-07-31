"""數據解析處理"""
import json
import re
import logging
from typing import Dict, Any

class DataParser:
    def __init__(self):
        """初始化數據解析器"""
        pass
    
    def parse_revenue_response(self, response_text: str) -> Dict[str, Any]:
        """解析GPT回應並提取營收數據
        
        Args:
            response_text: GPT回應文本
            
        Returns:
            Dict[str, Any]: 解析後的營收數據
        """
        try:
            print(f"原始回應內容:")
            print(f"{'='*50}")
            print(response_text)
            print(f"{'='*50}")
            
            # 嘗試提取JSON部分
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            
            if json_start != -1 and json_end > json_start:
                json_text = response_text[json_start:json_end]
                print(f"提取的JSON文本:")
                print(json_text)
                
                # 嘗試修復常見的JSON格式問題
                json_text = self.fix_json_format(json_text)
                
                data = json.loads(json_text)
                return data
            else:
                logging.warning("無法找到JSON格式的回應")
                print("回應中沒有找到有效的JSON格式")
                return {"success": False, "data": []}
                
        except json.JSONDecodeError as e:
            logging.error(f"JSON解析錯誤: {e}")
            print(f"JSON解析失敗，錯誤: {e}")
            print(f"嘗試解析的JSON: {json_text if 'json_text' in locals() else '未提取到JSON'}")
            return {"success": False, "data": []}
        except Exception as e:
            logging.error(f"解析回應時發生錯誤: {e}")
            print(f"解析錯誤: {e}")
            return {"success": False, "data": []}
    
    def fix_json_format(self, json_text: str) -> str:
        """修復常見的JSON格式問題
        
        Args:
            json_text: 原始JSON文本
            
        Returns:
            str: 修復後的JSON文本
        """
        try:
            # 移除可能的markdown標記
            json_text = json_text.replace('```json', '').replace('```', '')
            
            # 修復單引號為雙引號
            # 修復屬性名的單引號
            json_text = re.sub(r"'([^']+)':", r'"\1":', json_text)
            # 修復值的單引號
            json_text = re.sub(r": '([^']*)'", r': "\1"', json_text)
            
            # 移除註解
            json_text = re.sub(r'//.*?\n', '\n', json_text)
            
            # 修復尾隨逗號
            json_text = re.sub(r',(\s*[}\]])', r'\1', json_text)
            
            return json_text.strip()
            
        except Exception as e:
            logging.warning(f"JSON修復失敗: {e}")
            return json_text