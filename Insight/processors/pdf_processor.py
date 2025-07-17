import fitz  # PyMuPDF
import pandas as pd
from typing import List, Dict, Tuple
from config.settings import settings
from utils.logger import get_logger

logger = get_logger(__name__)

class PDFProcessor:
    """PDF文字提取處理器"""   
    def __init__(self):
        self.current_tables = []
        self.current_images = []
    
    def read_pdf_text_extraction(self, file_path: str, max_pages: int = None) -> Tuple[str, int]:
        """使用 PyMuPDF 進行文字提取"""
        try:
            logger.info(f"使用 PyMuPDF 文字提取讀取 PDF: {file_path}")
            pdf_document = fitz.open(file_path)
            
            total_pages = len(pdf_document)
            max_pages_setting = settings.get("file_processing.max_pages_per_pdf", 50)
            pages_to_read = total_pages if max_pages is None else min(total_pages, max_pages or max_pages_setting)
            
            logger.info(f"PDF 總頁數: {total_pages}, 處理頁數: {pages_to_read}")
            
            # 提取文本內容
            all_text_parts = []
            
            for page_num in range(pages_to_read):
                try:
                    page = pdf_document[page_num]
                    
                    # 使用更好的文本提取方法
                    text_dict = page.get_text("dict")
                    page_text = self._extract_text_from_dict(text_dict)
                    
                    # 添加清晰的頁碼標記
                    page_marker = f"\n{'='*50}\n[PAGE {page_num + 1}]\n{'='*50}\n"
                    all_text_parts.append(page_marker + page_text)
                
                except Exception as page_err:
                    logger.warning(f"處理頁面 {page_num + 1} 時發生錯誤: {page_err}")
                    continue
            
            pdf_document.close()
            
            # 合併文本
            combined_text = "\n".join(all_text_parts)
            
            # 提取表格
            tables = self.extract_tables_from_pdf(file_path)
            self.current_tables = tables
            
            # 提取圖像資訊
            images = self.extract_images_info(file_path)
            self.current_images = images
            
            # 將表格內容整合到文本中
            if tables:
                table_section = "\n\n=== 結構化表格資料 ===\n"
                for table in tables:
                    table_section += f"\n{table['text']}\n"
                combined_text += table_section
            
            # 添加圖像資訊
            if images:
                image_section = "\n\n=== 圖像資訊 ===\n"
                for img in images:
                    image_section += f"{img['description']}: {img['width']}x{img['height']} ({img['ext']})\n"
                combined_text += image_section
            
            logger.info(f"成功讀取 PDF: {file_path}")
            logger.info(f"提取頁數: {pages_to_read}, 表格數: {len(tables)}, 圖像數: {len(images)}")
            logger.info(f"總文本長度: {len(combined_text)} 字符")
            
            return combined_text, total_pages
        
        except Exception as e:
            logger.error(f"讀取 {file_path} 時發生錯誤: {e}")
            return "", 0
    
    def _extract_text_from_dict(self, text_dict: Dict) -> str:
        """從 PyMuPDF 的字典格式中提取文本"""
        try:
            text_parts = []
            
            for block in text_dict.get("blocks", []):
                if "lines" in block:  # 文本塊
                    for line in block["lines"]:
                        line_text = ""
                        for span in line.get("spans", []):
                            line_text += span.get("text", "")
                        if line_text.strip():
                            text_parts.append(line_text.strip())
            
            return "\n".join(text_parts)
        
        except Exception as e:
            logger.warning(f"從字典提取文本時發生錯誤: {e}")
            return ""
    
    def extract_tables_from_pdf(self, pdf_path: str) -> List[Dict]:
        """使用 PyMuPDF 從 PDF 中提取表格"""
        try:
            logger.info(f"從 PDF 提取表格: {pdf_path}")
            pdf_document = fitz.open(pdf_path)
            tables = []
            
            for page_num, page in enumerate(pdf_document):
                try:
                    # PyMuPDF 的表格提取功能
                    tab_rect_list = page.find_tables()
                    
                    if tab_rect_list:
                        for tab_rect in tab_rect_list.tables:
                            try:
                                # 獲取表格實例
                                tab_inst = tab_rect.extract()
                                
                                if tab_inst and len(tab_inst) > 1:
                                    # 處理表格標題和數據
                                    headers = tab_inst[0] if tab_inst[0] else [f"欄位{i+1}" for i in range(len(tab_inst[1]))]
                                    data = tab_inst[1:]
                                    
                                    if data:
                                        # 創建 DataFrame
                                        df = pd.DataFrame(data, columns=headers)
                                        df = df.fillna('')
                                        
                                        # 清理空行和空列
                                        df = df.loc[~df.apply(lambda x: x.astype(str).str.strip().eq('').all(), axis=1)]
                                        df = df.loc[:, ~df.apply(lambda x: x.astype(str).str.strip().eq('').all(), axis=0)]
                                        
                                        if not df.empty:
                                            # 將表格轉換為格式化文本
                                            table_text = self._format_table_text(df, page_num + 1)
                                            
                                            tables.append({
                                                "dataframe": df,
                                                "page": page_num + 1,
                                                "text": table_text,
                                                "type": "structured_table"
                                            })
                            
                            except Exception as table_err:
                                logger.warning(f"處理表格時發生錯誤: {table_err}")
                                continue
                
                except Exception as page_err:
                    logger.warning(f"處理頁面 {page_num + 1} 的表格時發生錯誤: {page_err}")
                    continue
            
            pdf_document.close()
            logger.info(f"從 {pdf_path} 中提取了 {len(tables)} 個表格")
            return tables
        
        except Exception as e:
            logger.error(f"提取表格時發生錯誤: {e}")
            return []
    
    def _format_table_text(self, df: pd.DataFrame, page_num: int) -> str:
        """將 DataFrame 格式化為適合 RAG 的文本"""
        try:
            # 創建表格的文本表示
            lines = [f"=== 表格 (第 {page_num} 頁) ==="]
            
            # 添加標題行
            headers = " | ".join([str(col).strip() for col in df.columns])
            lines.append(headers)
            lines.append("-" * len(headers))
            
            # 添加數據行
            for _, row in df.iterrows():
                row_text = " | ".join([str(val).strip() for val in row.values])
                if row_text.strip():  # 只添加非空行
                    lines.append(row_text)
            
            return "\n".join(lines)
        
        except Exception as e:
            logger.warning(f"格式化表格時發生錯誤: {e}")
            return df.to_string(index=False)
    
    def extract_images_info(self, pdf_path: str) -> List[Dict]:
        """提取 PDF 中的圖像資訊"""
        try:
            pdf_document = fitz.open(pdf_path)
            images = []
            
            for page_num, page in enumerate(pdf_document):
                img_list = page.get_images(full=True)
                
                for img_index, img in enumerate(img_list):
                    try:
                        xref = img[0]
                        base_image = pdf_document.extract_image(xref)
                        
                        images.append({
                            "page": page_num + 1,
                            "index": img_index,
                            "width": base_image["width"],
                            "height": base_image["height"],
                            "ext": base_image["ext"],
                            "description": f"圖像 {img_index + 1} (第 {page_num + 1} 頁)"
                        })
                    
                    except Exception as img_err:
                        logger.warning(f"處理圖像時發生錯誤: {img_err}")
                        continue
            
            pdf_document.close()
            return images
        
        except Exception as e:
            logger.error(f"提取圖像資訊時發生錯誤: {e}")
            return []