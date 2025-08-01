# 營收數據提取模組
此模組能夠從已處理的財報向量資料庫中提取總營收數據，使用RAG技術進行智能分析，並將結果儲存到MongoDB資料庫中。

## 功能特點
* **RAG增強營收提取**：結合檢索增強生成技術，使用GPT-4.1從財報向量資料庫中提取總營收數據
* **智能數據解析**：自動識別營收數值、單位（千、百萬、億等）和幣別（USD、KRW等）
* **單位標準化轉換**：所有營收數據統一轉換為百萬美元單位
* **Q4營收計算**：自動計算第四季度營收（全年營收 - Q1~Q3營收）
* **結構化數據管理**：所有營收數據均存儲於MongoDB資料庫，支援增量更新
* **Excel匯出功能**：支援將營收數據匯出為Excel檔案，包含原始數據和轉換後數據

## 專案結構
```
RevenueExtraction/
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
│   └── revenue_store.py        # MongoDB營收資料庫類別
│
├── extractors/                 # 提取模組
│   ├── __init__.py
│   ├── rag_extractor.py        # RAG營收提取器
│   └── q4_calculator.py        # Q4營收計算器
│
├── processors/                 # 處理模組
│   ├── __init__.py
│   ├── unit_converter.py       # 單位轉換處理
│   └── data_parser.py          # 數據解析處理
│
├── exporters/                  # 匯出模組
│   ├── __init__.py
│   └── excel_exporter.py       # Excel匯出工具
│
├── utils/                      # 工具模組
│   ├── __init__.py
│   ├── logger.py               # 日誌工具
│   └── mongodb_utils.py        # MongoDB連接工具
│
├── logs/                       # 日誌檔案夾（自動建立）
│   └── {日期}.log
│
└── 競業營收數據_{時間}.xlsx        # 匯出的Excel檔案
```

## 資料庫結構
### MongoDB 集合說明
**1. financial_analysis_embeddings**：來源財報向量資料庫（由Insight模組建立）
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
    "chunk_index": 塊索引
  }
}
```

**2. financial_revenue_try**：營收數據存儲集合
```json
{
  "_id": ObjectId,
  "company": "公司名稱",
  "year_quarter": "年份_季度", // "2024_Q1", "2024_全年"
  "value": 123.45,            // 標準化後的營收值（百萬美元）
  "original_value": 500.0,    // 原始數值
  "original_unit": "million", // 原始單位
  "original_currency": "USD", // 原始幣別
  "data_type": "actual",      // "actual", "actual_fullyear"
  "created_at": "建立時間"
}
```

## 環境設定
### 步驟 1: 安裝 Python 環境
```bash
# 確保使用 Python 3.8 或以上版本
python --version  

# 建議使用虛擬環境
python -m venv revenue_extraction_env
# 啟動虛擬環境
# Windows
revenue_extraction_env\\Scripts\\activate
# Linux/Mac
source revenue_extraction_env/bin/activate
```

### 步驟 2: 安裝依賴套件
```bash
# 切換到專案目錄
cd RevenueExtraction
# 安裝所有必要依賴套件
pip install -r requirements.txt
```

主要依賴：
- `pymongo` 
- `openai`
- `sentence-transformers` 
- `scikit-learn` 
- `pandas` 
- `openpyxl`
- `PyYAML`

### 步驟 3: 設定配置檔
編輯 `config.yaml`：
```yaml
# 必要設定項目
openai:
  api_key: "your-openai-api-key-here"

mongodb:
  uri: "mongodb+srv://<username>:<password>@cluster0.rlfhtdy.mongodb.net/"
  database_name: "igs_project"
  collections:
    embeddings: "financial_analysis_embeddings"  # 來源向量集合
    revenue: "financial_revenue"                 # 營收數據集合
```

### 步驟 4: 前置條件檢查
**重要：運行此模組前需要先執行Insight模組**
```bash
# 檢查MongoDB中是否存在 financial_analysis_embeddings 集合
```

## 操作教學
### 執行程式
```bash
python main.py
```

### 處理模式選擇
程式提供以下6種處理模式：

**1. 完整重新提取**
- 清空所有現有營收數據並重新提取所有公司季度的營收數據
- 自動計算Q4營收並匯出Excel檔案
- 適用於：首次使用或需要重新開始

**2. 增量提取**
- 只處理尚未提取營收數據的公司/季度組合
- 保留現有數據，只新增缺失的記錄
- 適用於：新增財報後的更新

**3. 只匯出現有數據到Excel**
- 直接將資料庫中的營收數據匯出為Excel
- 適用於：重新產生報表

**4. 清空所有營收數據**
- 刪除所有營收相關集合的數據
- 適用於：重置系統狀態

**5. 單獨計算Q4營收**
- 使用現有的全年和Q1~Q3數據計算Q4營收
- 公式：Q4 = 全年營收 - (Q1 + Q2 + Q3)
- 適用於：補充缺失的Q4數據

**6. 退出程式**

執行流程：
1. **系統檢查**：測試OpenAI API和SentenceTransformer模型連接
2. **資料庫檢查**：驗證MongoDB連接和資料狀態
3. **向量搜尋**：使用多階段檢索策略搜尋相關財報內容
4. **GPT分析**：將搜尋結果送至GPT-4.1進行營收數據提取
5. **數據解析**：提取數值、單位、幣別
6. **單位轉換**：統一轉換為百萬美元單位
7. **數據存儲**：儲存至MongoDB資料庫
8. **Q4計算**：自動計算第四季度營收
9. **Excel匯出**：產生結構化報表

執行日誌記錄於 `logs/YYYYMMDD.log` 檔中

## 功能擴展
### 新增支援的幣別
**1. 修改配置檔 `config.yaml`**：
```yaml
# 匯率設定
exchange_rates:
  KRW_to_USD: 0.000714  # 韓元轉美元 (1/1400)
  USD_to_USD: 1.0       # 美元保持不變
  EUR_to_USD: 1.1       # 歐元轉美元（新增）
  JPY_to_USD: 0.0067    # 日圓轉美元（新增）
  CNY_to_USD: 0.14      # 人民幣轉美元（新增）
  TWD_to_USD: 0.031     # 新台幣轉美元（新增）
```

**2. 更新單位轉換器 `processors/unit_converter.py`**：
```python
def convert_to_million_usd(self, value: Union[str, float, int], unit: str, currency: str) -> float:
    # 在現有程式碼中新增幣別處理
    if currency == "EUR":
        value_in_millions_usd = value_in_millions * self.exchange_rates.get('EUR_to_USD', 1.1)
    elif currency == "JPY":
        value_in_millions_usd = value_in_millions * self.exchange_rates.get('JPY_to_USD', 0.0067)
    elif currency == "CNY":
        value_in_millions_usd = value_in_millions * self.exchange_rates.get('CNY_to_USD', 0.14)
    elif currency == "TWD":
        value_in_millions_usd = value_in_millions * self.exchange_rates.get('TWD_to_USD', 0.031)
    # ... 其他現有程式碼
```

**3. 更新RAG提取器的提示詞 `extractors/rag_extractor.py`**：
```python
def _build_revenue_extraction_prompt(self, context: str, query: str) -> str:
    # 在提示詞中新增幣別識別說明
    prompt = f"""
    3. **幣別處理**：
       - 美元：如果看到 $ 或 USD 或相關描述，記為 USD
       - 韓元：如果看到 원 或 KRW 或相關描述，記為 KRW
       - 歐元：如果看到 € 或 EUR 或相關描述，記為 EUR
       - 日圓：如果看到 ¥ 或 JPY 或相關描述，記為 JPY  
       - 人民幣：如果看到 ¥ 或 CNY 或 RMB 或相關描述，記為 CNY
       - 新台幣：如果看到 NT$ 或 TWD 或相關描述，記為 TWD
    """
```
**修改匯率設定**：
如需更新匯率，只需修改步驟1的配置檔和步驟2的程式碼中對應的匯率數值即可。

### 新增支援的單位
**1. 修改配置檔 `config.yaml`**：
```yaml
unit_conversion:
  # 英文單位（轉換為百萬）
  thousand: 0.001
  thousands: 0.001
  million: 1.0
  millions: 1.0
  billion: 1000.0
  billions: 1000.0
  trillion: 1000000.0     # 兆（新增）
  trillions: 1000000.0    # 兆（新增）
  
  # 韓文單位
  천: 0.001      # 千
  만: 0.01       # 萬
  억: 100.0      # 億
  조: 1000000.0  # 兆（新增）
  
  # 中文單位（新增）
  千: 0.001      # 千
  萬: 0.01       # 萬
  億: 100.0      # 億
  兆: 1000000.0  # 兆
  
  # 日文單位（新增）
  千: 0.001      # 千
  万: 0.01       # 萬
  億: 100.0      # 億
  兆: 1000000.0  # 兆
  
  # 科學記號單位（新增）
  k: 0.001       # 千（k）
  m: 1.0         # 百萬（m）
  b: 1000.0      # 十億（b）
  t: 1000000.0   # 兆（t）
```

**2. 更新單位轉換器 `processors/unit_converter.py`**：
```python
def normalize_unit_name(self, unit_str: Union[str, None]) -> str:
    # 在現有程式碼基礎上新增更多單位變體處理
    unit_str = unit_str.replace('tln', 'trillion')
    unit_str = unit_str.replace('tri', 'trillion')
    
    # 處理科學記號
    unit_str = unit_str.replace('k', 'thousand')
    unit_str = unit_str.replace('m', 'million') 
    unit_str = unit_str.replace('b', 'billion')
    unit_str = unit_str.replace('t', 'trillion')
    
    return unit_str.strip()
```

**3. 更新RAG提取器的提示詞 `extractors/rag_extractor.py`**：
```python
def _build_revenue_extraction_prompt(self, context: str, query: str) -> str:
    # 在提示詞中新增單位識別說明
    return f"""
    2. **單位識別（重要）**：
       - **英文單位**：thousand, million, billion, trillion
       - **韓文單位**：천(千), 만(萬), 억(億), 조(兆)
       - **中文單位**：千, 萬, 億, 兆
       - **日文單位**：千, 万, 億, 兆
       - **科學記號**：K/k(千), M/m(百萬), B/b(十億), T/t(兆)
       - **縮寫形式**：tln/tri(兆), mln(百萬), bln(十億)
       - 如果沒有明確單位，根據上下文和數值大小推測最可能的單位
    """   
```

## 錯誤數據處理建議
**方法一**：刪除錯誤數據後重新提取
- 連接MongoDB後刪除錯誤紀錄
- 執行 `main.py`，選擇 `2. 增量提取` 補充數據

**方法二**：直接在 MongoDB 中手動修正數值

##  研究成果結案說明
### 專案概述
本模組成功開發了基於人工智慧的自動化財報營收數據提取系統，實現了從向量化財報到結構化營收分析的全自動化處理流程。此系統採用RAG增強生成技術，結合GPT-4.1進行智能數據提取，並支援多種貨幣和單位的標準化轉換，顯著提升了財報營收數據處理效率。

### 核心技術說明
#### 1. **RAG增強提取技術**
檢索策略：
- **向量搜尋**：使用SentenceTransformer進行語意搜尋
- **多階段檢索**：基於營收查詢的向量相似度計算
- **結果聚合**：最多20個相關文檔塊，總長度<200K字符
- **GPT分析**：使用專門設計的營收提取Prompt

提取流程：
```
查詢文本 → 向量編碼 → 相似度計算 → 文檔檢索 → 上下文整合 → GPT分析 → JSON解析
```

#### 2. **智能單位轉換**
**支援的單位類型**：
- **英文單位**：thousand, million, billion
- **韓文單位**：천(千), 만(萬), 억(億)
- **自動識別**：根據上下文推測單位

**轉換流程**：
```python
# 轉換公式
標準化數值 = 原始數值 × 單位係數 × 匯率係數
# 例如：500 億 KRW = 500 × 100.0 × 0.000714 = 35.7 Million USD
```

#### 3. **Q4營收計算邏輯**
```python
Q4營收 = 全年營收 - (Q1營收 + Q2營收 + Q3營收)
```

#### 4. **資料品質控制**
- **重複檢查**：使用upsert避免重複記錄
- **數據驗證**：檢查數值合理性和JSON格式
- **錯誤處理**：完整的異常處理和日誌記錄
- **原始數據保留**：保存轉換前的原始數值和單位

***
## 注意事項
1. **API金鑰設定**：必須在 `config.yaml` 中設定有效的 OpenAI API 金鑰
2. **MongoDB 連線**：確保 MongoDB 連線字串正確，同時確認資料庫名稱與集合名稱設定無誤
3. **依賴Insight模組**：必須先有向量化的財報數據，才能進行營收數據提取
4. **匯率固定**：韓元對美元匯率設定為1/1400，需定期更新
5. **數據準確性**：營收數據提取基於AI分析，建議人工抽查驗證
6. **單位轉換**：系統自動進行單位轉換，但建議檢查結果合理性

##  相關技術資源
- **OpenAI API 文件**：https://platform.openai.com/docs
- **MongoDB 文件**：https://docs.mongodb.com
- **SentenceTransformers**：https://www.sbert.net
