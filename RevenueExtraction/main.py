"""財報營收數據提取系統主程式"""
import time
import logging
from datetime import datetime

from config.settings import Settings
from models.revenue_store import RevenueStore
from extractors.rag_extractor import RAGExtractor
from extractors.q4_calculator import Q4Calculator
from exporters.excel_exporter import ExcelExporter
from utils.logger import setup_logger

def test_connections(settings: Settings) -> bool:
    """測試API和模型連接
    
    Args:
        settings: 設定物件
        
    Returns:
        bool: 是否所有連接都正常
    """
    print("=== 測試系統連接 ===")
    
    # 測試 OpenAI API 連接
    try:
        from openai import OpenAI
        openai_config = settings.get_openai_config()
        client = OpenAI(api_key=openai_config.get('api_key'))
        
        test_response = client.chat.completions.create(
            model=openai_config.get('model', 'gpt-4.1'),
            messages=[{"role": "user", "content": "測試連接"}],
            max_tokens=10
        )
        print("GPT-4.1 API 連接成功")
    except Exception as e:
        print(f"GPT-4.1 API 連接失敗: {e}")
        return False

    # 測試 SentenceTransformer 模型
    try:
        from sentence_transformers import SentenceTransformer
        rag_config = settings.get_rag_config()
        model_name = rag_config.get('embedding_model', 'paraphrase-multilingual-MiniLM-L12-v2')
        embedding_model = SentenceTransformer(model_name)
        
        test_embedding = embedding_model.encode("測試", convert_to_tensor=False)
        print(f"SentenceTransformer 載入成功，維度: {len(test_embedding)}")
    except Exception as e:
        print(f"SentenceTransformer 模型載入失敗: {e}")
        return False

    return True

def check_database_status(revenue_store: RevenueStore) -> dict:
    """檢查資料庫狀態
    
    Args:
        revenue_store: 營收資料庫
        
    Returns:
        dict: 資料庫狀態資訊
    """
    try:
        existing_embeddings = revenue_store.embedding_collection.count_documents({})
        existing_revenue = revenue_store.revenue_collection.count_documents({})
        
        status = {
            'embeddings_count': existing_embeddings,
            'revenue_count': existing_revenue,
            'has_embeddings': existing_embeddings > 0,
            'has_revenue': existing_revenue > 0
        }
        
        print(f"\n目前資料庫狀態:")
        print(f"- 嵌入文檔: {existing_embeddings} 個")
        print(f"- 總營收記錄: {existing_revenue} 個")
        
        return status
        
    except Exception as e:
        logging.error(f"檢查資料庫狀態時發生錯誤: {e}")
        return {
            'embeddings_count': 0,
            'revenue_count': 0,
            'has_embeddings': False,
            'has_revenue': False
        }

def get_user_choice() -> str:
    """獲取使用者選擇
    
    Returns:
        str: 使用者選擇的選項
    """
    print("\n請選擇營收提取模式:")
    print("1. 完整重新提取")
    print("2. 增量提取")
    print("3. 只匯出現有數據到Excel")
    print("4. 清空所有營收數據")
    print("5. 單獨計算Q4營收")
    print("6. 退出")
    
    choice = input("請輸入選項 (1-6): ").strip()
    return choice

def handle_full_extraction(rag_extractor: RAGExtractor, revenue_store: RevenueStore, 
                         excel_exporter: ExcelExporter) -> bool:
    """處理完整重新提取
    
    Args:
        rag_extractor: RAG提取器
        revenue_store: 營收資料庫
        excel_exporter: Excel匯出器
        
    Returns:
        bool: 是否處理成功
    """
    print("\n=== 完整重新提取營收數據 ===")
    confirm = input("這將清空所有現有營收數據，確定要繼續嗎？(y/N): ").lower()
    
    if confirm != 'y':
        print("取消操作")
        return False
    
    print("清空現有營收數據...")
    revenue_store.clear_revenue_data()
    
    print("開始提取營收數據...")
    success = extract_all_revenue_data(rag_extractor, force_reprocess=True)
    
    if success:
        print(f"\n匯出數據到Excel...")
        return excel_exporter.export_revenue_data(revenue_store)
    else:
        print("營收數據提取失敗")
        return False

def handle_incremental_extraction(rag_extractor: RAGExtractor, revenue_store: RevenueStore, 
                                excel_exporter: ExcelExporter, db_status: dict) -> bool:
    """處理增量提取
    
    Args:
        rag_extractor: RAG提取器
        revenue_store: 營收資料庫
        excel_exporter: Excel匯出器
        db_status: 資料庫狀態
        
    Returns:
        bool: 是否處理成功
    """
    print("\n=== 增量提取營收數據 ===")
    success = extract_all_revenue_data(rag_extractor, force_reprocess=False)
    
    if success or db_status['has_revenue']:
        print(f"\n匯出數據到Excel...")
        return excel_exporter.export_revenue_data(revenue_store)
    else:
        print("沒有營收數據可以匯出")
        return False

def handle_export_only(excel_exporter: ExcelExporter, revenue_store: RevenueStore, 
                      db_status: dict) -> bool:
    """處理只匯出現有數據
    
    Args:
        excel_exporter: Excel匯出器
        revenue_store: 營收資料庫
        db_status: 資料庫狀態
        
    Returns:
        bool: 是否處理成功
    """
    if db_status['has_revenue']:
        print(f"\n匯出現有數據到Excel...")
        return excel_exporter.export_revenue_data(revenue_store)
    else:
        print("沒有營收數據可以匯出")
        return False

def handle_clear_data(revenue_store: RevenueStore) -> bool:
    """處理清空營收數據
    
    Args:
        revenue_store: 營收資料庫
        
    Returns:
        bool: 是否處理成功
    """
    print("\n=== 清空營收數據 ===")
    confirm = input("確定要清空所有營收數據嗎？(y/N): ").lower()
    
    if confirm == 'y':
        success = revenue_store.clear_revenue_data()
        if success:
            print("營收數據已清空")
        return success
    else:
        print("取消操作")
        return False

def handle_q4_calculation(q4_calculator: Q4Calculator, excel_exporter: ExcelExporter, 
                         revenue_store: RevenueStore) -> bool:
    """處理Q4營收計算
    
    Args:
        q4_calculator: Q4計算器
        excel_exporter: Excel匯出器
        revenue_store: 營收資料庫
        
    Returns:
        bool: 是否處理成功
    """
    print("\n=== 單獨計算Q4營收 ===")
    
    # 獲取Q4計算摘要
    summary = q4_calculator.get_q4_calculation_summary()
    
    print(f"發現全年數據: {summary['annual_data_count']} 筆")
    print(f"發現Q1-Q3數據: {summary['quarterly_data_count']} 筆")
    
    if not summary['can_calculate_q4']:
        print("沒有找到全年營收數據，無法計算Q4")
        print("請先執行完整提取或增量提取以獲取全年數據")
        return False
    
    confirm = input("是否開始計算Q4營收？(y/N): ").lower()
    
    if confirm != 'y':
        print("取消Q4計算")
        return False
    
    success = q4_calculator.calculate_q4_revenue()
    
    if success:
        print("\nQ4營收計算完成！")
        
        # 詢問是否匯出到Excel
        export_choice = input("是否匯出更新後的數據到Excel？(y/N): ").lower()
        if export_choice == 'y':
            print(f"\n匯出數據到Excel...")
            return excel_exporter.export_revenue_data(revenue_store)
        return True
    else:
        print("Q4營收計算失敗")
        return False

def extract_all_revenue_data(rag_extractor: RAGExtractor, force_reprocess: bool = False) -> bool:
    """提取所有公司的總營收數據
    
    Args:
        rag_extractor: RAG提取器
        force_reprocess: 是否強制重新處理
        
    Returns:
        bool: 是否提取成功
    """
    print("\n=== 提取總營收數據 ===")
    
    # 獲取所有公司和季度
    companies_data = rag_extractor.revenue_store.get_processed_companies_quarters()
    
    if not companies_data:
        print("沒有找到任何已處理的財報數據")
        return False
    
    print(f"發現 {len(companies_data)} 家公司的財報數據")
    
    total_processed = 0
    total_skipped = 0
    
    # 處理每個公司的每個季度
    for company_name, quarters in companies_data.items():
        print(f"\n開始提取 {company_name} 的營收數據...")
        
        for quarter in sorted(quarters):
            print(f"  處理 {quarter}...")
            
            success = rag_extractor.process_company_quarter(company_name, quarter, force_reprocess)
            
            if success:
                total_processed += 1
            else:
                total_skipped += 1
            
            # 避免API限制
            time.sleep(1)
    
    # 計算Q4營收
    print("\n=== 開始計算Q4營收 ===")
    q4_calculator = Q4Calculator(rag_extractor.revenue_store)
    q4_calculator.calculate_q4_revenue()
    
    print(f"\n=== 營收數據提取完成 ===")
    print(f"成功處理: {total_processed} 筆記錄")
    print(f"跳過: {total_skipped} 個已處理項目")
    
    return total_processed > 0

def main():
    """主程式"""
    try:
        # 初始化設定和日誌
        settings = Settings()
        setup_logger(settings)
        
        logging.info("財報營收數據提取系統啟動")
        
        # 測試系統連接
        if not test_connections(settings):
            print("系統連接測試失敗，程式結束")
            return
        
        # 初始化系統組件
        revenue_store = RevenueStore(settings)
        rag_extractor = RAGExtractor(settings, revenue_store)
        q4_calculator = Q4Calculator(revenue_store)
        excel_exporter = ExcelExporter(settings)
        
        # 檢查資料庫狀態
        db_status = check_database_status(revenue_store)
        
        if not db_status['has_embeddings']:
            print("\n警告：沒有找到嵌入文檔！")
            print("請確保已經運行過Insight模組進行文檔預處理。")
            return
        
        # 獲取使用者選擇
        choice = get_user_choice()
        
        # 處理使用者選擇
        if choice == "1":
            handle_full_extraction(rag_extractor, revenue_store, excel_exporter)
        
        elif choice == "2":
            handle_incremental_extraction(rag_extractor, revenue_store, excel_exporter, db_status)
        
        elif choice == "3":
            handle_export_only(excel_exporter, revenue_store, db_status)
        
        elif choice == "4":
            handle_clear_data(revenue_store)
        
        elif choice == "5":
            handle_q4_calculation(q4_calculator, excel_exporter, revenue_store)
        
        elif choice == "6":
            print("程式結束")
        
        else:
            print("無效選項，程式結束")
        
        logging.info("財報營收數據提取系統正常結束")
        
    except Exception as e:
        logging.error(f"程式執行時發生錯誤: {e}")
        print(f"程式執行失敗: {e}")

if __name__ == "__main__":
    main()