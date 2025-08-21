import os
import pandas as pd
import openai
from pathlib import Path
import time
from tqdm import tqdm
import json
from pymongo import MongoClient
from datetime import datetime, timedelta

def load_config():
    """載入配置文件"""
    try:
        with open('config.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print("config.json 不存在，使用預設值")
        return None

# 載入配置
config = load_config()

if config:
    # 從配置文件讀取
    OPENAI_API_KEY = config["openai"]["api_key"]
    OPENAI_MODEL = config["openai"]["model"]
    OPENAI_MAX_TOKENS = config["openai"]["max_tokens"]
    OPENAI_TEMPERATURE = config["openai"]["temperature"]
    
    MONGO_URI = config["mongodb"]["uri"]
    MONGO_DATABASE = config["mongodb"]["database"]
    MONGO_COLLECTION = config["mongodb"]["collection"]
    
    RATE_LIMIT_DELAY = config["analysis"]["rate_limit_delay"]
    AVAILABLE_TAGS = config["analysis"]["tags"]
    print("已載入配置文件")
else:
    # 預設值
    OPENAI_API_KEY = "your_openai_api_key_here"
    OPENAI_MODEL = "gpt-4o"
    OPENAI_MAX_TOKENS = 300
    OPENAI_TEMPERATURE = 0.7
    
    MONGO_URI = "your_mongodb_uri_here"
    MONGO_DATABASE = "igs_project"
    MONGO_COLLECTION = "insight_report"
    
    RATE_LIMIT_DELAY = 1
    AVAILABLE_TAGS = ["市場", "法規", "政策", "集體訴訟", "訴訟", "州禁令"]
    print("使用預設配置")

# Configure OpenAI API
openai.api_key = OPENAI_API_KEY

# MongoDB connection
client = MongoClient(MONGO_URI)
db = client[MONGO_DATABASE]
collection = db[MONGO_COLLECTION]

def get_category_from_filename(filename):
    """Extract category from filename"""
    return filename.replace('.json', '')

def analyze_article_with_openai(article):
    """Analyze a single article using OpenAI API (v1.x syntax)"""
    try:
        tags_str = "、".join(AVAILABLE_TAGS)
        prompt = f"""請分析以下文章並提供：\n1. 將標題從英文翻譯成繁體中文\n2. 提供150字內的繁體中文摘要\n3. 根據內容，僅能從下列標籤中選擇1~3個最合適的繁體中文標籤（以逗號分隔）：\n{tags_str}\n\n文章內容：\n標題：{article.get('title', '')}\n內容：{article.get('content', '')}\n\n請直接輸出以下JSON格式（務必用雙引號），其他內容都不要留：\n{{"標題":"","摘要":"","標籤":["",""]}}"""
        response = openai.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=OPENAI_MAX_TOKENS,
            temperature=OPENAI_TEMPERATURE
        )
        content = response.choices[0].message.content
        print("[OpenAI 回傳內容]:", content)  # debug log
        import json, ast, re
        # 嘗試直接解析
        try:
            result = json.loads(content)
        except Exception:
            # 嘗試用正則萃取 JSON 區塊
            match = re.search(r'\{.*\}', content, re.DOTALL)
            if match:
                json_str = match.group(0)
                try:
                    result = json.loads(json_str)
                except Exception:
                    try:
                        result = ast.literal_eval(json_str)
                    except Exception:
                        result = {'標題': '', '摘要': '', '標籤': ''}
            else:
                result = {'標題': '', '摘要': '', '標籤': ''}
        return result
    except Exception as e:
        print(f"Error analyzing article: {str(e)}")
        return f"Error analyzing article: {str(e)}"

def process_json_files():
    """Process all JSON files in the data directory based on config date range"""
    # 從配置獲取時間範圍和資料根目錄
    if config:
        data_root = config["data_root"]
        # 計算動態時間
        hours_before = config.get("hours_before", 3)
        now = datetime.now()
        date_before = now.strftime("%Y-%m-%dT%H:%M:%S")
        date_after = (now - timedelta(hours=hours_before)).strftime("%Y-%m-%dT%H:%M:%S")
    else:
        data_root = "./data"
        # 使用動態時間作為預設值
        now = datetime.now()
        date_before = now.strftime("%Y-%m-%dT%H:%M:%S")
        date_after = (now - timedelta(hours=3)).strftime("%Y-%m-%dT%H:%M:%S")
    
    # 根據時間範圍計算資料夾名稱
    start_date = datetime.strptime(date_after, "%Y-%m-%dT%H:%M:%S")
    end_date = datetime.strptime(date_before, "%Y-%m-%dT%H:%M:%S")
    target_dir_name = f"{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}"
    target_dir = Path(data_root) / target_dir_name
    
    print(f"目標資料夾: {target_dir}")
    
    # 檢查目標資料夾是否存在
    if not target_dir.exists():
        print(f"錯誤: 資料夾 {target_dir} 不存在！")
        return {}
    
    # 只處理目標資料夾中的 JSON 文件
    all_files = list(target_dir.glob("*.json"))
    
    if not all_files:
        print(f"警告: 在 {target_dir} 中沒有找到 JSON 文件")
        return {}
    
    print(f"找到 {len(all_files)} 個 JSON 文件")
    
    # Group files by category
    categories = {}
    for file in all_files:
        category = get_category_from_filename(file.name)
        if category not in categories:
            categories[category] = []
        categories[category].append(file)
    
    # Process each category
    results = {}
    for category, files in categories.items():
        print(f"\nProcessing category: {category}")
        category_results = {}
        
        for file in tqdm(files, desc=f"Processing {category}"):
            try:
                with open(file, 'r', encoding='utf-8') as f:
                    articles = json.load(f)
                
                file_results = []
                for article in articles:
                    analysis = analyze_article_with_openai(article)
                    result = {
                        'link': article.get('link', ''),
                        'original_title': article.get('title', ''),
                        '標題': analysis.get('標題', ''),
                        '摘要': analysis.get('摘要', ''),
                        '標籤': analysis.get('標籤', '')
                    }
                    file_results.append(result)
                    time.sleep(RATE_LIMIT_DELAY)  # Rate limiting from config
                
                category_results[file.name] = file_results
                
            except Exception as e:
                print(f"Error processing {file}: {str(e)}")
        
        results[category] = category_results
    
    return results

def preview_results(results):
    """Preview the analysis results"""
    print("\n=== 分析結果預覽 ===")
    for category, files in results.items():
        print(f"\n類別: {category}")
        for filename, articles in files.items():
            print(f"\n檔案: {filename}")
            for article in articles:
                print("\n---")
                print(f"連結: {article['link']}")
                print(f"原始標題: {article['original_title']}")
                print(f"標題: {article['標題']}")
                print(f"摘要: {article['摘要']}")
                print(f"標籤: {article['標籤']}")
                print("---")

def save_to_mongodb(results):
    """Save results to MongoDB collection"""
    timestamp = datetime.now()
    
    # 從配置獲取時間範圍來設定日期標識
    if config:
        # 計算動態時間
        hours_before = config.get("hours_before", 3)
        now = datetime.now()
        date_before = now.strftime("%Y-%m-%dT%H:%M:%S")
        date_after = (now - timedelta(hours=hours_before)).strftime("%Y-%m-%dT%H:%M:%S")
    else:
        # 使用動態時間作為預設值
        now = datetime.now()
        date_before = now.strftime("%Y-%m-%dT%H:%M:%S")
        date_after = (now - timedelta(hours=3)).strftime("%Y-%m-%dT%H:%M:%S")
    
    # 計算日期標識
    start_date = datetime.strptime(date_after, "%Y-%m-%dT%H:%M:%S")
    end_date = datetime.strptime(date_before, "%Y-%m-%dT%H:%M:%S")
    date_identifier = f"{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}"
    
    for category, files in results.items():
        for filename, articles in files.items():
            for article in articles:
                # Prepare document for MongoDB
                document = {
                    'category': category,
                    'filename': filename,
                    'link': article['link'],
                    'original_title': article['original_title'],
                    '標題': article['標題'],
                    '摘要': article['摘要'],
                    '標籤': article['標籤'],
                    'created_at': timestamp,
                    'date': date_identifier,
                }
                # Insert into MongoDB
                try:
                    collection.insert_one(document)
                    print(f"已儲存 {category} - {filename} 的分析結果至 MongoDB")
                except Exception as e:
                    print(f"儲存 {category} - {filename} 時發生錯誤: {str(e)}")

def main():
    print("開始分析新聞文章...")
    results = process_json_files()
    
    # Preview results before saving
    preview_results(results)
    
    # Ask for confirmation before saving to MongoDB
    save_confirm = 'y'
    if save_confirm.lower() == 'y':
        print("\n正在儲存結果到 MongoDB...")
        save_to_mongodb(results)
        print("分析完成！結果已儲存至 MongoDB insight_report 集合")
    else:
        print("已取消儲存至 MongoDB")
    
    # Close MongoDB connection
    client.close()

if __name__ == "__main__":
    main()