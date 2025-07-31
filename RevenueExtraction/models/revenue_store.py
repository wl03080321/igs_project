"""MongoDB營收資料庫類別"""
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from config.settings import Settings
from utils.mongodb_utils import create_mongodb_client, get_database_and_collections, create_indexes

class RevenueStore:
    def __init__(self, settings: Settings):
        """初始化營收資料庫
        
        Args:
            settings: 設定物件
        """
        self.settings = settings
        self.client = create_mongodb_client(settings)
        self.db, self.embedding_collection, self.revenue_collection = get_database_and_collections(
            self.client, settings
        )
        
        # 創建索引
        create_indexes(self.revenue_collection)
    
    def get_processed_companies_quarters(self) -> Dict[str, List[str]]:
        """獲取已處理的公司和季度組合
        
        Returns:
            Dict[str, List[str]]: 公司名稱對應的季度列表
        """
        try:
            pipeline = [
                {
                    "$group": {
                        "_id": {
                            "company": "$metadata.company_name",
                            "quarter": "$metadata.quarter"
                        }
                    }
                },
                {
                    "$sort": {
                        "_id.company": 1,
                        "_id.quarter": 1
                    }
                }
            ]
            
            company_quarters = list(self.embedding_collection.aggregate(pipeline))
            
            # 按公司分組
            companies_data = {}
            for item in company_quarters:
                company = item['_id']['company']
                quarter = item['_id']['quarter']
                
                if company not in companies_data:
                    companies_data[company] = []
                companies_data[company].append(quarter)
            
            return companies_data
            
        except Exception as e:
            logging.error(f"獲取公司季度資訊時發生錯誤: {e}")
            return {}
    
    def check_existing_revenue_data(self, company: str, quarter: str) -> bool:
        """檢查是否已有營收數據
        
        Args:
            company: 公司名稱
            quarter: 季度
            
        Returns:
            bool: 是否已存在數據
        """
        count = self.revenue_collection.count_documents({
            "company": company,
            "year_quarter": quarter
        })
        return count > 0
    
    def save_revenue_data(self, company: str, year_quarter: str, revenue_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """保存營收數據到MongoDB
        
        Args:
            company: 公司名稱
            year_quarter: 年份季度
            revenue_data: 營收數據
            
        Returns:
            List[Dict[str, Any]]: 保存的記錄列表
        """
        from processors.unit_converter import UnitConverter
        
        saved_records = []
        current_time = datetime.now()
        unit_converter = UnitConverter(self.settings)
        
        try:
            for item in revenue_data.get('data', []):
                revenue_type = item.get('type')
                name = item.get('name')
                value = item.get('value')
                unit = item.get('unit', '')
                original_currency = item.get('original_currency', 'USD')
                
                if not all([revenue_type, name, value]):
                    continue
                
                try:
                    usd_value_millions = unit_converter.convert_to_million_usd(value, unit, original_currency)
                except Exception as e:
                    logging.error(f"單位轉換失敗: {e}, 使用回退處理")
                    # 回退處理
                    try:
                        if original_currency == "KRW":
                            usd_value_millions = float(value) / 1400
                        else:
                            usd_value_millions = float(value)
                    except:
                        usd_value_millions = 0.0
                
                # 只處理總營收
                if revenue_type == 'total_revenue':
                    # 根據季度類型設置data_type
                    if year_quarter.endswith('_全年'):
                        data_type = "actual_fullyear"
                    else:
                        data_type = "actual"
                    
                    record = {
                        "company": company,
                        "year_quarter": year_quarter,
                        "value": usd_value_millions,
                        "original_value": float(value),
                        "original_unit": unit, 
                        "original_currency": original_currency,
                        "data_type": data_type,
                        "created_at": current_time
                    }
                    
                    # 使用 upsert 避免重複
                    filter_criteria = {
                        "company": company,
                        "year_quarter": year_quarter
                    }
                    
                    result = self.revenue_collection.update_one(
                        filter_criteria,
                        {"$set": record},
                        upsert=True
                    )
                    
                    action = "inserted" if result.upserted_id else "updated"
                    saved_records.append({
                        "action": action,
                        "type": revenue_type,
                        "company": company,
                        "year_quarter": year_quarter,
                        "name": name,
                        "value": usd_value_millions,
                        "original_value": float(value),
                        "original_unit": unit,
                        "original_currency": original_currency
                    })
                    
                    logging.info(f"{action} {revenue_type}: {company} - {year_quarter} - {name}: {usd_value_millions:.2f} Million USD (原始: {value} {unit} {original_currency})")
            
            return saved_records
            
        except Exception as e:
            logging.error(f"保存營收數據時發生錯誤: {e}")
            return []
    
    def get_all_revenue_data(self) -> List[Dict[str, Any]]:
        """獲取所有營收數據
        
        Returns:
            List[Dict[str, Any]]: 營收數據列表
        """
        return list(self.revenue_collection.find().sort([("company", 1), ("year_quarter", 1)]))
    
    def clear_revenue_data(self) -> bool:
        """清空營收數據
        
        Returns:
            bool: 是否成功清空
        """
        try:
            count = self.revenue_collection.count_documents({})
            if count > 0:
                self.revenue_collection.delete_many({})
                logging.info(f"清空總營收: {count} 筆記錄")
                return True
            else:
                logging.info("總營收: 無記錄")
                return False
                
        except Exception as e:
            logging.error(f"清空營收集合時發生錯誤: {e}")
            return False
    
    def get_annual_and_quarterly_data(self):
        """獲取全年和季度數據用於Q4計算
        
        Returns:
            tuple: (annual_data, quarterly_data_by_company)
        """
        # 獲取全年數據
        annual_data = list(self.revenue_collection.find({"year_quarter": {"$regex": "_全年$"}}))
        
        # 獲取Q1-Q3數據
        quarterly_data = list(self.revenue_collection.find({"year_quarter": {"$regex": "_Q[123]$"}}))
        
        # 按公司和年份分組季度數據
        quarterly_data_by_company = {}
        for record in quarterly_data:
            company = record["company"]
            year_quarter = record["year_quarter"]
            year = year_quarter.split("_")[0]
            
            key = f"{company}_{year}"
            if key not in quarterly_data_by_company:
                quarterly_data_by_company[key] = []
            quarterly_data_by_company[key].append(record)
        
        return annual_data, quarterly_data_by_company
    
    def save_q4_record(self, company: str, year: str, q4_value: float, calculation_note: str, 
                      original_record: Optional[Dict[str, Any]] = None) -> bool:
        """保存Q4記錄
        
        Args:
            company: 公司名稱
            year: 年份
            q4_value: Q4營收值
            calculation_note: 計算說明
            original_record: 原始年度記錄（用於繼承原始數據字段）
            
        Returns:
            bool: 是否保存成功
        """
        try:
            # 構建Q4記錄 
            q4_record = {
                "company": company,  
                "year_quarter": f"{year}_Q4",
                "value": q4_value,
                "data_type": "actual",
                "created_at": datetime.now(),
                "calculation_note": calculation_note
            }
            
            # 添加原始數據字段（繼承自全年記錄）
            if original_record:
                if 'original_value' in original_record:
                    q4_record['original_value'] = q4_value
                if 'original_unit' in original_record:
                    q4_record['original_unit'] = original_record.get('original_unit', '')
                if 'original_currency' in original_record:
                    q4_record['original_currency'] = original_record.get('original_currency', 'USD')
            
            # 如果是負數，添加警告標記
            if q4_value < 0:
                q4_record['warning'] = "negative_value"
                q4_record['warning_note'] = "Q4計算結果為負數，可能存在數據單位不一致問題"
            
            # 構建查詢條件用於upsert
            filter_criteria = {
                "company": company,
                "year_quarter": f"{year}_Q4"
            }
            
            # 保存Q4數據到MongoDB
            result = self.revenue_collection.update_one(
                filter_criteria,
                {"$set": q4_record},
                upsert=True
            )
            
            return True
            
        except Exception as e:
            logging.error(f"保存Q4記錄時發生錯誤: {e}")
            return False