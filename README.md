````markdown
# IGS Project 說明文件

## 專案簡介

本專案為整合式財經資訊平台，涵蓋財報擷取分析、新聞爬蟲摘要、Email 寄送與 Telegram 推播功能，目標為自動化企業財務洞察與即時通訊。

---

## 模組說明

### 1. Auto\_mail

* **功能**

  * 自動寄送財報摘要 Email。
  * 推播新聞摘要至 Telegram 群組指定主題。
* **資料表使用**

  * 從 `financial_analysis` 讀取分析摘要作為 Email 內容。
  * 從 `insight_report` 擷取新聞摘要，依 `telegram_group.topic_relate` 對應分類後推送至相對應群組／主題。

---

### 2. Insight

* **功能**

  * 擷取財報 PDF，進行文字萃取、財報摘要與向量化處理。
  * 使用語言模型對財報內容進行重點摘要與語意理解分析。
* **資料表使用**

  * 原始擷取文本與向量資料儲存至 `financial_analysis_embeddings`。
  * 摘要分析內容儲存至 `financial_analysis`。

---

### 3. crawl

* **功能**

  * 自動化爬取財經相關新聞或網站內容。
  * 使用語言模型生成重點摘要。
* **資料表使用**

  * 將爬取的原始新聞與其摘要整理後存入 `insight_report`。

---

### 4. AutoML

* **功能**

  * 自動從 MongoDB 擷取歷史財報營收資料。
  * 執行多模型訓練（支援 7 種機器學習演算法），自動選擇最佳模型。
  * 預測未來 1～8 個季度的營收表現。
  * 將預測結果寫回資料庫，供後續分析或應用。
* **資料表使用**

  * 從 `financial_revenue` 中讀取 `data_type = actual` 的歷史營收資料作為訓練資料來源。
  * 將預測結果以 `data_type = forecast` 寫入回 `financial_revenue`。

---

## MongoDB Collections 詳細說明

| Collection 名稱        | 模組 | 描述 |
|-------------------------|------|------|
| `financial_analysis_embeddings` | Insight | 儲存財報原文及其向量資訊與相關 metadata。 |
| `financial_analysis`            | Insight、Auto_mail | 儲存財報分析結果摘要，供 Email 發送使用。 |
| `insight_report`                | crawl、Auto_mail | 儲存爬蟲擷取新聞原文與摘要內容，分類與關鍵字並用於推播。 |
| `telegram_group`                | Auto_mail | Telegram 群組與話題設定資料。 |
| `country_revenue`               | - | 儲存不同公司於各國各季度的營收資料，供財報分析使用。 |
| `department_revenue`            | - | 儲存公司部門在各季度的營收數據。 |
| `financial_revenue`             | AutoML | 儲存各公司在不同季度的財報數值（包含實際與預測資料）。 |
| `mobile_revenue`                | - | 儲存公司在 Mobile 的營收資料。 |
| `product_revenue`               | - | 儲存公司特定產品類別的營收資訊。 |
| `web_revenue`                   | - | 儲存公司在 Web 的營收資料。 |


---

## 資料表結構

<details>
<summary><strong>financial_analysis_embeddings</strong></summary>

- `text`: 財報原文  
- `embedding`: 向量資料  
- `metadata`:  
  - `file_name`: 檔案名稱  
  - `company_name`: 公司名稱  
  - `year`: 年份  
  - `quarter`: 財報季度  
  - `total_pages`: 檔案總頁數  
  - `processing_mode`: 檔案處理模式  
  - `extraction_method`: 文字擷取方法  
  - `model_combo`: 使用的語言模型與嵌入模型組合  
  - `tables_extracted`: 擷取的表格數  
  - `images_extracted`: 擷取的圖片數  
  - `attempt_number`: 處理嘗試次數  
  - `chunk_index`: 此筆資料在報告中的分段編號  
  - `total_chunks`: 報告被分段的總數  
  - `chunk_length`: 此段文字的字元長度  
  - `start_page`: 擷取起始頁碼  
  - `end_page`: 擷取結束頁碼  
  - `pages_covered`: 涵蓋的頁碼清單  
  - `is_partial_page`: 是否為部分頁擷取  
  - `has_structured_data`: 是否包含結構化資料  
  - `is_ocr_content`: 是否為 OCR 擷取內容  
  - `embedding_model`: 使用的嵌入模型  
  - `embedding_dimensions`: 向量維度  

</details>

<details>
<summary><strong>financial_analysis</strong></summary>

- `company`: 公司名稱  
- `title`: 主題名稱  
- `quarter`: 季度  
- `analysis`: 分析摘要文字  
- `created_at`, `updated_at`: 建立、更新時間  

</details>

<details>
<summary><strong>insight_report</strong></summary>

- `category`: 分類  
- `filename`, `link`, `original_title`: 原始資訊  
- `標題`, `摘要`, `標籤`: 內文資訊與標籤資訊
- `date`: 新聞上架時間
- `created_at`: 建立時間

</details>

<details>
<summary><strong>telegram_group</strong></summary>

- `topic_id`: 群組主題 ID  
- `topic_name`: 主題名稱  
- `topic_relate`: 對應 `insight_report.category`  
- `group_id`: Telegram 群組 ID  
- `created_at` : 建立時間

</details>

<details>
<summary><strong>country_revenue</strong></summary>

- `company`: 公司名稱  
- `year_quarter`: 查詢資料的年度與季度  
- `country`: 國家名稱  
- `value`: 營收值  
- `created_at`: 建立時間  

</details>

<details>
<summary><strong>department_revenue</strong></summary>

- `company`: 公司名稱  
- `year_quarter`: 查詢資料的年度與季度  
- `department`: 公司部門名稱  
- `value`: 營收值  
- `created_at`: 建立時間  

</details>

<details>
<summary><strong>financial_revenue</strong></summary>

- `company`: 公司名稱  
- `year_quarter`: 查詢資料的年度與季度  
- `value`: 營收值  
- `data_type`: 資料型態（actual 或 forecast）  
- `created_at`: 建立時間  

</details>

<details>
<summary><strong>product_revenue</strong></summary>

- `company`: 公司名稱  
- `year_quarter`: 查詢資料的年度與季度  
- `product`: 產品名稱  
- `value`: 營收值  
- `created_at`: 建立時間  

</details>

<details>
<summary><strong>mobile_revenue</strong></summary>

- `company`: 公司名稱  
- `year_quarter`: 查詢資料的年度與季度  
- `value`: 營收值  
- `created_at`: 建立時間  

</details>

<details>
<summary><strong>web_revenue</strong></summary>

- `company`: 公司名稱  
- `year_quarter`: 查詢資料的年度與季度  
- `value`: 營收值  
- `created_at`: 建立時間  

</details>

---

## 專案路徑架構

```
igs_project/
├── Auto_mail/       # 自動寄信與 Telegram 通知
├── Insight/         # 財報摘要處理
├── crawl/           # 爬蟲與新聞摘要
├── AutoML/          # AutoML模組
├── README.md        # 本說明文件
└── igs_project.zip  # MongoDB資料表資料
```
