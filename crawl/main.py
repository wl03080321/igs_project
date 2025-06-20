import tls_requests
import pandas as pd
import datetime



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

def get_quarter_dates(year):
    quarters = [
        # Q1: Jan 1 - Mar 31
        (f"{year}-01-01T00:00:00", f"{year}-03-31T23:59:59"),
        # Q2: Apr 1 - Jun 30
        (f"{year}-04-01T00:00:00", f"{year}-06-30T23:59:59"),
        # Q3: Jul 1 - Sep 30
        (f"{year}-07-01T00:00:00", f"{year}-09-30T23:59:59"),
        # Q4: Oct 1 - Dec 31
        (f"{year}-10-01T00:00:00", f"{year}-12-31T23:59:59")
    ]
    return quarters

keyword_dict={
  "市場": ["America+(USA)", "UK"],
  "實體賭場": ["Casino"],
  "線上博弈": ["mobile+Gambling"],
  "社交博弈": ["social+casino"],
  "法規與政策": ["Market+Trends", "Regulatory", "policy"],


}
company_dict={
    "Playtika": ["Playtika"],
  "Light":["Light+and+Wonder"],
  "PlayStudios":["PlayStudios"],
  "Netmarble":["Netmarble"],
  "Double":["Double+Down"],
}
webs = ["https://www.igamingbusiness.com/","https://cdcgaming.com/"]

for classification, keywords in company_dict.items():
    search_content = []
    
    # 遍歷年份和季度
    for year in range(2023, 2026):  # 2023-2025
        quarters = get_quarter_dates(year)
        for q_num, (date_after, date_before) in enumerate(quarters, 1):
            print(f"\nProcessing {year} Q{q_num}")
            print(f"Date range: {date_after} to {date_before}")
            
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
                print(f"\nFound {len(df)} articles for {year} Q{q_num}")

                # 保存為季度文件
                filename = f"./data/{classification}_{year}_Q{q_num}.csv"
                df.to_csv(filename, index=False, encoding="utf-8")
                print(f"Saved to {filename}")
            
            # 清空當前季度的搜索內容，準備處理下一個季度
            search_content = []