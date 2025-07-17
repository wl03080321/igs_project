import tls_requests
import pandas as pd
import datetime
import os
import json



def fetch_posts(url,keyword, per_page, page,date_after,date_before,):
    search_content = []
    Crawl_continue = True

    while Crawl_continue :
        try:
            burp0_url = f"{url}wp-json/wp/v2/posts?search={keyword}&per_page={per_page}&page={page}&orderby=date&order=desc&before={date_before}&after={date_after}"

            response = tls_requests.get(burp0_url)
            search_page = response.json()
            search_content.extend(search_page)
            print(f"Page {page}")
            if len(search_page) != per_page:
                Crawl_continue = False

        except Exception as e:
            print(f"Error occurred: {e}")
            Crawl_continue = False
        page += 1

    return search_content


keyword_dict={
  "實體賭場": ["Casino"],
  "線上博弈": ["mobile+Gambling"],
  "社交博弈": ["social+casino"],
  "法規與政策": ["Market+Trends", "Regulatory", "policy","class+action", "lawsuit", "state+prohibition", "state+ban"],
  "平台":["App+Store", "Google+Play"],

}

webs = ["https://www.igamingbusiness.com/","https://cdcgaming.com/"]

date_after = "2025-07-01T00:00:00"
date_before = "2025-07-01T23:59:59"

# 確保根 data 資料夾存在
data_root = "./data"
if not os.path.exists(data_root):
    os.makedirs(data_root)
    print(f"Created directory: {data_root}")

# Create directory based on date range
start_date = datetime.datetime.strptime(date_after, "%Y-%m-%dT%H:%M:%S")
end_date = datetime.datetime.strptime(date_before, "%Y-%m-%dT%H:%M:%S")
dir_name = f"./data/{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}"
os.makedirs(dir_name, exist_ok=True)

for classification, keywords in keyword_dict.items():
    search_content = []
    
    for keyword in keywords:
        for web in webs:
            post_count = 100
            page = 1
            per_page = 100

            print(f"Classification: {classification}, Keyword: {keyword}, Web: {web}, Page: {page}")
            
            post = fetch_posts(web, keyword, per_page, page, date_after, date_before)
            search_content += post

    # 處理當前季度的數據
    if search_content:  # 只在有數據時處理
        data = []
        for page in search_content:
            article_date = datetime.datetime.strptime(page['date'], "%Y-%m-%dT%H:%M:%S")
            data.append({
                "title": page['title']['rendered'],
                "date": page['date'],
                "link": page['link'],
                "content": page['content']['rendered']
            })

        # 將數據轉換為 DataFrame
        df = pd.DataFrame(data)

        # 輸出 DataFrame
        print(f"\nFound {len(df)} articles for {classification}")

        # 保存為 JSON 文件
        filename = f"{dir_name}/{classification}.json"
        df.to_json(filename, orient='records', force_ascii=False, indent=2)
        print(f"Saved to {filename}")
    
    # 清空當前季度的搜索內容，準備處理下一個季度
    search_content = []