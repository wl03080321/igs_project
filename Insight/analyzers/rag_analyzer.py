import re
import time
from typing import Dict, List
from openai import OpenAI
from config.settings import settings
from utils.logger import get_logger
from utils.file_utils import is_annual_report, is_quarterly_report, extract_year_and_quarter

logger = get_logger(__name__)

class RAGAnalyzer:
    """RAG增強分析器"""
    def __init__(self):
        self.client = OpenAI(api_key=settings.openai_api_key)
    
    def enhanced_rag_process(self, query: str, vector_store, company_filter: str, quarter_filter: str, query_keywords_en: str) -> str:
        """RAG處理，支援公司和季度篩選"""
        try:
            # 擴展多語言關鍵詞
            financial_keywords = [
                "營收", "收入", "利潤", "獲利", "營業利益", "淨利", "毛利", "費用", "成本", "EBITDA",
                "revenue", "Revenue", "REVENUE", "Total Revenue", "Net Revenue", 
                "Total Net Revenue", "Service Revenue", "Product Revenue",
                "Net Sales", "Total Sales", "income", "Income", "profit", "Profit", 
                "earnings", "sales", "operating", "margin", "Margin",
                "매출액", "영업이익", "순이익", "마진율", "수익", "비용", "지급수수료", "영업비용",
                "실적", "수익성", "매출", "영업", "당기", "분기", "연결", "개별",  
                "재무", "손익", "자산", "부채", "자본", "성과", "수수료", "인건비"
            ]
            
            strategy_keywords = [
                "策略", "計劃", "發展", "擴展", "投資", "併購", "創新", "市場", "組織", "技術",
                "strategy", "plan", "development", "expansion", "investment", "acquisition", "innovation",
                "전략", "계획", "개발", "확장", "투자", "인수", "혁신", "시장", "신작", "게임",
                "포트폴리오", "라인업", "출시", "지역별", "사업", "운영"
            ]
            
            risk_keywords = [
                "風險", "挑戰", "威脅", "不確定", "競爭", "法規",
                "risk", "challenge", "threat", "uncertainty", "competition", "regulatory",
                "위험", "도전", "위협", "불확실성", "경쟁", "규제"
            ]
            
            # 檢查查詢類型
            all_keywords = financial_keywords + strategy_keywords + risk_keywords
            needs_table_data = any(keyword.lower() in query.lower() for keyword in all_keywords)
            
            # 搜尋設定
            search_limit = settings.get("vector_search.search_limit", 15)
            backup_search_limit = settings.get("vector_search.backup_search_limit", 25)
            universal_search_limit = settings.get("vector_search.universal_search_limit", 25)
            
            # 第一次搜索
            results = vector_store.search_similar_enhanced(
                query, 
                company_filter=company_filter,
                quarter_filter=quarter_filter,
                limit=search_limit,
                prioritize_tables=needs_table_data
            )
            
            # 如果結果不足，進行第二次搜索
            if len(results) < search_limit:
                logger.info("第一次搜索結果不足，進行關鍵詞搜索")
                chinese_terms = re.findall(r'[\u4e00-\u9fff]{2,}', query)
                english_terms = re.findall(r'[a-zA-Z]{3,}', query)
                korean_terms = re.findall(r'[\uac00-\ud7af]{2,}', query)
                stop_words = {"用", "繁體中文", "總結", "條列式", "呈現", "請", "提供", "具體", "詳細", "分析"}
                key_terms = [term for term in chinese_terms + english_terms + korean_terms if term not in stop_words]
                simplified_query = " ".join(key_terms[:5])
                
                backup_results = vector_store.search_similar_enhanced(
                    simplified_query,
                    company_filter=company_filter,
                    quarter_filter=quarter_filter,
                    limit=backup_search_limit,
                    prioritize_tables=needs_table_data
                )
                
                # 合併結果並去重
                existing_texts = {r['text'][:100] for r in results}
                for r in backup_results:
                    if r['text'][:100] not in existing_texts:
                        results.append(r)
                        existing_texts.add(r['text'][:100])
            
            # 如果還是不足，使用英文關鍵詞搜索
            if len(results) < 20 and query_keywords_en:
                logger.info("進行英文關鍵詞搜索")
                en_keywords = query_keywords_en.split(',')[:8]
                en_query = ' '.join([kw.strip() for kw in en_keywords])
                
                general_results = vector_store.search_similar_enhanced(
                    en_query,
                    company_filter=company_filter,
                    quarter_filter=quarter_filter,
                    limit=20,
                    prioritize_tables=needs_table_data
                )
                
                existing_texts = {r['text'][:100] for r in results}
                for r in general_results:
                    if r['text'][:100] not in existing_texts:
                        results.append(r)
                        existing_texts.add(r['text'][:100])
            
            # 通用搜索
            if len(results) < 15:
                logger.info("進行通用搜索")
                universal_query = "매출 매출액 세전이익 영업이익 순이익 revenue profit"
                
                universal_results = vector_store.search_similar_enhanced(
                    universal_query,
                    company_filter=company_filter,
                    quarter_filter=quarter_filter,
                    limit=universal_search_limit,
                    prioritize_tables=needs_table_data
                )
                
                results.extend(universal_results)
            
            if not results:
                return "無法找到相關資訊"
            
            # 限制最終結果數量
            results = results[:30]
            
            # 整理搜索結果
            contexts = []
            page_references = set()
            table_count = 0
            ocr_content_count = 0
            
            for i, result in enumerate(results):
                chunk_text = result['text']
                metadata = result.get('metadata', {})
                score = result.get('score', 0)
                has_structured_data = metadata.get('has_structured_data', False)
                is_ocr_content = metadata.get('is_ocr_content', False)
                
                if has_structured_data:
                    table_count += 1
                
                if is_ocr_content:
                    ocr_content_count += 1
                
                # 收集頁面信息
                start_page = metadata.get('start_page')
                end_page = metadata.get('end_page')
                if start_page and end_page:
                    if start_page == end_page:
                        page_references.add(f"頁{start_page}")
                    else:
                        page_references.add(f"頁{start_page}-{end_page}")
                
                # 添加內容類型標記
                if is_ocr_content:
                    content_type = "OCR提取內容"
                elif has_structured_data:
                    content_type = "表格數據"
                else:
                    content_type = "文本內容"
                
                context_info = f"=== {content_type} {i+1} (相似度: {score:.3f}) ===\n{chunk_text}"
                contexts.append(context_info)
                
                logger.info(f"使用塊 {i+1}: 頁面 {start_page}-{end_page}, 相似度: {score:.3f}, 類型: {content_type}")
            
            # 合併上下文
            combined_context = '\n\n'.join(contexts)
            
            # 控制上下文長度
            max_context_length = settings.get("vector_search.max_context_length", 300000)
            if len(combined_context) > max_context_length:
                combined_context = combined_context[:max_context_length] + "\n\n[內容已截斷...]"
            
            page_ref_text = ", ".join(sorted(page_references)) if page_references else "未找到明確頁碼"
            
            # 提示詞
            llm_prompt = f"""
財報內容分析 (包含 {table_count} 個表格數據段落, {ocr_content_count} 個OCR提取段落)：
{combined_context}

分析任務：{query}

參考頁面：{page_ref_text}

分析要求：
- 按照分析任務裡的項目去撰寫內容
- **對於英文財報，請特別關注以下項目**：
  * "Revenue"、"Total Revenue"、"Net Revenue" = 總營收
  * "Operating Income" = 營業利益  
  * "Net Income" = 淨利
  * "Three months ended" = 當季三個月數據
- **營收數據優先級**：
  * 第一優先：使用 "Three months ended" 的當季數據（適用於季報分析）
  * 第二優先：使用年度數據 "Year ended" 或 "For the year ended"（適用於年報分析）
  * **盡量避免使用**：累計數據（如 Six months ended、Nine months ended等）
- 若是營收與產品（部門）相關分析任務，優先使用表格中的具體數字進行分析，若無表格則使用內文中提及的數字進行分析
- 若是部門或產品名稱則使用原文，不需翻譯
- **重要1：引用數據與財報內文時必須標註頁碼，格式為 (p.X)（括號一定要使用半形括號）**
- **重要2：若找不到相關內容時使用「無明確提及」作為答案，不用添加額外的推論**
- **重要3：直接輸出純文字內容，且分析內容前不需要有任何前導標題（如：XXXX年XX季度公司概況等）**
- **重要4：米字號使用規則**
  * 在重要的**數字、金額、百分比、營收數據、獲利數字**等關鍵財務數據前後添加兩個米字號
  * 在重要的**公司策略、風險評估結論、關鍵業務變化**等重要資訊前後添加兩個米字號
  * **不要**在以下內容添加米字號：
    - 分析任務中的主要標題（如：1. 綜合營收與獲利、2. 部門表現等）
    - 分析任務中的副標題（如：(1) 總營收、(2) 服務收入等）
    - 一般性的描述文字和過渡語句
    - 頁數
    - 無明確提及
- 分析應該結構化且簡明扼要、易於理解
- 用繁體中文回答，字數控制在 300 字左右

米字號使用範例：
正確：「總營收達到**750億韓元**，較去年同期成長**15%**」
正確：「公司計劃在**2024年推出5款新遊戲**，重點布局**全球市場**」
錯誤：「**1. 綜合營收與獲利**」（主標題不要加）
錯誤：「**(1) 總營收**」（副標題不要加）
錯誤：「**(p.X)**」（頁數不要加）
"""
            
            # 使用 GPT-4.1 進行分析
            response = self.client.chat.completions.create(
                model=settings.llm_model,
                messages=[
                    {
                        "role": "system", 
                        "content": "你是一個專業的財務分析師，擅長分析多種語言的財報，財報內容包含表格數據和OCR提取的圖像內容。你能夠準確解讀財務表格和圖像中的數據，提供精確的數據分析，並將復雜的財務信息轉化為清晰易懂的中文分析報告。在引用數據時，你總是會準確標註頁碼來源。"
                    },
                    {"role": "user", "content": llm_prompt}
                ],
                max_tokens=settings.get("openai_settings.max_tokens", 1800),
                temperature=settings.get("openai_settings.temperature", 0.1)
            )
            
            return response.choices[0].message.content
        
        except Exception as e:
            logger.error(f"RAG 處理時發生錯誤: {e}")
            return "處理查詢時發生錯誤"
    
    def generate_enhanced_business_analysis_with_fallback(self, vector_store, file_name: str, company_name: str, quarter_filter: str) -> Dict:
        """生成商業分析，支援特定公司和季度的篩選"""
        # 判斷報告類型
        is_annual = is_annual_report(file_name)
        is_quarterly = is_quarterly_report(file_name)
        
        # 根據報告類型設定不同的查詢模板
        if is_quarterly:
            queries_zh = {
                "company_overview": {
                    "query": "用繁體中文總結{year}年{quarter}的公司概況，條列式呈現：1. 綜合營收與獲利、2. 部門（產品）表現。綜合營收與獲利部分要細分成：(1) 總營收、(2) 服務收入、(3) 產品收入、(4) 營業利益、(5) 稅後淨利、(6) 營業費用。**請優先使用Three months ended（當季三個月）的營收數據**。請提供具體數字和詳細分析，優先使用表格數據。",
                    "keywords_en": "Three months ended, quarterly, 매출액, 영업이익, 순이익, 마진율, 지급수수료, 인건비, 마케팅비, Revenue, Income, Profit, Net Income, Earnings, Segment, Division, Product, Business, Financial Performance, Sales, Operating Income, Gross Profit, EBITDA, Operating Expenses, Cost of Revenue, Service Revenue, Product Revenue"
                },
                "business_strategy": {
                    "query": "用繁體中文總結{year}年{quarter}的商業策略，條列式呈現：1. 市場拓展、2. 產品（營運）策略、3. 組織計劃、4. 技術創新、5. 收購資訊。請提供具體的策略細節和實施計劃，重點關注當季的策略執行情況。",
                    "keywords_en": "quarterly strategy, 신작, 게임, 포트폴리오, 라인업, 출시, 지역별, Strategy, Strategic, Market, Product, Operations, Operational, Organization, Technology, Innovation, Acquisition, Investment, Expansion, Growth, Development, Initiatives, Objectives, Goals, Strategic Plans, Business Development"
                },
                "risks": {
                    "query": "用繁體中文總結{year}年{quarter}的主要風險，條列式呈現：1. 經濟與市場相關風險、2. 資本結構與流動性風險、3. 業務與產業風險、4. 技術相關風險、5. 法規與政策風險。請提供具體的風險評估和影響分析，重點關注當季面臨的風險變化。",
                    "keywords_en": "quarterly risks, 위험, 불확실성, 경쟁, 시장, 규제, Risk, Risks, Challenge, Challenges, Threat, Threats, Market Risk, Economic, Regulatory, Competition, Competitive, Technology, Capital, Liquidity, Credit Risk, Operational Risk, Compliance, Legal, Financial Risk, Business Risk"
                }
            }
        elif is_annual:
            queries_zh = {
                "company_overview": {
                    "query": "用繁體中文總結{year}年度的公司概況，條列式呈現：1. 綜合營收與獲利、2. 部門（產品）表現。綜合營收與獲利部分要細分成：(1) 總營收、(2) 服務收入、(3) 產品收入、(4) 營業利益、(5) 稅後淨利、(6) 營業費用。**請使用年度總營收數據（Year ended 或 For the year ended）**。請提供具體數字和詳細分析，優先使用表格數據。",
                    "keywords_en": "Year ended, For the year ended, annual revenue, 연간매출, 연도말, 매출액, 영업이익, 순이익, 마진율, 지급수수료, 인건비, 마케팅비, Revenue, Income, Profit, Net Income, Earnings, Segment, Division, Product, Business, Financial Performance, Sales, Operating Income, Gross Profit, EBITDA, Operating Expenses, Cost of Revenue, Service Revenue, Product Revenue"
                },
                "business_strategy": {
                    "query": "用繁體中文總結{year}年度的商業策略，條列式呈現：1. 市場拓展、2. 產品（營運）策略、3. 組織計劃、4. 技術創新、5. 收購資訊。請提供具體的策略細節和實施計劃，重點關注年度整體策略規劃與執行成果。",
                    "keywords_en": "annual strategy, 연간전략, 신작, 게임, 포트폴리오, 라인업, 출시, 지역별, Strategy, Strategic, Market, Product, Operations, Operational, Organization, Technology, Innovation, Acquisition, Investment, Expansion, Growth, Development, Initiatives, Objectives, Goals, Strategic Plans, Business Development"
                },
                "risks": {
                    "query": "用繁體中文總結{year}年度的主要風險，條列式呈現：1. 經濟與市場相關風險、2. 資本結構與流動性風險、3. 業務與產業風險、4. 技術相關風險、5. 法規與政策風險。請提供具體的風險評估和影響分析，重點關注年度整體風險管理狀況。",
                    "keywords_en": "annual risks, 연간위험, 위험, 불확실성, 경쟁, 시장, 규제, Risk, Risks, Challenge, Challenges, Threat, Threats, Market Risk, Economic, Regulatory, Competition, Competitive, Technology, Capital, Liquidity, Credit Risk, Operational Risk, Compliance, Legal, Financial Risk, Business Risk"
                }
            }
        else:
            # 預設查詢模板
            queries_zh = {
                "company_overview": {
                    "query": "用繁體中文總結{year}年{quarter}的公司概況，條列式呈現：1. 綜合營收與獲利、2. 部門（產品）表現。綜合營收與獲利部分要細分成：(1) 總營收、(2) 服務收入、(3) 產品收入、(4) 營業利益、(5) 稅後淨利、(6) 營業費用。請提供具體數字和詳細分析，優先使用表格數據。",
                    "keywords_en": "매출액, 영업이익, 순이익, 마진율, 지급수수료, 인건비, 마케팅비, Revenue, Income, Profit, Net Income, Earnings, Segment, Division, Product, Business, Financial Performance, Sales, Operating Income, Gross Profit, EBITDA, Operating Expenses, Cost of Revenue, Service Revenue, Product Revenue"
                },
                "business_strategy": {
                    "query": "用繁體中文總結{year}年{quarter}的商業策略，條列式呈現：1. 市場拓展、2. 產品（營運）策略、3. 組織計劃、4. 技術創新、5. 收購資訊。請提供具體的策略細節和實施計劃。",
                    "keywords_en": "신작, 게임, 포트폴리오, 라인업, 출시, 지역별, Strategy, Strategic, Market, Product, Operations, Operational, Organization, Technology, Innovation, Acquisition, Investment, Expansion, Growth, Development, Initiatives, Objectives, Goals, Strategic Plans, Business Development"
                },
                "risks": {
                    "query": "用繁體中文總結{year}年{quarter}的主要風險，條列式呈現：1. 經濟與市場相關風險、2. 資本結構與流動性風險、3. 業務與產業風險、4. 技術相關風險、5. 法規與政策風險。請提供具體的風險評估和影響分析。",
                    "keywords_en": "위험, 불확실성, 경쟁, 시장, 규제, Risk, Risks, Challenge, Challenges, Threat, Threats, Market Risk, Economic, Regulatory, Competition, Competitive, Technology, Capital, Liquidity, Credit Risk, Operational Risk, Compliance, Legal, Financial Risk, Business Risk"
                }
            }
        
        results = {}
        year, quarter = extract_year_and_quarter(file_name)
        year = year or "未知"
        quarter = quarter or "全年"
        
        results["year_quarter"] = f"{year}_{quarter}"
        
        # 處理每個查詢
        for key, query_info in queries_zh.items():
            print(f"處理查詢: {key} ({'年報' if is_annual else '季報' if is_quarterly else '一般報告'})")
            
            # 根據報告類型調整顯示文字
            if is_annual:
                display_quarter = "年度"
                query = query_info["query"].format(year=year, quarter=display_quarter)
            else:
                display_quarter = "全年" if quarter == "全年" else f"{quarter}季度"
                query = query_info["query"].format(year=year, quarter=display_quarter)

            time.sleep(1)  # 短暫延遲

            answer = self.enhanced_rag_process(query, vector_store, company_name, quarter_filter, query_info["keywords_en"])
            results[key] = answer
            
            logger.info(f"完成 {key} 分析 ({'年報' if is_annual else '季報' if is_quarterly else '一般報告'})")
        
        # 對於Netmarble公司，檢查分析質量
        if vector_store.is_netmarble_company(company_name):
            need_ocr = vector_store.check_analysis_quality(results)
            if need_ocr:
                logger.warning(f"Netmarble檔案 {file_name} 分析質量不佳，標記為需要OCR處理")
                file_key = f"{company_name}_{file_name}"
                vector_store.netmarble_failed_files.add(file_key)
                return None  # 返回None表示需要重新處理
        
        return results