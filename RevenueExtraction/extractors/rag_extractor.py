"""RAG營收提取器"""
import logging
import numpy as np
from typing import List, Dict, Any, Optional
from sentence_transformers import SentenceTransformer
from openai import OpenAI
from sklearn.metrics.pairwise import cosine_similarity

from config.settings import Settings
from models.revenue_store import RevenueStore
from processors.data_parser import DataParser

class RAGExtractor:
    def __init__(self, settings: Settings, revenue_store: RevenueStore):
        """初始化RAG提取器
        
        Args:
            settings: 設定物件
            revenue_store: 營收資料庫
        """
        self.settings = settings
        self.revenue_store = revenue_store
        self.data_parser = DataParser()
        
        # 初始化OpenAI客戶端
        openai_config = settings.get_openai_config()
        self.openai_client = OpenAI(api_key=openai_config.get('api_key'))
        self.model = openai_config.get('model', 'gpt-4.1')
        self.max_tokens = openai_config.get('max_tokens', 2000)
        self.temperature = openai_config.get('temperature', 0.1)
        
        # 初始化向量模型
        rag_config = settings.get_rag_config()
        model_name = rag_config.get('embedding_model', 'paraphrase-multilingual-MiniLM-L12-v2')
        self.embedding_model = SentenceTransformer(model_name)
        
        # RAG配置
        self.search_limit = rag_config.get('search_limit', 20)
        self.max_context_length = rag_config.get('max_context_length', 200000)
    
    def search_similar_enhanced(self, query_text: str, company_filter: Optional[str] = None, 
                              quarter_filter: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """從嵌入集合中搜索相關文檔
        
        Args:
            query_text: 查詢文本
            company_filter: 公司篩選條件
            quarter_filter: 季度篩選條件
            limit: 返回結果數量限制
            
        Returns:
            List[Dict[str, Any]]: 搜索結果列表
        """
        try:
            query_embedding = self.embedding_model.encode(query_text, convert_to_tensor=False)
            if isinstance(query_embedding, np.ndarray):
                query_embedding = query_embedding.reshape(1, -1)
            
            # 構建查詢條件
            query_conditions = {}
            if company_filter:
                query_conditions["metadata.company_name"] = company_filter
            if quarter_filter:
                query_conditions["metadata.quarter"] = quarter_filter
            
            # 從 MongoDB 獲取所有符合條件的文檔
            documents = list(self.revenue_store.embedding_collection.find(query_conditions))
            
            if not documents:
                logging.warning("沒有找到符合條件的文檔")
                return []
            
            # 提取嵌入向量並計算相似度
            doc_embeddings = []
            doc_info = []
            
            for doc in documents:
                embedding = doc.get('embedding')
                if embedding:
                    doc_embeddings.append(embedding)
                    doc_info.append({
                        'text': doc.get('text', ''),
                        'metadata': doc.get('metadata', {}),
                        '_id': doc.get('_id')
                    })
            
            if not doc_embeddings:
                return []
            
            doc_embeddings = np.array(doc_embeddings)
            similarities = cosine_similarity(query_embedding, doc_embeddings)[0]
            
            # 創建結果列表
            results_with_scores = []
            for i, similarity_score in enumerate(similarities):
                result = {
                    'text': doc_info[i]['text'],
                    'metadata': doc_info[i]['metadata'],
                    'score': float(similarity_score),
                    '_id': doc_info[i]['_id']
                }
                results_with_scores.append(result)
            
            # 按相似度排序並返回前N個結果
            results_with_scores.sort(key=lambda x: x['score'], reverse=True)
            return results_with_scores[:limit]
            
        except Exception as e:
            logging.error(f"搜索時發生錯誤: {e}")
            return []
    
    def extract_revenue_data(self, query: str, company_filter: str, quarter_filter: str) -> str:
        """使用RAG提取營收數據
        
        Args:
            query: 查詢文本
            company_filter: 公司篩選條件
            quarter_filter: 季度篩選條件
            
        Returns:
            str: GPT回應結果
        """
        try:
            # 搜索相關文檔
            results = self.search_similar_enhanced(
                query, 
                company_filter=company_filter,
                quarter_filter=quarter_filter,
                limit=self.search_limit
            )
            
            if not results:
                return "無法找到相關營收資訊"
            
            # 整理上下文
            contexts = []
            for i, result in enumerate(results):
                chunk_text = result['text']
                metadata = result.get('metadata', {})
                score = result.get('score', 0)
                
                context_info = f"=== 文檔片段 {i+1} (相似度: {score:.3f}) ===\n{chunk_text}"
                contexts.append(context_info)
            
            combined_context = '\n\n'.join(contexts)
            
            # 控制上下文長度
            if len(combined_context) > self.max_context_length:
                combined_context = combined_context[:self.max_context_length] + "\n\n[內容已截斷...]"
            
            # 構建提示詞
            llm_prompt = self._build_revenue_extraction_prompt(combined_context, query)
            
            # 使用 GPT 進行分析
            response = self.openai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system", 
                        "content": "你是一個專業的財務數據提取專家，專門從財報中提取準確的總營收數據。你會仔細分析財報內容，識別總營收數據，特別注意識別數值的單位（千、百萬、億等），並以結構化的JSON格式回答。你會保持原始幣別，不進行匯率轉換。"
                    },
                    {"role": "user", "content": llm_prompt}
                ],
                max_tokens=self.max_tokens,
                temperature=self.temperature
            )
            
            return response.choices[0].message.content
        
        except Exception as e:
            logging.error(f"提取營收數據時發生錯誤: {e}")
            return "處理查詢時發生錯誤"
    
    def _build_revenue_extraction_prompt(self, context: str, query: str) -> str:
        """構建營收提取提示詞
        
        Args:
            context: 搜索到的上下文
            query: 原始查詢
            
        Returns:
            str: 構建好的提示詞
        """
        return f"""
財報內容：
{context}

分析任務：{query}

請根據財報內容提取準確的總營收數據。要求：

1. **數據提取規則**：
   - 優先使用 "Three months ended" 的當季數據（適用於季報）
   - 其次使用年度數據 "Year ended" 或 "For the year ended"（適用於年報）
   - 避免使用累計數據（如 Six months ended、Nine months ended）
   - 保持原始數值、單位和幣別，後續會統一轉換

2. **單位識別（重要）**：
   - 仔細識別數值的單位：千、百萬、億、千億、兆等
   - 英文單位：thousand, million, billion
   - 韓文單位：천, 만, 억
   - 如果沒有明確單位，根據上下文推測最可能的單位

3. **幣別處理**：
   - 美元：如果看到 $ 或 USD 或相關描述，記為 USD
   - 韓元：如果看到 원 或 KRW 或相關描述，記為 KRW

4. **嚴格JSON格式回答**：
   請務必按照以下嚴格的JSON格式回答，不要包含任何其他文字、說明或markdown標記：

{{
  "success": true,
  "data": [
    {{
      "type": "total_revenue",
      "name": "Total Revenue",
      "value": 123.45,
      "unit": "million",
      "original_currency": "USD",
      "source_page": "page_1"
    }}
  ]
}}

5. **JSON格式規則**：
   - 所有屬性名必須用雙引號
   - 字符串值必須用雙引號
   - 數值不要用引號
   - 布林值使用 true/false（小寫）
   - 不要有尾隨逗號
   - 不要包含註解

6. **重要提示**：
   - 如果找不到明確數據，success設為false
   - 保持原始的營收項目名稱，不要翻譯
   - 確保數值準確性，包含小數位
   - 標註數據來源頁碼
   - 不要轉換匯率，保持原始幣別

請直接回答JSON，不要包含任何其他文字。
"""
    
    def process_company_quarter(self, company_name: str, quarter: str, force_reprocess: bool = False) -> bool:
        """處理單個公司季度的營收數據提取
        
        Args:
            company_name: 公司名稱
            quarter: 季度
            force_reprocess: 是否強制重新處理
            
        Returns:
            bool: 是否處理成功
        """
        try:
            # 檢查是否已有數據
            if not force_reprocess and self.revenue_store.check_existing_revenue_data(company_name, quarter):
                print(f"    跳過 {company_name} - {quarter}（已有數據）")
                return False
            
            # 從quarter中提取年份和季度信息
            if "_" in quarter:
                year_part, quarter_part = quarter.split("_", 1)
                
                # 格式化顯示文字
                if quarter_part == "全年":
                    display_quarter = "年度"
                else:
                    display_quarter = f"{quarter_part}季度"
            else:
                year_part = "未知"
                display_quarter = "未知"
            
            print(f"    提取總營收...")
            
            query = f"請提取{year_part}年{display_quarter}的總營收數據，包括 Total Revenue、Net Revenue、Total Net Revenue 等總營收項目的具體數值。保持原始幣別不要轉換。"
            
            response = self.extract_revenue_data(
                query,
                company_name,
                quarter
            )
            
            if response and "無法找到相關" not in response:
                revenue_data = self.data_parser.parse_revenue_response(response)
                
                if revenue_data.get('success'):
                    saved_records = self.revenue_store.save_revenue_data(
                        company_name,
                        quarter,
                        revenue_data
                    )
                    
                    if saved_records:
                        print(f"      成功保存 {len(saved_records)} 筆總營收數據")
                        return True
                    else:
                        print(f"      總營收無有效數據")
                        return False
                else:
                    print(f"      總營收提取失敗 - 可能沒有找到相關數據")
                    # 顯示詳細信息以便調試
                    if 'data' in revenue_data:
                        print(f"      返回的數據結構: {revenue_data}")
                    return False
            else:
                print(f"      總營收無相關數據")
                print(f"      GPT回應: {response[:200]}..." if len(response) > 200 else f"      GPT回應: {response}")
                return False
                
        except Exception as e:
            logging.error(f"提取 {company_name} - {quarter} 總營收時發生錯誤: {e}")
            return False