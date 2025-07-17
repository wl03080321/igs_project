import fitz  # PyMuPDF
import time
import base64
import io
from PIL import Image
from typing import List, Dict, Tuple
from openai import OpenAI
from config.settings import settings
from utils.logger import get_logger

logger = get_logger(__name__)

class OCRProcessor:
    """OCR圖像處理器"""
    def __init__(self):
        self.client = OpenAI(api_key=settings.openai_api_key)
        self.current_images = []
    
    def read_pdf_with_ocr(self, file_path: str, max_pages: int = None) -> Tuple[str, int]:
        """使用OCR方式讀取PDF"""
        try:
            logger.info(f"使用OCR方式讀取PDF: {file_path}")
            max_pages_setting = settings.get("file_processing.max_pages_per_pdf", 50)
            max_pages = max_pages or max_pages_setting
            
            # 轉換為圖像
            images = self.pdf_to_images(file_path, max_pages)
            if not images:
                return "", 0
            
            # 批量OCR處理
            batch_size = settings.get("ocr_settings.batch_size", 2)
            extracted_text = self.extract_text_from_image_batch(images, batch_size)
            
            # 確保文本不為空
            if not extracted_text or not extracted_text.strip() or "[OCR提取結果不完整或失敗]" in extracted_text:
                logger.warning("OCR提取失敗")
                return "", 0
            
            # 設置圖像信息
            self.current_images = [
                {
                    "description": f"OCR處理的圖像 {i+1}", 
                    "page": img['page']
                } for i, img in enumerate(images)
            ]
            
            logger.info(f"OCR處理完成: {file_path}")
            logger.info(f"處理頁數: {len(images)}, 提取文本長度: {len(extracted_text)} 字符")
            
            return extracted_text, len(images)
            
        except Exception as e:
            logger.error(f"OCR讀取 {file_path} 時發生錯誤: {e}")
            return "", 0
    
    def pdf_to_images(self, pdf_path: str, max_pages: int) -> List[Dict]:
        """將PDF轉換為圖像列表"""
        try:
            logger.info(f"將PDF轉換為圖像: {pdf_path}")
            pdf_document = fitz.open(pdf_path)
            images = []
            
            total_pages = len(pdf_document)
            pages_to_process = min(total_pages, max_pages)
            
            dpi = settings.get("ocr_settings.dpi", 300)
            image_format = settings.get("ocr_settings.image_format", "png")
            
            for page_num in range(pages_to_process):
                try:
                    page = pdf_document[page_num]
                    # 將頁面轉換為圖像 (高DPI以獲得更好的OCR效果)
                    mat = fitz.Matrix(dpi/72, dpi/72)
                    pix = page.get_pixmap(matrix=mat)
                    img_data = pix.tobytes(image_format)
                    
                    # 轉換為PIL Image
                    pil_image = Image.open(io.BytesIO(img_data))
                    
                    # 轉換為base64
                    buffered = io.BytesIO()
                    pil_image.save(buffered, format=image_format.upper())
                    img_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
                    
                    images.append({
                        'page': page_num + 1,
                        'base64': img_base64,
                        'format': image_format
                    })
                    
                    logger.info(f"已處理頁面 {page_num + 1}/{pages_to_process}")
                    
                except Exception as page_err:
                    logger.warning(f"處理頁面 {page_num + 1} 時發生錯誤: {page_err}")
                    continue
            
            pdf_document.close()
            logger.info(f"成功轉換 {len(images)} 頁為圖像")
            return images
            
        except Exception as e:
            logger.error(f"PDF轉圖像時發生錯誤: {e}")
            return []
    
    def extract_text_from_image_batch(self, images: List[Dict], batch_size: int) -> str:
        """OCR批量處理"""
        all_text_parts = []
        max_retries = settings.get("ocr_settings.max_retries", 2)
        retry_delay = settings.get("ocr_settings.retry_delay", 3)
        
        for i in range(0, len(images), batch_size):
            batch = images[i:i + batch_size]
            logger.info(f"處理圖像批次 {i//batch_size + 1}, 包含 {len(batch)} 頁")
            
            # 重試機制
            retry_count = 0
            extracted_text = None
            
            while retry_count < max_retries and not extracted_text:
                try:
                    # 調整批次大小 - 如果重試，減少批次大小
                    current_batch_size = max(1, batch_size - retry_count)
                    current_batch = batch[:current_batch_size]
                    
                    messages = [
                        {
                            "role": "system", 
                            "content": """你是一個專業的OCR助理，專門處理韓文財務報告。請仔細提取圖像中的所有文字內容，包括：
1. 標題和副標題
2. 表格數據（包括數字和單位）
3. 圖表說明
4. 段落文字
5. 注釋和備註

重要提示：
- 保持原始格式和結構
- 對於韓文內容，如果無法準確識別，請盡量提供相近的韓文字符
- 對於數字和英文，請確保準確性
- 用繁體中文輸出說明文字，韓文專有名詞保留原文"""
                        },
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    "text": f"請提取這 {len(current_batch)} 頁財務報告的所有文字內容，保持原始結構和格式："
                                }
                            ]
                        }
                    ]
                    
                    # 添加圖像
                    for img_data in current_batch:
                        messages[1]["content"].append({
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/{img_data['format']};base64,{img_data['base64']}",
                                "detail": "high"
                            }
                        })
                    
                    # 調用GPT-4 Vision
                    response = self.client.chat.completions.create(
                        model=settings.vision_model,
                        messages=messages,
                        max_tokens=4000,
                        temperature=0.1,
                        timeout=settings.get("openai_settings.timeout", 90)
                    )
                    
                    extracted_text = response.choices[0].message.content
                    
                    # 檢查提取結果質量
                    if extracted_text and len(extracted_text.strip()) > 50:
                        # 添加頁碼標記
                        batch_pages = [img['page'] for img in current_batch]
                        if len(batch_pages) == 1:
                            page_marker = f"\n{'='*50}\n[PAGES {batch_pages[0]}]\n{'='*50}\n"
                        else:
                            page_marker = f"\n{'='*50}\n[PAGES {batch_pages[0]}-{batch_pages[-1]}]\n{'='*50}\n"
                        
                        all_text_parts.append(page_marker + extracted_text)
                        break
                    else:
                        logger.warning(f"OCR提取結果質量不佳，重試 {retry_count + 1}/{max_retries}")
                        retry_count += 1
                        time.sleep(retry_delay)
                
                except Exception as batch_err:
                    retry_count += 1
                    logger.error(f"處理圖像批次時發生錯誤 (嘗試 {retry_count}/{max_retries}): {batch_err}")
                    
                    if retry_count < max_retries:
                        time.sleep(retry_delay)
                    else:
                        # 最後一次嘗試失敗，添加錯誤標記但繼續處理
                        error_pages = [img['page'] for img in batch]
                        error_marker = f"\n{'='*50}\n[ERROR: 無法處理頁面 {error_pages}]\n{'='*50}\n[無法識別區域]\n"
                        all_text_parts.append(error_marker)
            
            # 避免API限制
            time.sleep(2)
        
        result_text = "\n".join(all_text_parts)
        
        # 檢查最終結果
        if not result_text or len(result_text.strip()) < 100:
            logger.warning("OCR提取結果可能不完整")
            return "[OCR提取結果不完整或失敗]"
        
        return result_text