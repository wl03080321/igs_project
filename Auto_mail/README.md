# 自動寄信與Telegram機器人推播

這個項目是整合資訊後，透過信封方式進行寄送，以及透過Telegram機器人進行推播。

## 功能特點

本系統具備以下核心功能：

* **資料獲取與儲存**：能從 MongoDB 資料庫中依據需求（如季度、公司）獲取分析資料 。
* **HTML 報告生成**：將擷取到的資料自動整理成帶有關鍵字及頁碼高亮功能的 HTML 報告 。
* **多渠道訊息分發**：
    * 透過電子郵件發送生成的 HTML 報告 。
    * 透過 Telegram Bot 將爬蟲資料之特定主題的週報資訊推送到對應群組 。
* **結構化數據管理**：所有資料均存儲於 MongoDB 資料庫，便於查詢和應用 。

## 專案結構

```
Auto_mail/
│   main.py                    # 寄信程式
│   telegram_pusher.py         # Telegram機器人推播程式
│   requirements.txt           # 相依套件清單
│   
├── config/
│   └── config.yaml            # 設定檔
│
├── attachments/
│   └── (空或儲存附件用的資料夾)
│
├── html_files/
│   └── tableau_dashboards.json # 儲存 Tableau dashboard 的 HTML 設定或元件
│
└── src/                       # 實作模組與工具函式
    ├── __init__.py
    ├── emailsender.py         # 寄送 email 的核心模組
    ├── html1_generative.py    # 產生 HTML 內容
    ├── logger.py              # 記錄 log 的工具
    ├── mongodb_client.py      # 與 MongoDB 連線的模組
    └── script.py              # 共通使用程式
```


## 安裝需求

```bash
pip install -r requirements.txt
```

主要依賴：
- pymongo
- python-telegram-bot
- PyYAML

## 環境設定
#### 步驟 1: 安裝 Python 環境
```bash
# 確保使用 Python 3.8 或以上版本
python --version

# 建議使用虛擬環境
python -m venv automail_env
# Windows
automail_env\Scripts\activate
# Linux/Mac
source automail_env/bin/activate
```

#### 步驟 2: 安裝依賴套件
```bash
# 切換到 Auto_mail 目錄
cd Auto_mail

# 安裝所有必要依賴
pip install -r requirements.txt
```

執行程式碼前請修改config/config.yaml連線內容與html_files/tableau_dashboards.json資訊

config.yaml內容

```yaml
# Email 寄信者資訊，請根據使用的信箱服務相關設定做設置，此範例中是使用Google的郵件伺服器服務
email_settings:
  smtp_server: smtp.gmail.com
  smtp_port: 465
  email_address: wl0308032129@gmail.com
  email_password: 
  use_ssl: true


# Email 收信者資訊，請透過"-"區隔每個信箱使用者，範例如下
email_receivers:
  email_address: 
    - ccchang@mail.ntust.edu.tw
    - arielhuang@igs.com.tw
    - dana.wu.529@gmail.com
    - cindy08150815@gmail.com
    - yufang09190919@gmail.com
    - petercy32@gmail.com

# MongoDB 連線資訊，請將連線的字串填入至url
mongodb_settings:
  uri: mongodb+srv://xxxxxxxxxxxxx:xxxxxxxxxxxxxxx@cluster0.rlfhtdy.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0

# Telegram 機器人token
telegram_settings:
  token: 7xxxxxxxx3:Axxxxxxxxxxxxxxxxxxxxxxxxxxf3A

```

tableau_dashboards.json

```json
// 該資訊為連結Tableau財報網址位置。程式主要使用url網址資料作為HTML導引至Tableau網站位置。
{ "name": "美國競業廠商營收報告", "url": "https://public.tableau.com/app/profile/.48571349/viz/_1_17477238159080/sheet25" }
```

### 基礎操作教學

##### 執行寄信程式

```bash
python main.py

# 程式會運行
# - 根據各公司財報內容整合"公司概況"、"商業策略"、"風險"結果進行資料整理
# - 按設定季度進行資料提取
# - 整理結果透過Email自動寄出信封
```

##### 執行Telegram機器人推播程式

```bash
python telegram_pusher.py

# 程式會運行
# - 根據爬蟲資料整合"實體賭場"、"法規與政策"、"社交博弈"等主題內容進行資料整理
# - 按照資料庫中insight_report表內資料created_at最新資料做提取
# - 根據主題名稱與資料庫中Telegram_topic表對應欄位"topic_relate"資料，將相同主題內容傳送至Telegram群組之主題對話

```

以上程式都會將運行結果紀錄於logs/{日期}.log檔中

### 進階操作教學

#### 1. 指定信封內容季度資料
```python
# 請於 main.py 中調整quarter變數，請依{年}_{季度}設定要取得該年之第幾季資料
# 目前 generate_financial_report_html 函式中只有處理目前要求呈現的狀態。

db_name = "igs_project"
collection_name = "financial_analysis"
quarter = "2025_Q1"
# 生成 HTML 報表
html_body = generate_financial_report_html(
    tableau_json_path=tableau_json_path,
    client=client,
    db_name=db_name,
    collection_name=collection_name,
    quarter=quarter
)

```

#### 2. 調整信封標題與內容
```python
# 同樣於 main.py 中可自行調整subject、content_text、attachment_files、attachments_dir、html_body五個參數
# subject 為信封之標題
# content_text 則以純文字部分添加到信封內容
# attachment_files 為信封之附件檔案，可透過list去調整要寄送哪幾個檔案內容
# attachments_dir 為信封之附件檔案，會將傳遞的資料夾底下所有檔案當作附件做傳送
# html_body 為信封HTML呈現樣式，可根據公司需條調整HTML呈現樣式

sender.send(
    recipients=email_receivers,
    subject='【AI戰情室】美國競業廠商營收報告_'+ quarter.replace("_", "年"),
    content_text='',
    attachment_files=["./attachments/{檔案1}","/attachments/{檔案2}"],
    attachments_dir=["./attachments"],
    html_body=html_body
)
```

#### 3. 設定Telegram機器人推播主題與群組
```json
// 請依據MongoDB資料庫中insight_report表裡category標籤，做為要傳送到Telegram group的聊天位置
// 此內容是insight_report其中一筆資料
{
  "_id": {
    "$oid": "6854c870f14bf38ac3aac3d5"
  },
  "category": "法規與政策",
  "filename": "法規與政策.json",
  "link": "https://igamingbusiness.com/casino/integrated-resorts/thailand-budget-economic-stimulus-casino-resorts/",
  "original_title": "Thailand considers economic stimulus as kingdom gears up for potential casino resorts",
  "標題": "泰國考慮經濟刺激措施以迎接潛在的賭場度假村",
  "摘要": "泰國總理佩通唐·西那瓦提出了3.78萬億泰銖的預算，旨在促進經濟可持續增長，並改善人民生活質量。預算案預計支出增加0.7%，赤字減少0.7%。美國的關稅可能對泰國經濟構成挑戰，因此需要加速自由貿易協定談判和探索新的貿易夥伴。近期的地震和中國遊客綁架事件影響了泰國的旅遊業，遊客數量同比下降1.04%。娛樂綜合體法案被視為吸引投資和推動旅遊業的潛在解決方案，法案已提交參議院審議。",
  "標籤": [
    "政策",
    "法規",
    "市場"
  ],
  "created_at": {
    "$date": "2025-06-20T10:33:18.727Z"
  },
  "date": "20250522_20250529"
}
```

```json
// 此表是MongoDB資料庫中 telegram_topic表中資料內容，該表中topic_relate主要與insight_report表裡category設定一致，當設定相同的主題後，執行telegram_pusher.py時會把對應的主題傳送至對應的群組對話中。
// 當新增新的群組後，把資料寫入至該表中，即可自動把對應主題內容發送訊息至該群組
{
  "_id": {
    "$oid": "686c97955cff26a1b51e923c"
  },
  "topic_id": "2",
  "topic_name": "市場法規政策",
  "topic_relate": "法規與政策",
  "group_id": "-1002760645416",
  "created_at": "2025-07-08T12:00:00Z"
}
```
## 研發成果結案說明

### 專案概述

本項目成功開發並部署了一套自動化數據報告與訊息推送系統。此系統的核心功能是從 MongoDB 資料庫中擷取預先處理好的資訊，將其自動化整理成結構化的 HTML 報告並透過電子郵件發送，同時也能將特定主題的資料透過 Telegram Bot 推送到對應的群組對話中。此系統顯著提升了數據傳遞的效率與報告的即時性。

### 核心技術成果

1.  **資料擷取與整合模組**
    * **資料庫來源**：主要從 MongoDB 資料庫中擷取已結構化儲存的分析報告（如「insight\_report」和「financial\_analysis」集合）以及 Telegram 主題設定（「telegram\_topic」集合）。
    * **彈性查詢機制**：支援根據類別、最新日期、公司、季度等多元條件進行資料查詢與篩選，確保資料的準確性與時效性。
    * **數據重組能力**：能針對不同報告需求，將原始資料按指定欄位（如公司、類別）進行分組整理。

2.  **自動化報告生成引擎 (HTML)**
    * **動態 HTML 生成**：根據從 MongoDB 擷取的數據，自動生成包含豐富內容的 HTML 報告。
    * **多源資訊整合**：能夠將來自 MongoDB 的文本分析結果與外部 Tableau Dashboard 連結整合至同一份報告中。
    * **視覺化優化**：應用 CSS 樣式確保報告的可讀性與專業度，並針對關鍵資訊（如頁碼引用、關鍵字）進行高亮顯示。

3.  **多渠道訊息推送系統**
    * **電子郵件發送模組**：
        * **安全傳輸**：支援 SSL/TLS 加密方式連接 SMTP 伺服器，確保郵件傳輸安全。
        * **豐富內容支援**：可發送純文字或 HTML 格式郵件，並支援多附件夾帶功能（包括單一檔案或整個目錄）。
        * **接收者管理**：可同時發送給多個收件人。
    * **Telegram 自動推送模組**：
        * **精準主題推送**：透過查詢 MongoDB 中預設的 Telegram 主題設定，將特定類別的報告內容推送至對應的 Telegram 群組主題對話中。
        * **訊息分批處理**：支援將長篇報告分批發送，提升訊息傳遞的穩定性與閱讀體驗。
        * **即時狀態回饋**：提供訊息發送成功或失敗的日誌記錄。

### 研發成果統計

#### 產出成果

* **自動化報告發送**：已實現將財報資料統整結果並自動生成並發送市場分析報告。
* **郵件報告產出**：透過郵件系統發送整合式財務分析報告。
* **Telegram 機器人推播**：根據爬蟲資料將對應的主題對話自動傳送至Telegram群組
* **資料類型涵蓋**：成功處理並展示了公司概況、商業策略、風險、市場週報等多種業務相關數據。

---

## 注意事項

1. 請確保在執行程式前config.yaml設定需要預先設定。
2. 請確保MongoDB資料表對應的資料是否正確。
3. 請確保tableau_dashboards.json內容存在。

### 每周執行方案

可根據部屬之電腦設定電腦排程，可根據設定電腦排成並以每周方式執行main.py或telegram_pusher.py程式，即可達到自動化執行效果。
