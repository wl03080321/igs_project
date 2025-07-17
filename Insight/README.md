# 洞察報告模組
此模組能夠自動從PDF財報中提取資訊，生成結構化分析報告，並將結果儲存到MongoDB資料庫中。

## 功能特點
本系統具備以下核心功能：

* **多模式PDF處理**：支援文字提取和OCR影像識別兩種模式，針對不同類型的財報自動選擇最佳處理方式
* **智能分塊與向量化**：使用SentenceTransformer模型生成向量表示，支援語意搜尋
* **RAG增強分析**：結合檢索增強生成技術，使用GPT-4.1進行深度財報分析
* **結構化資料管理**：所有原始文件塊和分析結果均存儲於MongoDB資料庫
* **多語言支援**：支援中文、英文、韓文財報的混合處理
* **批量處理能力**：支援多家公司、多季度財報的批量分析和比較

## 專案結構
```
Insight/
│
├── main.py                     # 主程式
├── config.yaml                 # 配置檔
├── requirements.txt            # 套件清單
│
├── config/                     # 設定管理模組
│   ├── __init__.py
│   └── settings.py             # YAML設定讀取工具
│
├── models/                     # 資料模型模組
│   ├── __init__.py
│   └── vector_store.py         # MongoDB向量資料庫類別
│
├── processors/                 # 檔案處理模組
│   ├── __init__.py
│   ├── pdf_processor.py        # PDF文字提取處理
│   └── ocr_processor.py        # OCR圖像處理
│
├── analyzers/                  # 分析模組
│   ├── __init__.py
│   └── rag_analyzer.py         # RAG分析
│
├── utils/                      # 工具模組
│   ├── __init__.py
│   ├── logger.py               # 日誌工具
│   └── file_utils.py           # 檔案處理工具
│
├── logs/                       # 日誌檔案夾（自動建立）
│   └── {日期}.log
│
├── 財報分析/                     # 分析結果輸出資料夾（自動建立）
│   └── 競業財報分析_{時間}.xlsx
│
└── {公司名稱}_財報資料/            # 各公司財報資料夾
    ├── 檔案1.pdf
    ├── 檔案2.pdf
    └── ...
```

## 資料庫結構
### MongoDB 集合說明
**1. insight_report_embeddings**：儲存財報文件的分塊內容和向量表示
```json
{
  "_id": ObjectId,
  "text": "文件內容塊",
  "embedding": [384維向量陣列],
  "metadata": {
    "file_name": "檔案名稱",
    "company_name": "公司名稱", 
    "year": "年份",
    "quarter": "年份_季度",
    "chunk_index": 塊索引,
    "start_page": "起始頁碼",
    "end_page": "結束頁碼",
    "has_structured_data": true/false,
    "is_ocr_content": true/false,
    "extraction_method": "處理方法"
  },
  "created_at": "建立時間"
}
```

**2. financial_analysis**：儲存最終的分析結果
```json
{
  "_id": ObjectId,
  "company": "公司名稱",
  "title": "分析類型", // "公司概況", "商業策略", "風險"
  "quarter": "年份_季度",
  "analysis": "分析內容",
  "created_at": "建立時間",
  "updated_at": "更新時間"
}
```

## 環境設定
### 步驟 1: 安裝 Python 環境
```bash
# 確保使用 Python 3.8 或以上版本
python --version  

# 建議使用虛擬環境
python -m venv financial_analysis_env
# 啟動虛擬環境
# Windows
financial_analysis_env\Scripts\activate
# Linux/Mac
source financial_analysis_env/bin/activate
```

### 步驟 2:  安裝依賴套件
```bash
# 切換到 Insight 目錄
cd Insight
# 安裝所有必要依賴套件
pip install -r requirements.txt
```

主要依賴：
- `pymongo`
- `openai`
- `PyMuPDF`
- `sentence-transformers`
- `scikit-learn`
- `pandas`
- `openpyxl`
- `Pillow`
- `PyYAML`

### 步驟 3: 設定配置檔
編輯 `config.yaml`：
```yaml
# 必要設定項目
openai_settings:
  api_key: "your-openai-api-key-here"  

mongodb_settings:
  uri: "mongodb+srv://<username>:<password>@cluster0.rlfhtdy.mongodb.net/" # MongoDB連線字串  
  database_name: "igs_project"                                             # 資料庫名稱
  collection_name: "insight_report_embeddings"                             # 文件向量集合名稱
  analysis_collection_name: "financial_analysis"                           # 最終分析結果集合名稱
  
file_processing:
  base_directory: "/path/to/your/financial/reports"                        # 財報檔案路徑
```

### 步驟 4: 準備財報檔案
建立財報資料夾結構：
```
您的基礎目錄/
├── DoubleDown_財報資料/
│   ├── DoubleDown_2024Q1.pdf
│   └── DoubleDown_2024Q2.pdf
├── Light Wonder_財報資料/
│   ├── Light Wonder_2024Q1.pdf
│   └── Light Wonder_2024年報.pdf
└── ...
```

**檔案命名規範**
- 檔案夾必須命名為 `{公司名稱}_財報資料`
- 檔名必須包含：
  - 年份（4位數字，如 2024）
  - 季報：包含 Q1、Q2、Q3、Q4
  - 年報：包含 `年報` 或 `Annual Report` 關鍵字
- 檔名範例： 
  - 季報：`{公司名稱}_2024Q1`
  - 年報：`{公司名稱}_2024年報`

## 操作教學
### 執行程式
```bash
python main.py
```
選擇處理模式：
1. **完整重新處理** - 首次使用或重新開始
2. **增量處理** - 只處理新增檔案
3. **只重新分析** - 使用現有資料重新分析
4. **退出程式**

執行日誌記錄於 `logs/YYYYMMDD.log` 檔中

### 自訂分析模板
如需新增分析內容，可編輯 `analyzers/rag_analyzer.py` 中的查詢模板：
```python
# 範例：新增獲利能力分析
queries_zh = {
    "profitability": {
        "query": "分析公司的獲利能力，包括毛利率、營業利益率、淨利率的變化趨勢",
        "keywords_en": "profitability, margin, ROE, ROA, gross profit"
    }
}
```

## 功能擴展
### 新增分析類型
**1. 修改設定檔 `config.yaml`**：
```yaml
analysis_settings:
  analysis_types:
    - "company_overview"
    - "business_strategy"
    - "risks"
    - "market_analysis"    # 新增
  title_mapping:
    market_analysis: "市場分析"
```

**2. 更新分析器 `analyzers/rag_analyzer.py`**：
```python
# 在 analyzers/rag_analyzer.py 中新增
"market_analysis": {
    "query": "分析公司的市場地位和競爭優勢",
    "keywords_en": "market position, competitive advantage, market share"
}
```

### 支援新的檔案格式
**1. 修改檔案工具 `utils/file_utils.py`**：
```python
# 在 utils/file_utils.py 中新增
def process_word_document(file_path):
    # 處理 Word 文件的邏輯
    pass
```

**2. 更新設定 `config.yaml`**：
```yaml
file_processing:
  supported_extensions: [".pdf", ".docx", ".doc"]
```

## 研發成果結案說明
### 專案概述
本項目成功開發了一基於人工智慧的自動化財報分析系統，實現了從PDF財報到結構化分析報告的全自動化處理流程。此系統支援多語言財報處理，並針對不同類型的財報自動選擇最佳的處理策略，顯著提升了財報分析效率和準確性。

### 核心技術
#### 1. **智能文件處理技術**
- **雙模式處理**：PyMuPDF文字提取 + GPT-4 Vision OCR
- **自動策略選擇**：根據檔案類型和公司特性自動選擇最佳處理模式
- **結構化資料提取**：自動識別和提取財報中的表格、圖表資訊

#### 2. **多語言向量化技術**
- **向量模型**：paraphrase-multilingual-MiniLM-L12-v2
- **向量維度**：384維
- **多語言支援**
- **相似度計算**：Cosine Similarity

#### 3. **RAG增強分析技術**
**架構設計**：
```
查詢輸入 → 多階段檢索 → 上下文聚合 → GPT-4.1分析 → 結構化輸出
```

**檢索策略**：
- **第一階段**：基於查詢的直接向量搜尋
- **第二階段**：關鍵詞擴展搜尋
- **第三階段**：通用財務術語搜尋
- **結果聚合**：最多30個相關塊，總長度<300K字符

#### 4. 自適應品質控制技術
- **品質評估機制**：檢查內容長度、關鍵指標、數據完整性
- **自動切換文件處理方式**：初次使用文字提取，品質不佳時自動切換OCR
- **特殊處理**：針對特定公司（Netmarble）直接使用OCR

***
## 注意事項
1. **API 金鑰設定**：必須在 `config.yaml` 中設定有效的 OpenAI API 金鑰
2. **MongoDB 連線**：確保 MongoDB 連線字串正確，同時確認資料庫名稱與集合名稱設定無誤
3. **資料夾命名規範**：財報資料夾必須以 `_財報資料` 結尾
4. **檔案命名規範**：檔名必須包含年份與季度或年報標示，如：`{公司名稱}_2024Q1`、`{公司名稱}_2024年報`
5. **檔案格式支援**：目前僅支援 PDF 格式

## 相關技術資源
- **OpenAI API 文件**：https://platform.openai.com/docs
- **MongoDB 文件**：https://docs.mongodb.com
- **SentenceTransformers**：https://www.sbert.net
