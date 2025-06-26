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
│   main.py              # 主要爬蟲程式
│   main_week.py         # 每週爬蟲程式
│   analyze_files.py     # 文章分析程式
│   analyze_files_week.py # 每週分析程式
│   requirements.txt     # 專案依賴
│   search.json         # 搜尋設定
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

```bash
pip install -r requirements.txt
```

主要依賴：
- pandas >= 2.0.0
- google-generativeai >= 0.3.0
- openpyxl >= 3.1.0
- tqdm >= 4.65.0

## 環境設定

使用前需要設定以下環境：

1. Google Gemini API 金鑰
2. MongoDB 連線資訊

## 使用方法

### 執行定期爬蟲

```bash
python main.py
```

### 執行每週爬蟲

```bash
python main_week.py
```

### 執行文章分析

```bash
python analyze_files.py
```

## 輸出結果

系統會產生以下輸出：
- CSV 格式的分析結果（位於 analysis_results 目錄）
- Excel 格式的整合報告（新聞分析結果.xlsx）
- MongoDB 資料庫中的分析記錄

## 注意事項

1. 請確保在執行程式前已正確設定所有必要的 API 金鑰和資料庫連線資訊
2. 爬蟲過程中請注意網站的使用規範和速率限制
3. 定期備份重要的分析結果

## 授權說明

本項目為內部使用，請勿對外分享或散布。
