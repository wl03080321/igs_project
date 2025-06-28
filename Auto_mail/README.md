# 自動寄信與Telegram機器人推撥

這個項目是整合資訊後，透過信封方式進行寄送，以及透過Telegram機器人進行推撥。

## 專案結構

```
Auto_mail/
│   main.py                    # 寄信程式
│   telegram_pusher.py         # Telegram機器人推撥程式
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
├── src/                       # 實作模組與工具函式
│   ├── __init__.py
│   ├── emailsender.py         # 寄送 email 的核心模組
│   ├── html1_generative.py    # 產生 HTML 內容
│   ├── logger.py              # 記錄 log 的工具
│   ├── mongodb_client.py      # 與 MongoDB 連線的模組
│   └── script.py              # 執行流程邏輯
```


## 安裝需求

```bash
pip install -r requirements.txt
```

## 環境設定

使用前請修改config/config.yaml連線內容

1. Email 寄信者資訊
2. Email 收信者資訊
3. MongoDB 連線資訊
4. Telegram 機器人token

## 使用方法

### 執行寄信程式

```bash
python main.py
```

### 執行Telegram機器人推撥程式

```bash
python telegram_pusher.py
```

## 注意事項

1. 請確保在執行程式前config.yaml設定需要預先設定。
2. 請確保MongoDB資料表對應的資料是否正確。


