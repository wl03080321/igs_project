import os
import pandas as pd
import google.generativeai as genai
from pathlib import Path
import time
from tqdm import tqdm
import json
from pymongo import MongoClient
from datetime import datetime

# Configure Gemini API
GOOGLE_API_KEY = "AIzaSyCvxd4EcRIBUKizMJxh8CF5gho4BGzyCk4"  # Replace with your actual API key
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel('gemini-2.0-flash')

# MongoDB connection
MONGO_URI = "mongodb://ccchang:ma-205-4@100.102.183.38:27017/igs_project"
client = MongoClient(MONGO_URI)
db = client.igs_project
collection = db.insight_report

def get_category_from_filename(filename):
    """Extract category from filename"""
    return filename.split('_')[0]

def get_quarter_from_filename(filename):
    """Extract quarter from filename"""
    parts = filename.split('_')
    return f"{parts[1]}_{parts[2].replace('.csv', '')}"

def analyze_file_with_gemini(file_path):
    """Analyze a single file using Gemini API"""
    try:
        df = pd.read_csv(file_path)
        
        # Prepare articles for analysis
        articles_text = []
        for _, row in df.iterrows():
            article = f"標題：{row.get('title', '')}\n"
            article += f"連結：{row.get('link', '')}\n"
            article += f"內容：{row.get('content', '')}\n"
            articles_text.append(article)
        
        combined_text = "\n---\n".join(articles_text)
        
        prompt = f"""請分析以下新聞文章並提供摘要。每篇文章的摘要需包含：
1. 原始連結（純文字顯示）
2. 標題
3. 150字內的摘要，包含最重要的事件、政策、影響等

最後請提供一份300字內的「市場趨勢總結」，說明近期產業整體動態與重點趨勢發展方向。

請使用以下格式輸出：
---
[來源連結]
【標題】
摘要內容

...（每篇依此格式）...

---
【市場總結】
內容

新聞文章內容：
{combined_text}

請確保所有內容都使用繁體中文撰寫。"""

        response = model.generate_content(prompt)
        return response.text

    except Exception as e:
        print(f"Error analyzing {file_path}: {str(e)}")
        return f"Error analyzing file: {str(e)}"

def process_files_in_batches():
    """Process all files in batches of 10"""
    data_dir = Path("./data")
    all_files = [file for file in data_dir.glob("*.csv") ]
    
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
        
        # Process files in batches of 10
        for i in range(0, len(files), 10):
            batch = files[i:i+10]
            for file in tqdm(batch, desc=f"Batch {i//10 + 1}"):
                quarter = get_quarter_from_filename(file.name)
                analysis = analyze_file_with_gemini(file)
                category_results[quarter] = analysis
                time.sleep(1)  # Rate limiting
        
        results[category] = category_results
    
    return results

def save_to_mongodb(results):
    """Save results to MongoDB collection"""
    timestamp = datetime.now()
    
    for category, quarters in results.items():
        for quarter, analysis in quarters.items():
            # Prepare document for MongoDB
            document = {
                'category': category,
                'quarter': quarter,
                'analysis': analysis,
                'created_at': timestamp
            }
            
            # Insert into MongoDB
            try:
                collection.insert_one(document)
                print(f"已儲存 {category} - {quarter} 的分析結果至 MongoDB")
            except Exception as e:
                print(f"儲存 {category} - {quarter} 時發生錯誤: {str(e)}")

def main():
    print("開始分析新聞文章...")
    results = process_files_in_batches()
    print("\n正在儲存結果到 MongoDB...")
    save_to_mongodb(results)
    print("分析完成！結果已儲存至 MongoDB insight_report 集合")
    
    # Close MongoDB connection
    client.close()

if __name__ == "__main__":
    main()