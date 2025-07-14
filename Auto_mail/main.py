from src.emailsender import EmailSender
from src.mongodb_client import MongoDBClient
from src.html_generative import generate_combined_html
from src.script import load_config
from typing import List, Tuple, Dict, Any
import os
import json

def load_dashboards_from_json(json_path: str) -> List[Tuple[str, str]]:
        """
        從 JSON 檔案中讀取 Tableau 報表資料。

        Returns:
            List of (name, url) tuples
        """
        dashboards = {}
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                dashboards["url"] = data.get("url", "")
                dashboards["name"] = data.get("name", "")
        except Exception as e:
            error_msg = f"Failed to load dashboards from JSON: {e}"
            raise RuntimeError(error_msg)
        return dashboards

def generate_financial_report_html(
    tableau_json_path: str,
    client: MongoDBClient,
    db_name: str,
    collection_name: str,
    quarter: str = "2025_Q1"
) -> str:
    """
    生成包含Tableau儀表板和MongoDB公司資料的HTML報表。
    
    Args:
        tableau_json_path: Tableau儀表板JSON文件的路徑
        client: MongoDB客戶端實例
        db_name: 數據庫名稱
        collection_name: 集合名稱
        
    Returns:
        str: 生成的HTML內容
        
    Raises:
        ValueError: 如果沒有找到Tableau儀表板
    """
    # 讀取 Tableau Dashboard JSON
    dashboards = load_dashboards_from_json(tableau_json_path)

    # 讀取 MongoDB 公司資料
    companies = client.get_distinct(
        db_name=db_name,
        collection_name=collection_name,
        field="company"
    )
    
    grouped_result: Dict[str, List[Dict[str, Any]]] = {}
    for company in companies:
        
        created_at_values = client.get_distinct(
            db_name=db_name,
            collection_name=collection_name,
            field="created_at",
            filter_dict={"company": company}
        )
        
        if not created_at_values:
            grouped_result[company] = []
            continue
        
        latest_created_at = max(created_at_values)
        
        data = client.query_by_fields(
            db_name=db_name,
            collection_name=collection_name,
            filter_dict={
                "company": company,
                "created_at": latest_created_at,
                "title":{"$in":["公司概況", "商業策略", "風險"]},
                "quarter":  quarter
                },
            fields=["title", "analysis", "quarter","link"],
            sort_by=("quarter", 1)  # 按季度和標題排序
        )
        grouped_result[company] = data
        
    #print(f"Grouped result: {grouped_result}")
    if dashboards is None or not dashboards:
        raise ValueError("No Tableau dashboards found in the JSON file.")
    return generate_combined_html(
            tableau_data=dashboards,
            grouped_result=grouped_result,
            quarter=quarter
        )


if __name__ == "__main__":
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        config_path = os.path.join(base_dir, 'config', 'config.yaml')
        attachments_folder = os.path.join(base_dir, 'attachments')
        tableau_json_path = os.path.join(base_dir, 'html_files', 'tableau_dashboards.json')

        if not os.path.exists(attachments_folder):
            os.makedirs(attachments_folder)
            print(f"已建立附件資料夾: {attachments_folder}")
        config = load_config(config_path)

        # 檢查 MongoDB 與 Email 設定
        uri = config.get("mongodb_settings", {}).get("uri", "")
        if not uri:
            raise ValueError("MongoDB URI is not provided in the configuration file.")

        sender_config = config.get("email_settings", {})
        if not sender_config:
            raise ValueError("Email configuration is missing in the configuration file.")

        # 初始化物件
        client = MongoDBClient(uri=uri)
        sender = EmailSender(config=sender_config)

        # 資料參數
        db_name = "igs_project"
        collection_name = "financial_analysis"
        quarter = "2025_Q1"
        # 生成 HTML 報表
        html_body = generate_financial_report_html(
            tableau_json_path=tableau_json_path,
            client=client,
            db_name=db_name,
            collection_name=collection_name,
            quarter=quarter
        )
        
        email_receivers = config.get("email_receivers", {}).get("email_address", [])

        sender.send(
            recipients=email_receivers,
            subject='【AI戰情室】美國競業廠商營收報告_'+ quarter.replace("_", "年"),
            content_text='',
            attachment_files=None,
            attachments_dir=attachments_folder,
            html_body=html_body
        )

    except Exception as e:
        print(f"[主程式發生錯誤] {type(e).__name__}: {e}")



