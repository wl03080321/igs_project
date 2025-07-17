import re
import numpy as np
from pymongo import MongoClient
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

from config.settings import settings
from utils.logger import get_logger
from processors.pdf_processor import PDFProcessor
from processors.ocr_processor import OCRProcessor

logger = get_logger(__name__)

class EnhancedMongoDBVectorStore:
    """MongoDB向量資料庫"""
    def __init__(self):
        self.client = MongoClient(settings.mongodb_uri)
        self.db = self.client[settings.database_name]
        self.collection = self.db[settings.collection_name]
        self.analysis_collection = self.db[settings.analysis_collection_name]
        
        # 初始化處理器
        self.pdf_processor = PDFProcessor()
        self.ocr_processor = OCRProcessor()
        
        # 初始化向量模型
        self.embedding_model = SentenceTransformer(settings.embedding_model)
        
        # Netmarble特殊處理標記
        self.netmarble_failed_files = set()
        
        # 創建索引
        self._create_vector_index()
        self._create_analysis_index()
    
    def _create_vector_index(self):
        """創建向量搜索索引"""
        try:
            self.collection.create_index([
                ("metadata.company_name", 1),
                ("metadata.quarter", 1)
            ], name="company_quarter_index")
            
            self.collection.create_index([
                ("metadata.file_name", 1)
            ], name="file_name_index")
            
            logger.info("成功創建基本查詢索引")
        except Exception as e:
            logger.warning(f"創建索引時發生錯誤: {e}")
    
    def _create_analysis_index(self):
        """創建分析結果索引"""
        try:
            self.analysis_collection.create_index([
                ("company", 1),
                ("quarter", 1),
                ("title", 1)
            ], name="company_quarter_title_index")
            
            self.analysis_collection.create_index([
                ("created_at", -1)
            ], name="created_at_index")
            
            logger.info("成功創建分析結果索引")
        except Exception as e:
            logger.warning(f"創建分析結果索引時發生錯誤: {e}")
    
    def is_netmarble_company(self, company_name: str) -> bool:
        """檢查是否為Netmarble公司"""
        netmarble_indicators = ["netmarble", "넷마블", "네트마블"]
        return any(indicator.lower() in company_name.lower() for indicator in netmarble_indicators)
    
    def should_use_ocr_processing(self, file_name: str, company_name: str) -> bool:
        """判斷是否應該使用OCR處理"""
        file_key = f"{company_name}_{file_name}"
        if file_key in self.netmarble_failed_files:
            return True
        
        if not self.is_netmarble_company(company_name):
            presentation_indicators = [
                "presentation", "investor", "earnings call", "slide", 
                "발표", "설명", "IR", "실적발표"
            ]
            
            for indicator in presentation_indicators:
                if indicator.lower() in file_name.lower():
                    return True
        
        return False
    
    def read_pdf_enhanced(self, file_path: str, company_name: str, max_pages: int = None) -> Tuple[str, int]:
        """智能PDF讀取：自動選擇文字提取或OCR"""
        file_name = os.path.basename(file_path)
        
        if self.should_use_ocr_processing(file_name, company_name):
            logger.info(f"使用OCR模式處理: {company_name} - {file_name}")
            return self.ocr_processor.read_pdf_with_ocr(file_path, max_pages)
        else:
            logger.info(f"使用文字提取模式處理: {company_name} - {file_name}")
            text, pages = self.pdf_processor.read_pdf_text_extraction(file_path, max_pages)
            # 同步表格和圖像信息
            self.current_tables = self.pdf_processor.current_tables
            self.current_images = self.pdf_processor.current_images
            return text, pages
    
    @property
    def current_tables(self):
        """獲取當前處理的表格"""
        if hasattr(self.pdf_processor, 'current_tables'):
            return self.pdf_processor.current_tables
        return []
    
    @current_tables.setter
    def current_tables(self, value):
        """設置當前處理的表格"""
        if hasattr(self.pdf_processor, 'current_tables'):
            self.pdf_processor.current_tables = value
    
    @property
    def current_images(self):
        """獲取當前處理的圖像"""
        if hasattr(self.pdf_processor, 'current_images'):
            return self.pdf_processor.current_images
        elif hasattr(self.ocr_processor, 'current_images'):
            return self.ocr_processor.current_images
        return []
    
    @current_images.setter
    def current_images(self, value):
        """設置當前處理的圖像"""
        if hasattr(self.pdf_processor, 'current_images'):
            self.pdf_processor.current_images = value
        if hasattr(self.ocr_processor, 'current_images'):
            self.ocr_processor.current_images = value
    
    def check_analysis_quality(self, analysis_results: Dict) -> bool:
        """檢查分析結果質量，判斷是否需要使用OCR"""
        if not analysis_results:
            return False
        
        failure_indicators = [
            "無法找到相關資訊",
            "處理查詢時發生錯誤",
            "找不到相關內容",
        ]
        
        failed_count = 0
        total_count = 0
        
        for key, content in analysis_results.items():
            if key == "year_quarter":
                continue
            
            total_count += 1
            
            # 檢查內容長度
            if len(content.strip()) < 50:
                failed_count += 1
                continue
            
            # 檢查失敗指標
            content_lower = content.lower()
            if any(indicator in content_lower for indicator in failure_indicators):
                failed_count += 1
                continue
            
            # 檢查是否包含具體數據
            if not re.search(r'\d+', content):
                failed_count += 0.5
        
        failure_rate = failed_count / total_count if total_count > 0 else 1
        logger.info(f"分析質量檢查：失敗率 {failure_rate:.2f} ({failed_count}/{total_count})")
        
        return failure_rate > 0.5
    
    def add_document_with_enhanced_chunking(self, text: str, metadata: Dict = None) -> List[str]:
        """使用分塊添加文檔"""
        try:
            text_chunks = self._intelligent_split_text_enhanced(text)
            document_ids = []
            
            logger.info(f"準備處理 {len(text_chunks)} 個分割塊")
            
            for i, chunk_info in enumerate(text_chunks):
                chunk_text = chunk_info['text']
                
                if not chunk_text.strip():
                    continue
                
                try:
                    logger.info(f"處理塊 {i+1}/{len(text_chunks)}，長度：{len(chunk_text)} 字符")
                    
                    # 生成embedding
                    embedding = self.embedding_model.encode(chunk_text, convert_to_tensor=False)
                    if isinstance(embedding, np.ndarray):
                        embedding = embedding.tolist()
                    
                    # 設置metadata
                    chunk_metadata = metadata.copy() if metadata else {}
                    chunk_metadata.update({
                        "chunk_index": i,
                        "total_chunks": len(text_chunks),
                        "chunk_length": len(chunk_text),
                        "start_page": chunk_info['start_page'],
                        "end_page": chunk_info['end_page'],
                        "pages_covered": chunk_info['pages'],
                        "is_partial_page": chunk_info.get('is_partial_page', False),
                        "has_structured_data": chunk_info.get('has_structured_data', False),
                        "is_ocr_content": chunk_info.get('is_ocr_content', False),
                        "embedding_model": settings.embedding_model,
                        "embedding_dimensions": settings.get("vector_search.embedding_dimensions", 384)
                    })
                    
                    document = {
                        "text": chunk_text,
                        "embedding": embedding,
                        "metadata": chunk_metadata,
                        "created_at": datetime.now()
                    }
                    
                    result = self.collection.insert_one(document)
                    document_ids.append(str(result.inserted_id))
                    
                    logger.info(f"成功處理文檔塊 {i+1}，ID: {result.inserted_id}")
                    
                except Exception as chunk_error:
                    logger.error(f"處理文檔塊 {i+1} 時發生錯誤: {chunk_error}")
                    continue
            
            if document_ids:
                logger.info(f"成功分割為 {len(document_ids)} 個塊")
                table_count = sum(1 for chunk in text_chunks if chunk.get('has_structured_data', False))
                ocr_count = sum(1 for chunk in text_chunks if chunk.get('is_ocr_content', False))
                logger.info(f"包含表格的塊數：{table_count}, OCR塊數：{ocr_count}")
            
            return document_ids
        
        except Exception as e:
            logger.error(f"添加文檔時發生錯誤: {e}")
            return []
    
    def _intelligent_split_text_enhanced(self, text: str) -> List[Dict]:
        """智能文本分割"""
        max_tokens = settings.get("vector_search.chunk_max_tokens", 6000)
        chunks = []
        
        # 檢查是否為OCR內容
        is_ocr_content = "[PAGES " in text and "=" * 50 in text
        
        if is_ocr_content:
            return self._split_ocr_content(text, max_tokens)
        else:
            return self._split_regular_content(text, max_tokens)
    
    def _split_ocr_content(self, text: str, max_tokens: int) -> List[Dict]:
        """處理OCR提取的文本分割"""
        chunks = []
        
        try:
            # 按OCR的頁面標記分割
            page_pattern = r'\n={50}\n\[PAGES (\d+(?:-\d+)?)\]\n={50}\n'
            page_splits = re.split(page_pattern, text)
            
            current_chunk = ""
            current_page_info = []
            
            i = 0
            while i < len(page_splits):
                if i == 0:
                    if page_splits[i].strip():
                        content = page_splits[i].strip()
                        if len(content) < max_tokens:
                            current_chunk = content
                    i += 1
                    continue
                
                if i < len(page_splits):
                    page_info = page_splits[i]
                    i += 1
                    
                    if i < len(page_splits):
                        page_content = page_splits[i].strip()
                        
                        # 解析頁碼範圍
                        if '-' in page_info:
                            start_page, end_page = page_info.split('-')
                            pages_list = list(range(int(start_page), int(end_page) + 1))
                        else:
                            pages_list = [int(page_info)]
                        
                        test_content = current_chunk + f"\n[PAGES {page_info}]\n" + page_content
                        
                        if len(test_content) > max_tokens and current_chunk.strip():
                            chunks.append({
                                'text': current_chunk.strip(),
                                'pages': current_page_info.copy(),
                                'start_page': str(current_page_info[0]) if current_page_info else None,
                                'end_page': str(current_page_info[-1]) if current_page_info else None,
                                'has_structured_data': "=== 表格" in current_chunk,
                                'is_ocr_content': True
                            })
                            
                            current_chunk = f"[PAGES {page_info}]\n" + page_content
                            current_page_info = pages_list.copy()
                        else:
                            if current_chunk:
                                current_chunk += f"\n[PAGES {page_info}]\n" + page_content
                            else:
                                current_chunk = f"[PAGES {page_info}]\n" + page_content
                            current_page_info.extend(pages_list)
                    
                    i += 1
            
            # 添加最後一個塊
            if current_chunk.strip():
                chunks.append({
                    'text': current_chunk.strip(),
                    'pages': current_page_info,
                    'start_page': str(current_page_info[0]) if current_page_info else None,
                    'end_page': str(current_page_info[-1]) if current_page_info else None,
                    'has_structured_data': "=== 表格" in current_chunk,
                    'is_ocr_content': True
                })
            
            logger.info(f"OCR內容分割完成：{len(chunks)} 塊")
            return chunks
            
        except Exception as e:
            logger.error(f"OCR內容分割時發生錯誤: {e}")
            return self._fallback_split(text, max_tokens, is_ocr=True)
    
    def _split_regular_content(self, text: str, max_tokens: int) -> List[Dict]:
        """處理常規PDF文本分割"""
        chunks = []
        
        try:
            pages = text.split('[PAGE ')
            current_chunk = ""
            current_page_info = []
            
            for i, page in enumerate(pages):
                if not page.strip():
                    continue
                
                if i > 0 or page.startswith('[PAGE'):
                    page_content = '[PAGE ' + page if not page.startswith('[PAGE') else page
                else:
                    page_content = page
                
                # 提取頁碼信息
                page_match = re.search(r'\[PAGE (\d+)\]', page_content)
                page_num = page_match.group(1) if page_match else str(i)
                
                has_table = "=== 表格" in page_content or "結構化表格資料" in page_content
                effective_max_tokens = max_tokens * 1.5 if has_table else max_tokens
                
                if len(current_chunk + page_content) > effective_max_tokens:
                    if current_chunk.strip():
                        chunks.append({
                            'text': current_chunk.strip(),
                            'pages': current_page_info.copy(),
                            'start_page': current_page_info[0] if current_page_info else None,
                            'end_page': current_page_info[-1] if current_page_info else None,
                            'has_structured_data': "=== 表格" in current_chunk,
                            'is_ocr_content': False
                        })
                    
                    current_chunk = page_content
                    current_page_info = [page_num]
                else:
                    current_chunk += page_content
                    current_page_info.append(page_num)
            
            # 添加最後一個塊
            if current_chunk.strip():
                chunks.append({
                    'text': current_chunk.strip(),
                    'pages': current_page_info,
                    'start_page': current_page_info[0] if current_page_info else None,
                    'end_page': current_page_info[-1] if current_page_info else None,
                    'has_structured_data': "=== 表格" in current_chunk,
                    'is_ocr_content': False
                })
            
            logger.info(f"常規內容分割完成：{len(chunks)} 塊")
            return chunks
            
        except Exception as e:
            logger.error(f"常規內容分割時發生錯誤: {e}")
            return self._fallback_split(text, max_tokens, is_ocr=False)
    
    def _fallback_split(self, text: str, max_tokens: int, is_ocr: bool = False) -> List[Dict]:
        """簡單的文本分割"""
        chunks = []
        
        try:
            text_length = len(text)
            chunk_size = max_tokens
            
            for i in range(0, text_length, chunk_size):
                chunk_text = text[i:i + chunk_size]
                
                if chunk_text.strip():
                    chunks.append({
                        'text': chunk_text.strip(),
                        'pages': ['unknown'],
                        'start_page': 'unknown',
                        'end_page': 'unknown',
                        'has_structured_data': False,
                        'is_fallback': True,
                        'is_ocr_content': is_ocr
                    })
            
            logger.info(f"降級分割完成：{len(chunks)} 塊")
            return chunks
            
        except Exception as e:
            logger.error(f"降級分割時發生錯誤: {e}")
            return []
    
    def search_similar_enhanced(self, query_text: str, company_filter: str = None, quarter_filter: str = None, limit: int = 5, prioritize_tables: bool = False) -> List[Dict]:
        """相似文檔搜索"""
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
            
            logger.info(f"查詢條件: {query_conditions}")
            documents = list(self.collection.find(query_conditions))
            
            if not documents:
                logger.warning("沒有找到符合條件的文檔")
                return []
            
            logger.info(f"找到 {len(documents)} 個候選文檔")
            
            # 提取所有文檔的embedding
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
                logger.warning("沒有找到有效的 embedding")
                return []
            
            # 計算相似度
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
            
            # 按相似度排序
            results_with_scores.sort(key=lambda x: x['score'], reverse=True)
            
            # 如果需要優先表格內容
            if prioritize_tables:
                table_results = [r for r in results_with_scores if r.get('metadata', {}).get('has_structured_data', False)]
                non_table_results = [r for r in results_with_scores if not r.get('metadata', {}).get('has_structured_data', False)]
                
                final_results = []
                table_limit = min(len(table_results), limit // 2)
                final_results.extend(table_results[:table_limit])
                remaining_limit = limit - len(final_results)
                final_results.extend(non_table_results[:remaining_limit])
                
                results = final_results
            else:
                results = results_with_scores[:limit]
            
            logger.info(f"返回 {len(results)} 個相關塊")
            if results:
                logger.info(f"相似度範圍: {results[-1]['score']:.3f} - {results[0]['score']:.3f}")
            
            return results
        
        except Exception as e:
            logger.error(f"搜索時發生錯誤: {e}")
            return []
    
    def save_analysis_to_mongodb(self, company: str, quarter: str, analysis_results: Dict) -> List[Dict]:
        """將分析結果保存到MongoDB"""
        try:
            current_time = datetime.now()
            title_mapping = settings.get("analysis_settings.title_mapping", {})
            
            saved_docs = []
            
            for analysis_type, analysis_content in analysis_results.items():
                if analysis_type == "year_quarter":
                    continue
                
                title = title_mapping.get(analysis_type, analysis_type)
                
                filter_criteria = {
                    "company": company,
                    "title": title,
                    "quarter": quarter
                }
                
                update_data = {
                    "$set": {
                        "analysis": analysis_content,
                        "updated_at": current_time
                    },
                    "$setOnInsert": {
                        "company": company,
                        "title": title,
                        "quarter": quarter,
                        "created_at": current_time
                    }
                }
                
                result = self.analysis_collection.update_one(
                    filter_criteria,
                    update_data,
                    upsert=True
                )
                
                if result.upserted_id:
                    logger.info(f"新增分析記錄: {company} - {title} - {quarter}")
                    saved_docs.append({
                        "action": "inserted",
                        "company": company,
                        "title": title,
                        "quarter": quarter,
                        "id": str(result.upserted_id)
                    })
                elif result.modified_count > 0:
                    logger.info(f"更新分析記錄: {company} - {title} - {quarter}")
                    saved_docs.append({
                        "action": "updated",
                        "company": company,
                        "title": title,
                        "quarter": quarter
                    })
                else:
                    logger.info(f"分析記錄無變更: {company} - {title} - {quarter}")
                    saved_docs.append({
                        "action": "no_change",
                        "company": company,
                        "title": title,
                        "quarter": quarter
                    })
            
            return saved_docs
            
        except Exception as e:
            logger.error(f"保存分析結果到MongoDB時發生錯誤: {e}")
            return []
    
    def clear_collection(self):
        """清空集合"""
        try:
            self.collection.delete_many({})
            logger.info("成功清空集合")
        except Exception as e:
            logger.error(f"清空集合時發生錯誤: {e}")
    
    def clear_analysis_collection(self, company: str = None, quarter: str = None):
        """清空分析結果集合"""
        try:
            if company or quarter:
                query = {}
                if company:
                    query["company"] = company
                if quarter:
                    query["quarter"] = quarter
                
                count_to_delete = self.analysis_collection.count_documents(query)
                
                if count_to_delete > 0:
                    self.analysis_collection.delete_many(query)
                    logger.info(f"清空分析結果: {query}, 刪除了 {count_to_delete} 筆記錄")
                else:
                    logger.info(f"沒有找到符合條件的分析結果: {query}")
            else:
                total_count = self.analysis_collection.count_documents({})
                confirmation = input(f"確定要刪除所有 {total_count} 筆分析結果嗎？(y/N): ").lower()
                
                if confirmation == 'y':
                    self.analysis_collection.delete_many({})
                    logger.info(f"清空所有分析結果，共刪除 {total_count} 筆記錄")
                else:
                    logger.info("取消清空所有分析結果")
        except Exception as e:
            logger.error(f"清空分析結果時發生錯誤: {e}")