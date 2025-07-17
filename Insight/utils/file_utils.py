import os
import re
import glob
from typing import Tuple, Optional, List
from config.settings import settings
from utils.logger import get_logger

logger = get_logger(__name__)

def is_annual_report(file_name: str) -> bool:
    """判斷檔案是否為年報"""
    annual_indicators = ["年報", "Annual Report", "年度報告", "annual"]
    return any(indicator in file_name for indicator in annual_indicators)

def is_quarterly_report(file_name: str) -> bool:
    """判斷檔案是否為季報"""
    quarterly_indicators = ["Q1", "Q2", "Q3", "Q4", "季報", "quarterly"]
    return any(indicator in file_name for indicator in quarterly_indicators)

def extract_year_and_quarter(file_name: str) -> Tuple[Optional[str], Optional[str]]:
    """從檔名中提取年份與季度資訊"""
    match = re.search(r"(\d{4})(?:Q)?(\d)?", file_name)
    if match:
        year = match.group(1)
        quarter = match.group(2) or "全年"
        if quarter == "全年":
            formatted_quarter = "全年"
        else:
            formatted_quarter = f"Q{quarter}"
        return year, formatted_quarter
    return None, None

def extract_company_name(folder_path: str) -> str:
    """從資料夾路徑提取公司名稱"""
    folder_name = os.path.basename(folder_path)
    folder_suffix = settings.get("file_processing.folder_suffix", "_財報資料")
    company_name = folder_name.replace(folder_suffix, "")
    company_name = re.sub(r'[^\w\-]', '_', company_name)
    return company_name

def find_report_folders(base_dir: str) -> List[str]:
    """尋找所有財報資料夾"""
    report_folders = []
    folder_suffix = settings.get("file_processing.folder_suffix", "_財報資料")
    
    for root, dirs, files in os.walk(base_dir):
        for dir_name in dirs:
            if folder_suffix in dir_name:
                report_folders.append(os.path.join(root, dir_name))
    
    logger.info(f"找到 {len(report_folders)} 個財報資料夾")
    return report_folders

def find_pdf_files(folder: str) -> List[str]:
    """在指定資料夾中尋找PDF檔案"""
    supported_extensions = settings.get("file_processing.supported_extensions", [".pdf"])
    pdf_files = []
    
    for ext in supported_extensions:
        pattern = os.path.join(folder, f"*{ext}")
        pdf_files.extend(glob.glob(pattern))
    
    return pdf_files

def create_output_directory(base_dir: str) -> str:
    """創建輸出目錄"""
    output_dir = settings.get("excel_output.output_directory", "財報分析")
    full_path = os.path.join(base_dir, output_dir)
    os.makedirs(full_path, exist_ok=True)
    return full_path

def generate_excel_filename() -> str:
    """生成Excel檔案名稱"""
    from datetime import datetime
    prefix = settings.get("excel_output.filename_prefix", "競業財報分析")
    datetime_version = datetime.now().strftime("%m%d%H%M")
    return f"{prefix}_{datetime_version}.xlsx"