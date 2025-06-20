import os
import pandas as pd
import openai
from pathlib import Path
import time
from tqdm import tqdm
import json
from pymongo import MongoClient
from datetime import datetime

# Configure OpenAI API
OPENAI_API_KEY = "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"
openai.api_key = OPENAI_API_KEY

# MongoDB connection
MONGO_URI = "mongodb+srv://petercy32:AfEjW3g4z8kPbzgf@cluster0.rlfhtdy.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
client = MongoClient(MONGO_URI)
db = client.igs_project
collection = db.insight_report

def get_category_from_filename(filename):
    """Extract category from filename"""
    return filename.replace('.json', '')

def analyze_article_with_openai(article):
    """Analyze a single article using OpenAI API (v1.x syntax)"""
    try:
        prompt = f"""請分析以下文章並提供：\n1. 將標題從英文翻譯成繁體中文\n2. 提供150字內的繁體中文摘要\n3. 根據內容，僅能從下列標籤中選擇1~3個最合適的繁體中文標籤（以逗號分隔）：\n市場、法規、政策、集體訴訟、訴訟、州禁令\n\n文章內容：\n標題：{article.get('title', '')}\n內容：{article.get('content', '')}\n\n請直接輸出以下JSON格式（務必用雙引號），其他內容都不要留：\n{{"標題":"","摘要":"","標籤":["",""]}}"""
        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=300,
            temperature=0.7
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
    """Process all JSON files in the data directory"""
    data_dir = Path("./data")
    all_files = []
    
    # Find all JSON files in subdirectories
    for subdir in data_dir.iterdir():
        if subdir.is_dir():
            all_files.extend(list(subdir.glob("*.json")))
    
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
                    time.sleep(1)  # Rate limiting
                
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
                    'date': "20250522_20250529",
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
    save_confirm = input("\n是否要將結果儲存至 MongoDB？(y/n): ")
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