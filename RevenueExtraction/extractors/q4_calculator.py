"""Q4營收計算器"""
import logging
from typing import Dict, List, Any
from models.revenue_store import RevenueStore

class Q4Calculator:
    def __init__(self, revenue_store: RevenueStore):
        """初始化Q4計算器
        
        Args:
            revenue_store: 營收資料庫
        """
        self.revenue_store = revenue_store
    
    def calculate_q4_revenue(self) -> bool:
        """計算Q4營收（全年 - Q1 - Q2 - Q3）
        
        Returns:
            bool: 是否計算成功
        """
        print("\n=== 計算Q4營收 ===")
        
        # 獲取全年和季度數據
        annual_data, quarterly_data_by_company = self.revenue_store.get_annual_and_quarterly_data()
        
        # 按公司年份分組全年數據
        companies_with_annual = {}
        for record in annual_data:
            company = record["company"]
            year = record["year_quarter"].split("_")[0]
            
            key = f"{company}_{year}"
            if key not in companies_with_annual:
                companies_with_annual[key] = []
            companies_with_annual[key].append(record)
        
        print(f"發現 {len(companies_with_annual)} 個公司年度組合")
        
        total_calculated = 0
        
        for company_year, annual_records in companies_with_annual.items():
            # 修正拆分邏輯：從右邊拆分，因為年份總是在最後
            parts = company_year.rsplit("_", 1)  # 從右邊拆分一次
            if len(parts) != 2:
                print(f"  警告: 無法解析公司年份組合: {company_year}")
                continue
            
            company, year = parts
            print(f"  調試：解析結果 - 公司: '{company}', 年份: '{year}'")
            
            for annual_record in annual_records:
                try:
                    # 調試：顯示正在搜尋的公司名稱
                    print(f"    調試：搜尋公司名稱: '{company}'")
                    
                    # 獲取對應的季度數據
                    quarterly_data = quarterly_data_by_company.get(company_year, [])
                    
                    print(f"  {company} {year}: 找到 {len(quarterly_data)} 筆季度數據")
                    
                    # 列出找到的季度數據
                    if quarterly_data:
                        quarters_found = [q["year_quarter"] for q in quarterly_data]
                        print(f"    季度數據: {quarters_found}")
                    
                    # 檢查是否有足夠的季度數據
                    if len(quarterly_data) == 0:
                        print(f"  警告: {company} {year} 沒有找到Q1-Q3數據，跳過Q4計算")
                        continue
                    
                    # 計算各季度總和
                    quarterly_total = sum(record["value"] for record in quarterly_data)
                    annual_value = annual_record["value"]
                    
                    # 計算Q4
                    q4_value = annual_value - quarterly_total
                    
                    print(f"  計算: {company} {year} Q4 = {annual_value:.2f} - {quarterly_total:.2f} = {q4_value:.2f}")
                    
                    if q4_value < 0:
                        print(f"  警告: {company} {year} Q4計算結果為負數: {q4_value:.2f}")
                        print(f"    全年營收: {annual_value:.2f}, Q1-Q3總計: {quarterly_total:.2f}")
                        print("    可能原因: 全年數據單位與季度數據單位不一致，或數據來源不同")
                    
                    # 構建計算說明
                    calculation_note = f"Q4 = 全年({annual_value:.2f}) - Q1-Q3({quarterly_total:.2f})"
                    
                    # 保存Q4數據
                    success = self.revenue_store.save_q4_record(
                        company, year, q4_value, calculation_note, annual_record
                    )
                    
                    if success:
                        if q4_value < 0:
                            print(f"  成功保存 Q4（負數警告）: {company} {year}: {q4_value:.2f} Million USD")
                        else:
                            print(f"  成功保存 Q4: {company} {year}: {q4_value:.2f} Million USD")
                        total_calculated += 1
                    else:
                        print(f"  保存失敗 Q4: {company} {year}")
                    
                    # 驗證插入結果
                    verification = self.revenue_store.revenue_collection.find_one({
                        "company": company,
                        "year_quarter": f"{year}_Q4"
                    })
                    if verification:
                        print(f"  驗證成功: Q4記錄已存在於資料庫中")
                    else:
                        print(f"  驗證失敗: Q4記錄未找到於資料庫中")
                        logging.error(f"Q4記錄插入驗證失敗: {company} {year}")
                    
                except Exception as e:
                    logging.error(f"計算Q4時發生錯誤 {company} {year}: {e}")
                    print(f"  錯誤: {company} {year} - {str(e)}")
                    continue
        
        print(f"\n=== Q4計算完成 ===")
        print(f"總計算/更新: {total_calculated} 筆Q4營收記錄")
        
        # 最終驗證：檢查所有Q4記錄
        q4_count = self.revenue_store.revenue_collection.count_documents({"year_quarter": {"$regex": "_Q4$"}})
        print(f"總營收 Q4記錄數量: {q4_count}")
        
        return total_calculated > 0
    
    def get_q4_calculation_summary(self) -> Dict[str, Any]:
        """獲取Q4計算摘要信息
        
        Returns:
            Dict[str, Any]: 摘要信息
        """
        try:
            # 統計全年數據
            annual_count = self.revenue_store.revenue_collection.count_documents(
                {"year_quarter": {"$regex": "_全年$"}}
            )
            
            # 統計Q1-Q3數據
            quarterly_count = self.revenue_store.revenue_collection.count_documents(
                {"year_quarter": {"$regex": "_Q[123]$"}}
            )
            
            # 統計Q4數據
            q4_count = self.revenue_store.revenue_collection.count_documents(
                {"year_quarter": {"$regex": "_Q4$"}}
            )
            
            # 統計負數Q4數據
            negative_q4_count = self.revenue_store.revenue_collection.count_documents({
                "year_quarter": {"$regex": "_Q4$"},
                "warning": "negative_value"
            })
            
            return {
                "annual_data_count": annual_count,
                "quarterly_data_count": quarterly_count,
                "q4_data_count": q4_count,
                "negative_q4_count": negative_q4_count,
                "can_calculate_q4": annual_count > 0
            }
            
        except Exception as e:
            logging.error(f"獲取Q4計算摘要時發生錯誤: {e}")
            return {
                "annual_data_count": 0,
                "quarterly_data_count": 0,
                "q4_data_count": 0,
                "negative_q4_count": 0,
                "can_calculate_q4": False
            }