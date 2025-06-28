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
        dashboards = []
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for item in data:
                    name = item.get('name')
                    url = item.get('url')
                    if name and url:
                        dashboards.append((name, url))
        except Exception as e:
            error_msg = f"Failed to load dashboards from JSON: {e}"
            raise RuntimeError(error_msg)
        return dashboards

def generate_financial_report_html(
    tableau_json_path: str,
    client: MongoDBClient,
    db_name: str,
    collection_name: str
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
                "created_at": latest_created_at
                },
            fields=["title", "quarter", "analysis","created_at"],
            sort_by=("quarter", 1)  # 按季度和標題排序
        )
        grouped_result[company] = data
        
    if dashboards is None or not dashboards:
        raise ValueError("No Tableau dashboards found in the JSON file.")
        
    return generate_combined_html(dashboards, grouped_result)


if __name__ == "__main__":
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        config_path = os.path.join(base_dir, 'config', 'config.yaml')
        attachments_folder = os.path.join(base_dir, 'attachments')
        tableau_json_path = os.path.join(base_dir, 'html_files', 'tableau_dashboards.json')

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

        # 生成 HTML 報表
        html_body = generate_financial_report_html(
            tableau_json_path=tableau_json_path,
            client=client,
            db_name=db_name,
            collection_name=collection_name
        )
        
        email_receivers = config.get("email_receivers", {}).get("email_address", [])
        # 寄送 Email
        sender.send(
            recipients=email_receivers,
            subject='📎 整合報表寄送',
            content_text='你好，這是自動化報表通知，請參考下方內容與附件資料。',
            attachment_files=None,
            attachments_dir=attachments_folder,
            html_body=html_body
        )

    except Exception as e:
        print(f"[主程式發生錯誤] {type(e).__name__}: {e}")



