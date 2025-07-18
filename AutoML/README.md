# AutoML 營收預測模組
此模組自動從 MongoDB 載入財務營收資料，訓練多個機器學習模型，選擇最佳模型預測未來季度的營收表現。

## 功能特點
* **自動資料載入**：從 MongoDB 自動擷取實際財務資料
* **多模型比較**：支援 7 種機器學習演算法，自動選擇最佳模型
* **未來營收預測**：預測未來 1-8 個季度的營收
* **結果自動存儲**：預測結果存回 MongoDB

## 支援的機器學習模型
- **RandomForest**：隨機森林回歸
- **GradientBoosting**：梯度提升回歸  
- **LinearRegression**：線性回歸
- **Ridge**：Ridge 正則化回歸
- **Lasso**：Lasso 正則化回歸
- **SVR**：支援向量回歸
- **XGBoost**：極致梯度提升

## 專案結構
```
AutoML/
│   AutoML.py                 # 主程式
│   requirements.txt          # 套件清單
│   config.yaml               # 配置檔
│   
└── logs/                     # 日誌檔案夾（自動建立）
    └── automl_{date}.log
```

## 資料庫結構需求
### MongoDB 集合結構
**輸入資料格式**（實際營收資料）
```json
{
  "company": "公司名稱",
  "year_quarter": "2024_Q3",
  "value": 1234.56,
  "data_type": "actual"
}
```

**輸出資料格式**（預測結果）
```json
{
  "company": "公司名稱", 
  "year_quarter": "2025_Q1",
  "value": 1456.78,
  "data_type": "forecast",
  "created_at": "2025-07-16T10:30:00Z"
}
``` 

## 環境設定
### 步驟 1: 安裝 Python 環境
```bash
# 確保使用 Python 3.8 或以上版本
python --version

# 建議使用虛擬環境
python -m venv automl_env
# 啟動虛擬環境
# Windows
automl_env\Scripts\activate
# Linux/Mac
source automl_env/bin/activate
```

### 步驟 2: 安裝依賴套件
```bash
# 切換到 AutoML 目錄
cd AutoML
# 安裝所有必要依賴套件
pip install -r requirements.txt
```

主要依賴：
- `pandas` 
- `numpy`   
- `scikit-learn` 
- `xgboost` 
- `pymongo` 
- `PyYAML` 

### 步驟 3: 設定 MongoDB 連線
編輯 `config.yaml`：
```yaml
mongodb:
  connection_string: "mongodb+srv://<username>:<password>@cluster0.rlfhtdy.mongodb.net/" # MongoDB連線字串
  database_name: "資料庫名稱"
  collection_name: "集合名稱"
```

### 步驟 4: 準備資料
確保 MongoDB 中有足夠的歷史資料：
- 每家公司至少需要 8 個季度的資料
- 建議每家公司有 12-20 個季度的資料以獲得更好的預測效果

## 操作教學
### 執行程式
```bash
python AutoML.py
```
執行日誌記錄於 `logs/automl_YYYYMMDD.log` 檔中

### 自訂預測參數
修改 `config.yaml` 中的參數：
```yaml
model:
  future_quarters: 2    # 短期預測，提高準確性
  # 或
  future_quarters: 8    # 長期規劃，降低準確性
  
# 資料量少時使用較少特徵
features:
  lag_periods: [1, 2]
  rolling_windows: [2]

# 資料量多時可增加特徵
features:
  lag_periods: [1, 2, 3, 4, 5, 6]
  rolling_windows: [2, 4, 8, 12]
```

### 測試 MongoDB 連線
```python
from pymongo import MongoClient
import yaml

# 載入配置
with open('config.yaml', 'r') as f:
    config = yaml.safe_load(f)

# 測試連線
client = MongoClient(config['mongodb']['connection_string'])
client.admin.command('ping')
print('MongoDB 連線測試成功')
```

## 研究成果結案說明
### 專案概述
本模組採用時間序列分析方法，整合多種機器學習演算法，實現自動載入資料、特徵工程、模型訓練到預測結果存儲的全自動化流程。

### 核心技術成果
1. **多模型訓練與自動選擇最佳表現模型做預測**
2. **預測營收與自動存儲**

## 研究成果統計
### 產出成果
1. **支援多種演算法**：整合 7 種機器學習演算法
2. **自動選擇最佳表現模型**
3. **預測彈性**：支援 1-8 個季度的靈活預測週期設定

***
## 注意事項
1. **資料格式**：year_quarter 必須使用 `YYYY_QX` 格式
2. **資料完整性**：避免歷史資料中有缺失的季度
3. **資料最少需求**：每家公司 `8` 個季度歷史資料
4. **建議資料量**：每家公司 `12-20` 個季度可提升預測效果

## 相關技術資源
- scikit learn: https://scikit-learn.org/stable/user_guide.html
- XGBoost: https://xgboost.readthedocs.io/en/latest/python/python_api.html#xgboost.XGBRFRegressor
