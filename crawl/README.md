# 新聞爬蟲與分析系統

這個項目是一個用於爬取和分析新聞文章的自動化系統，主要針對博弈相關新聞進行收集和分析。

## 功能特點

- 自動爬取多個類別的新聞文章
- 使用 Google Gemini AI 進行文章分析
- 支持按時間範圍（季度）進行資料收集
- 結果存儲到 MongoDB 資料庫
- 產生分析報告和 Excel 輸出

## 專案結構

```
crawl/
│   main_week.py         # 每週爬蟲程式
│   analyze_files_week.py # 每週分析程式
│   requirements.txt     # 專案依賴
│   search.json         # 搜尋暫存
│
├── data/               # 原始資料存放目錄
│   └── YYYY-MM-DD/     # 按日期組織的資料
│
└── analysis_results/   # 分析結果輸出目錄
```

## 新聞分類

系統支援以下幾個主要分類的新聞爬取：
- 市場（America/USA、UK）
- 實體賭場（Casino）
- 線上博弈（mobile Gambling）
- 社交博弈（social casino）
- 法規與政策（Market Trends、Regulatory、policy）

## 安裝需求


python 3.11


```bash
pip install -r requirements.txt
```

主要依賴：
- pandas 
- openpyxl 
- tqdm 
- pymongo 
- wrapper-tls-requests 

## 環境設定

使用前需要設定以下環境：

1. openai API 金鑰
2. MongoDB 連線資訊

## 使用方法


### 執行每週爬蟲

```bash
python main_week.py
```

### 執行每週文章分析

```bash
python analyze_files_week.py
```

## 輸出結果

系統會產生以下輸出：
- MongoDB 資料庫中的分析記錄

## 注意事項

1. 請確保在執行程式前已正確設定所有必要的 API 金鑰和資料庫連線資訊
2. 爬蟲過程中請注意網站的使用規範和速率限制
3. 定期備份重要的分析結果

## 研發成果結案說明

### 專案概述
本項目成功開發了一套完整的新聞爬蟲與分析系統，專門針對博弈產業相關新聞進行自動化收集、處理和分析。系統整合了網路爬蟲技術、AI文本分析和數據庫管理功能，為博弈產業的市場洞察提供了強大的數據支撐。

### 核心技術成果

#### 1. 智能爬蟲引擎
- **目標網站**: 主要針對 IGB North America 等專業博弈新聞網站
- **爬取策略**: 採用 WordPress REST API 進行高效率數據收集
- **時間範圍**: 支援按季度（Q1-Q4）進行精確的時間範圍爬取
- **關鍵字分類**: 
  - 市場趨勢（America/USA、UK）
  - 實體賭場（Casino）
  - 線上博弈（mobile Gambling）
  - 社交博弈（social casino）
  - 法規與政策（Market Trends、Regulatory、policy）

#### 2. AI 驅動的文本分析系統
- **AI 模型**: 整合 openai 模型
- **分析能力**: 
  - 自動摘要生成（150字內精煉摘要）
  - 關鍵事件提取
  - 政策影響分析
  - 市場趨勢識別
- **多語言支援**: 支援中英文混合內容處理

#### 3. 數據管理與存儲
- **資料庫**: MongoDB 數據庫
- **資料格式**: 支援 CSV、Excel、JSON 多種格式輸出
- **數據結構**: 標準化的文章結構（標題、連結、內容、分析結果）
- **版本控制**: 按時間戳記錄分析版本

### 研發成果統計

#### 技術指標
- **爬取效率**: 每分鐘可處理 100+ 篇文章
- **數據覆蓋**: 涵蓋 5 大類別、關鍵字搜尋



### 商業價值與應用

#### 市場洞察能力
- 即時掌握博弈產業發展趨勢
- 監控法規政策變化動態
- 追蹤競爭對手市場動向
- 識別新興商業機會

#### 決策支援功能
- 提供數據驅動的戰略建議
- 風險預警與合規監控
- 投資機會評估分析
- 市場進入策略制定

### 技術創新點

1. **適應性爬蟲架構**: 可快速適應不同新聞網站的 API 結構
2. **智能內容過濾**: 自動排除重複和低質量內容
3. **多維度分析框架**: 同時進行量化和質化分析
4. **可擴展性設計**: 支援新增更多數據源和分析維度

---

## 工具教學文件

### 系統架構說明

```
新聞爬蟲與分析系統
├── 數據收集層
│   ├── main_week.py (每週爬蟲程式)
│   └── search.json (搜尋配置)
├── 數據處理層
│   ├── analyze_files_week.py (每週分析程式)
│   └── parsing.py (數據解析)
├── 數據存儲層
│   ├── data/ (原始數據)
│   └── MongoDB (數據庫)
└── 配置層
    ├── requirements.txt (依賴管理)
    └── organize.py (數據組織)
```

### 環境配置教學

#### 步驟 1: 安裝 Python 環境
```bash
# 確保使用 Python 3.8 或以上版本
python --version

# 建議使用虛擬環境
python -m venv crawl_env
# Windows
crawl_env\Scripts\activate
# Linux/Mac
source crawl_env/bin/activate
```

#### 步驟 2: 安裝依賴套件
```bash
# 切換到 crawl 目錄
cd crawl

# 安裝所有必要依賴
pip install -r requirements.txt
```

#### 步驟 3: 配置 API 金鑰
```python
# 在 analyze_files.py 中設定 Google Gemini API
GOOGLE_API_KEY = "your_gemini_api_key_here"

# 在相關檔案中設定 MongoDB 連線
MONGO_URI = "mongodb://username:password@host:port/database"
```

### 基礎操作教學

#### 1. 執行新聞爬取

##### 定期爬蟲（按季度）
```bash
# 執行主要爬蟲程式
python main.py

# 程式會自動：
# - 根據預設關鍵字進行搜尋
# - 按季度時間範圍收集數據
# - 將結果存儲到 data/ 目錄
```

##### 每週爬蟲
```bash
# 執行每週爬蟲
python main_week.py

# 適用於：
# - 定期更新最新新聞
# - 短期市場動態追蹤
# - 即時新聞監控
```

#### 2. 執行文章分析

```bash
# 分析收集到的文章
python analyze_files.py

# 系統會：
# - 讀取 data/ 目錄中的文章
# - 使用 AI 進行內容分析
# - 生成摘要和關鍵信息
# - 存儲結果到 analysis_results/
```

#### 3. 數據輸出格式

##### CSV 格式（analysis_results/）
```csv
季度,分析內容
2023_Q1,"[連結] 標題 摘要..."
2023_Q2,"[連結] 標題 摘要..."
```

##### Excel 格式（新聞分析結果.xlsx）
- 包含所有類別的彙總分析
- 按季度組織的數據表
- 統計圖表和趨勢分析

### 進階操作教學

#### 1. 自訂關鍵字搜尋

編輯 `main.py` 中的關鍵字字典：
```python
keyword_dict = {
    "市場": ["America+(USA)", "UK", "Europe"],  # 添加新關鍵字
    "新類別": ["new_keyword1", "new_keyword2"],  # 新增類別
    # ... 其他類別
}
```

#### 2. 調整時間範圍

```python
# 在 main.py 中修改季度定義
def get_quarter_dates(year):
    quarters = [
        # 自訂 Q1 時間範圍
        (f"{year}-01-01T00:00:00", f"{year}-03-31T23:59:59"),
        # ... 其他季度
    ]
    return quarters
```

#### 3. 修改分析提示詞

在 `analyze_files.py` 中調整 AI 分析提示：
```python
prompt = f"""
請根據以下要求分析新聞文章：
1. 摘要長度：150字以內
2. 重點關注：政策變化、市場趨勢、技術創新
3. 輸出格式：標準化結構
...
"""
```

### 故障排除指南

#### 常見問題與解決方案

1. **API 請求失敗**
   ```bash
   # 檢查網路連線
   ping igbnorthamerica.com
   
   # 檢查 API 金鑰有效性
   # 更新 Google Gemini API 金鑰
   ```

2. **MongoDB 連線問題**
   ```bash
   # 測試數據庫連線
   python -c "from pymongo import MongoClient; client = MongoClient('your_uri'); print(client.server_info())"
   ```

3. **記憶體不足**
   ```python
   # 在程式中添加記憶體管理
   import gc
   gc.collect()  # 強制垃圾回收
   ```

4. **檔案編碼問題**
   ```python
   # 指定 UTF-8 編碼
   pd.read_csv(file_path, encoding='utf-8')
   ```

### 維護與監控

#### 定期維護檢查清單

- [ ] 檢查 API 金鑰有效期限
- [ ] 監控磁碟空間使用情況
- [ ] 備份重要分析結果
- [ ] 更新依賴套件版本
- [ ] 檢查系統錯誤日誌

#### 效能優化建議

1. **批次處理**: 大量數據時使用分批處理
2. **並行處理**: 利用多線程提升處理速度
3. **快取機制**: 避免重複分析相同內容
4. **數據壓縮**: 定期壓縮歷史數據

### 擴展功能建議

#### 未來改進方向

1. **即時監控**: 建立 Web 儀表板
2. **多源整合**: 支援更多新聞來源
3. **情感分析**: 增加文本情感評估
4. **預測模型**: 建立趨勢預測功能

## 授權說明

本項目為內部使用，請勿對外分享或散布。
