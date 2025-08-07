import pandas as pd
import numpy as np
import logging
import yaml
import os
from datetime import datetime
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.linear_model import LinearRegression, Ridge, Lasso
from sklearn.svm import SVR
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import TimeSeriesSplit, cross_val_score
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from xgboost import XGBRegressor
import warnings
from pymongo import MongoClient
import gc  
import multiprocessing  

warnings.filterwarnings('ignore')

# 設定日誌系統
def setup_logging(config):
    """設定日誌系統"""
    log_dir = config['logging']['log_dir']
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    log_filename = f"{log_dir}/automl_{datetime.now().strftime('%Y%m%d')}.log"
    
    logging.basicConfig(
        level=getattr(logging, config['logging']['level']),
        format=config['logging']['log_format'],
        handlers=[
            logging.FileHandler(log_filename, encoding=config['logging']['encoding']),
            logging.StreamHandler()
        ] if config['logging']['console_output'] else [
            logging.FileHandler(log_filename, encoding=config['logging']['encoding'])
        ]
    )
    return logging.getLogger(__name__)

# 載入配置檔
def load_config(config_path="config.yaml"):
    """載入配置檔案"""
    try:
        with open(config_path, 'r', encoding='utf-8') as file:
            config = yaml.safe_load(file)
        return config
    except FileNotFoundError:
        print(f"找不到配置檔案: {config_path}")
        raise
    except yaml.YAMLError as e:
        print(f"配置檔案格式錯誤: {e}")
        raise

# MongoDB連接設定
def connect_to_mongodb(connection_string, database_name, collection_name):
    """連接到MongoDB"""
    try:
        client = MongoClient(connection_string)
        # 測試連接
        client.admin.command('ping')
        db = client[database_name]
        collection = db[collection_name]
        logger.info(f"成功連接到MongoDB: {database_name}.{collection_name}")
        return collection
    except Exception as e:
        logger.error(f"MongoDB連接失敗: {str(e)}")
        raise

# 從MongoDB載入和準備資料
def load_and_prepare_data_from_mongo(collection):
    """從MongoDB載入實際資料(data_type='actual')"""
    try:
        # 查詢所有實際資料
        query = {"data_type": "actual"}
        cursor = collection.find(query)
        
        # 轉換為DataFrame
        data_list = []
        for doc in cursor:
            data_list.append({
                'company': doc['company'],
                'year_quarter': doc['year_quarter'],  
                'value': doc['value'],  
                'data_type': doc['data_type']
            })
        
        df = pd.DataFrame(data_list)
        
        if df.empty:
            raise ValueError("沒有找到任何實際資料(data_type='actual')")
        
        # 解析期間格式 (例如: "2024_Q3" -> year=2024, quarter=3)
        df[['year', 'quarter']] = df['year_quarter'].str.extract(r'(\d{4})_Q(\d)')
        df['year'] = df['year'].astype(int)
        df['quarter'] = df['quarter'].astype(int)
        
        # 創建時間序號 (從1開始)
        df['time_index'] = (df['year'] - df['year'].min()) * 4 + df['quarter']
        
        # 重新命名欄位以保持一致性
        df = df.rename(columns={
            'company': '公司名稱',
            'value': '營收',  
            'quarter': '季數值',
            'time_index': '時間序號'
        })
        
        logger.info(f"成功載入 {len(df)} 筆資料，包含 {df['公司名稱'].nunique()} 家公司")
        logger.info(f"資料時間範圍: {df['year'].min()}-{df['year'].max()}")
        logger.info(f"公司列表: {', '.join(df['公司名稱'].unique())}")
        
        return df
        
    except Exception as e:
        logger.error(f"資料載入失敗: {str(e)}")
        raise

# 特徵工程（針對單一公司）
def create_features_for_company(company_data, config):
    """為單一公司建立滯後特徵"""
    try:
        company_data = company_data.sort_values('時間序號').copy()
        
        lag_periods = config['features']['lag_periods']
        rolling_windows = config['features']['rolling_windows']
        include_seasonality = config['features']['include_seasonality']
        
        # 檢查資料量是否足夠
        min_data_points = max(lag_periods) + max(rolling_windows)
        if len(company_data) < min_data_points:
            raise ValueError(f"資料量不足 ({len(company_data)} < {min_data_points})")
        
        # 創建滯後特徵
        for lag in lag_periods:
            company_data[f'lag_{lag}'] = company_data['營收'].shift(lag)
        
        # 創建移動平均特徵
        for window in rolling_windows:
            company_data[f'rolling_mean_{window}'] = company_data['營收'].rolling(window=window).mean()
        
        # 添加季節性指標
        if include_seasonality:
            company_data['季節性_Q1'] = (company_data['季數值'] == 1).astype(int)
            company_data['季節性_Q2'] = (company_data['季數值'] == 2).astype(int)
            company_data['季節性_Q3'] = (company_data['季數值'] == 3).astype(int)
            company_data['季節性_Q4'] = (company_data['季數值'] == 4).astype(int)
        
        # 丟棄有缺失值的行
        company_data = company_data.dropna()
        
        return company_data
        
    except Exception as e:
        raise Exception(f"特徵工程失敗: {str(e)}")

# 模型訓練函數 
def safe_model_training(model, X, y, cv, model_name):
    """安全的模型訓練函數"""
    try:
        # 針對XGBoost進行特殊處理
        if 'XGB' in model_name or 'xgb' in str(type(model)).lower():
            model.set_params(n_jobs=1, tree_method='hist')
            
        # 設定n_jobs=1避免多執行緒問題
        cv_scores = cross_val_score(model, X, y, cv=cv, scoring='neg_mean_squared_error', n_jobs=1)
        mean_score = -cv_scores.mean()
        std_score = cv_scores.std()
        
        # 強制垃圾回收
        gc.collect()
        
        return mean_score, std_score, True
        
    except Exception as e:
        gc.collect()
        return float('inf'), 0, False

# 為單一公司訓練最佳模型
def train_best_model_for_company(company_name, company_data_with_features, config):
    """為單一公司訓練最佳模型"""
    try:
        # 準備特徵列表
        lag_features = [f'lag_{lag}' for lag in config['features']['lag_periods']]
        rolling_features = [f'rolling_mean_{window}' for window in config['features']['rolling_windows']]
        
        feature_columns = lag_features + rolling_features
        if config['features']['include_seasonality']:
            feature_columns += ['季節性_Q1', '季節性_Q2', '季節性_Q3', '季節性_Q4']
        
        # 準備訓練集
        X = company_data_with_features[feature_columns]
        y = company_data_with_features['營收']
        
        if len(X) < 5:  # 資料量太少無法進行交叉驗證
            logger.warning(f"{company_name}: 資料量太少 ({len(X)} < 5)，使用簡單線性回歸")
            model = LinearRegression()
            scaler = StandardScaler()
            X_scaled = scaler.fit_transform(X)
            model.fit(X_scaled, y)
            
            return {
                'model': model,
                'scaler': scaler,
                'model_name': 'LinearRegression',
                'mse': None,
                'feature_columns': feature_columns
            }
        
        logger.info(f"{company_name}: 使用特徵 {feature_columns}")
        logger.info(f"{company_name}: 訓練資料形狀 X={X.shape}, y={y.shape}")
        
        # 標準化特徵
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        X_scaled = np.ascontiguousarray(X_scaled)
        y_values = np.ascontiguousarray(y.values)
        
        # 定義多個模型
        model_config = config['model']
        models = {
            'RandomForest': RandomForestRegressor(
                n_estimators=min(model_config['rf_n_estimators'], 50),  # 減少樹數量
                random_state=model_config['random_state'],
                n_jobs=1
            ),
            'GradientBoosting': GradientBoostingRegressor(
                n_estimators=min(model_config['gb_n_estimators'], 50),  # 減少樹數量
                random_state=model_config['random_state']
            ),
            'LinearRegression': LinearRegression(),
            'Ridge': Ridge(alpha=model_config['ridge_alpha']),
            'Lasso': Lasso(alpha=model_config['lasso_alpha'], max_iter=2000),
        }
        
        # 如果資料量足夠，加入更複雜的模型
        if len(X) >= 10:
            models['SVR'] = SVR(
                kernel=model_config['svr_kernel'],
                C=model_config['svr_C']
            )
            models['XGBoost'] = XGBRegressor(
                n_estimators=min(model_config['xgb_n_estimators'], 50),
                random_state=model_config['random_state'],
                n_jobs=1,
                tree_method='hist',
                verbosity=0
            )
        
        # 時間序列交叉驗證（調整splits數量）
        n_splits = min(model_config['cv_splits'], len(X) // 3)
        if n_splits < 2:
            n_splits = 2
        tscv = TimeSeriesSplit(n_splits=n_splits)
        
        # 評估每個模型
        model_scores = {}
        logger.info(f"{company_name}: 正在評估多個模型...")
        
        for name, model in models.items():
            mean_score, std_score, success = safe_model_training(model, X_scaled, y_values, tscv, name)
            
            if success:
                model_scores[name] = {
                    'mse': mean_score,
                    'std': std_score,
                    'model': model
                }
                logger.info(f"{company_name} - {name}: MSE = {mean_score:.2f} (±{std_score:.2f})")
            
            gc.collect()
        
        if not model_scores:
            raise ValueError(f"{company_name}: 所有模型訓練失敗")
        
        # 選擇最佳模型
        best_model_name = min(model_scores.keys(), key=lambda k: model_scores[k]['mse'])
        best_model = model_scores[best_model_name]['model']
        best_mse = model_scores[best_model_name]['mse']
        
        logger.info(f"{company_name}: 最佳模型 = {best_model_name}, MSE = {best_mse:.2f}")
        
        # 用全部數據重新訓練最佳模型
        best_model.fit(X_scaled, y_values)
        
        # 計算訓練集表現
        y_pred = best_model.predict(X_scaled)
        mse = mean_squared_error(y_values, y_pred)
        mae = mean_absolute_error(y_values, y_pred)
        r2 = r2_score(y_values, y_pred)
        
        logger.info(f"{company_name}: 訓練集表現 - MSE: {mse:.2f}, MAE: {mae:.2f}, R²: {r2:.4f}")
        
        gc.collect()
        
        return {
            'model': best_model,
            'scaler': scaler,
            'model_name': best_model_name,
            'mse': best_mse,
            'feature_columns': feature_columns,
            'training_metrics': {
                'mse': mse,
                'mae': mae,
                'r2': r2
            }
        }
        
    except Exception as e:
        logger.error(f"{company_name}: 模型訓練失敗 - {str(e)}")
        gc.collect()
        raise

# 為所有公司訓練獨立模型
def train_models_for_all_companies(df, config):
    """為每家公司訓練獨立模型"""
    try:
        companies = df['公司名稱'].unique()
        company_models = {}
        training_summary = {}
        
        logger.info(f"開始為 {len(companies)} 家公司訓練獨立模型...")
        logger.info("=" * 80)
        
        for company in companies:
            logger.info(f"正在處理公司: {company}")
            
            try:
                # 獲取該公司的資料
                company_data = df[df['公司名稱'] == company].copy()
                
                # 特徵工程
                company_data_with_features = create_features_for_company(company_data, config)
                
                # 訓練模型
                model_result = train_best_model_for_company(company, company_data_with_features, config)
                
                # 儲存結果
                company_models[company] = model_result
                training_summary[company] = {
                    'model_name': model_result['model_name'],
                    'cv_mse': model_result['mse'],
                    'training_metrics': model_result['training_metrics'],
                    'data_points': len(company_data_with_features)
                }
                
                logger.info(f"{company}: 完成 ✓")
                
            except Exception as e:
                logger.error(f"{company}: 訓練失敗 - {str(e)}")
                training_summary[company] = {
                    'model_name': 'FAILED',
                    'error': str(e)
                }
            
            logger.info("-" * 40)
        
        # 輸出訓練摘要
        logger.info("=" * 80)
        logger.info("模型訓練摘要:")
        successful_companies = 0
        
        for company, summary in training_summary.items():
            if summary['model_name'] != 'FAILED':
                successful_companies += 1
                cv_mse_str = f"{summary['cv_mse']:.2f}" if summary['cv_mse'] is not None else 'N/A'
                logger.info(f"{company:<15}: {summary['model_name']:<18} | "
                          f"資料點: {summary['data_points']:<3} | "
                          f"CV MSE: {cv_mse_str}")
            else:
                logger.error(f"{company:<15}: 訓練失敗 - {summary.get('error', '未知錯誤')}")
        
        logger.info(f"成功訓練: {successful_companies}/{len(companies)} 家公司")
        logger.info("=" * 80)
        
        if successful_companies == 0:
            raise ValueError("沒有任何公司成功訓練模型")
        
        return company_models, training_summary
        
    except Exception as e:
        logger.error(f"批量模型訓練失敗: {str(e)}")
        raise

# 使用獨立模型預測未來季度
def predict_future_quarters_with_individual_models(df, company_models, config):
    """使用每家公司的獨立模型預測未來季度"""
    try:
        future_predictions = []
        num_future_quarters = config['model']['future_quarters']
        
        for company, model_info in company_models.items():
            logger.info(f"使用 {model_info['model_name']} 預測 {company} 的未來 {num_future_quarters} 個季度")
            
            company_data = df[df['公司名稱'] == company].sort_values('時間序號')
            last_time_idx = company_data['時間序號'].max()
            
            # 找出最後一個季度
            last_quarter_data = company_data[company_data['時間序號'] == last_time_idx].iloc[0]
            base_year = last_quarter_data['year']
            base_quarter = last_quarter_data['季數值']
            
            model = model_info['model']
            scaler = model_info['scaler']
            feature_columns = model_info['feature_columns']
            
            # 為該公司創建完整的特徵資料
            company_data_with_features = create_features_for_company(company_data, config)
            
            # 預測未來季度
            company_predictions = []
            
            for i in range(1, num_future_quarters + 1):
                # 計算下一個季度的年份和季數
                total_quarters = base_quarter + i
                next_year = base_year + (total_quarters - 1) // 4
                next_quarter = ((total_quarters - 1) % 4) + 1
                
                # 準備特徵
                feature_dict = {}
                
                # 滯後特徵
                lag_periods = config['features']['lag_periods']
                for lag in lag_periods:
                    if i <= lag:
                        # 使用歷史資料
                        hist_idx = len(company_data) - lag + i - 1
                        if hist_idx >= 0:
                            feature_dict[f'lag_{lag}'] = company_data['營收'].iloc[hist_idx]
                        else:
                            feature_dict[f'lag_{lag}'] = company_data['營收'].mean()
                    else:
                        # 使用預測值
                        pred_idx = i - lag - 1
                        if pred_idx < len(company_predictions):
                            feature_dict[f'lag_{lag}'] = company_predictions[pred_idx]['value']
                        else:
                            feature_dict[f'lag_{lag}'] = company_data['營收'].iloc[-1]
                
                # 移動平均特徵
                rolling_windows = config['features']['rolling_windows']
                for window in rolling_windows:
                    values = []
                    for j in range(1, window + 1):
                        if i <= j:
                            hist_idx = len(company_data) - j + i - 1
                            if hist_idx >= 0:
                                values.append(company_data['營收'].iloc[hist_idx])
                        else:
                            pred_idx = i - j - 1
                            if pred_idx < len(company_predictions):
                                values.append(company_predictions[pred_idx]['value'])
                    
                    if values:
                        feature_dict[f'rolling_mean_{window}'] = np.mean(values)
                    else:
                        feature_dict[f'rolling_mean_{window}'] = company_data['營收'].mean()
                
                # 季節性指標
                if config['features']['include_seasonality']:
                    feature_dict['季節性_Q1'] = 1 if next_quarter == 1 else 0
                    feature_dict['季節性_Q2'] = 1 if next_quarter == 2 else 0
                    feature_dict['季節性_Q3'] = 1 if next_quarter == 3 else 0
                    feature_dict['季節性_Q4'] = 1 if next_quarter == 4 else 0
                
                # 構建特徵矩陣
                X_pred = np.array([[feature_dict[col] for col in feature_columns]])
                X_pred = np.ascontiguousarray(X_pred)
                
                # 標準化特徵
                X_pred_scaled = scaler.transform(X_pred)
                
                # 預測
                pred_value = model.predict(X_pred_scaled)[0]
                
                # 準備MongoDB文檔格式
                mongo_doc = {
                    "company": company,
                    "year_quarter": f"{next_year}_Q{next_quarter}",
                    "value": float(pred_value),
                    "data_type": "forecast",
                    "created_at": datetime.now()
                }
                
                company_predictions.append(mongo_doc)
                future_predictions.append(mongo_doc)
                logger.info(f"  {next_year}_Q{next_quarter}: {pred_value:.2f}")
        
        logger.info(f"完成所有預測，總計 {len(future_predictions)} 筆")
        
        # 進行垃圾回收
        gc.collect()
        
        return future_predictions
        
    except Exception as e:
        logger.error(f"預測失敗: {str(e)}")
        gc.collect()
        raise

# 將預測結果寫入MongoDB
def save_predictions_to_mongo(collection, predictions):
    """將預測結果保存到MongoDB"""
    try:
        # 先刪除現有的預測資料
        delete_result = collection.delete_many({"data_type": "forecast"})
        logger.info(f"刪除了 {delete_result.deleted_count} 筆舊的預測資料")
        
        # 插入新的預測資料
        if predictions:
            insert_result = collection.insert_many(predictions)
            logger.info(f"成功插入 {len(insert_result.inserted_ids)} 筆預測資料")
            return insert_result.inserted_ids
        else:
            logger.warning("沒有預測資料需要插入")
            return []
            
    except Exception as e:
        logger.error(f"保存預測結果失敗: {str(e)}")
        raise

# 驗證預測結果
def validate_predictions(collection):
    """驗證預測結果"""
    try:
        # 查詢預測資料
        forecast_cursor = collection.find({"data_type": "forecast"})
        forecast_df = pd.DataFrame(list(forecast_cursor))
        
        if not forecast_df.empty:
            logger.info("\n預測資料摘要:")
            logger.info(f"預測的公司數量: {forecast_df['company'].nunique()}")
            logger.info(f"預測的期間範圍: {forecast_df['year_quarter'].min()} 到 {forecast_df['year_quarter'].max()}")
            logger.info(f"預測營收範圍: {forecast_df['value'].min():.2f} 到 {forecast_df['value'].max():.2f}")
            
            # 按公司顯示預測結果
            logger.info("\n各公司預測結果:")
            for company in forecast_df['company'].unique():
                company_forecasts = forecast_df[forecast_df['company'] == company]
                logger.info(f"\n{company}:")
                for _, row in company_forecasts.iterrows():
                    logger.info(f"  {row['year_quarter']}: {row['value']:.2f}")
        else:
            logger.warning("沒有找到預測資料")
            
    except Exception as e:
        logger.error(f"驗證預測結果失敗: {str(e)}")

# 主程式
def main(config_path="config.yaml"):
    """主要執行函數"""
    try:
        # 設定multiprocessing為spawn模式 (Windows相容)
        if __name__ == "__main__":
            multiprocessing.set_start_method('spawn', force=True)
        
        # 載入配置
        config = load_config(config_path)
        
        # 設定日誌
        global logger
        logger = setup_logging(config)
        logger.info("=== AutoML 營收預測 (獨立公司模型版本) ===")
        logger.info("配置檔載入成功")
        
        # 連接MongoDB
        logger.info("連接到MongoDB...")
        collection = connect_to_mongodb(
            config['mongodb']['connection_string'],
            config['mongodb']['database_name'],
            config['mongodb']['collection_name']
        )
        
        # 載入和準備資料
        logger.info("載入實際資料...")
        df = load_and_prepare_data_from_mongo(collection)
        
        # 為每家公司訓練獨立模型
        logger.info("為每家公司訓練獨立模型...")
        company_models, training_summary = train_models_for_all_companies(df, config)
        
        # 使用獨立模型預測未來季度
        logger.info(f"使用獨立模型預測未來 {config['model']['future_quarters']} 個季度...")
        predictions = predict_future_quarters_with_individual_models(df, company_models, config)
        
        # 保存預測結果到MongoDB
        logger.info("保存預測結果到MongoDB...")
        inserted_ids = save_predictions_to_mongo(collection, predictions)
        
        # 驗證結果
        validate_predictions(collection)
        
        logger.info("預測流程完成")
        logger.info("=== AutoML 營收預測結束 ===")
        
        # 最終垃圾回收
        gc.collect()
        
        return predictions, company_models, training_summary
        
    except Exception as e:
        logger.error(f"程式執行失敗: {str(e)}")
        gc.collect()
        raise

if __name__ == "__main__":
    try:
        # 執行預測
        predictions, company_models, training_summary = main()
        
        print(f"\n=== 執行結果摘要 ===")
        print(f"總共產生了 {len(predictions)} 筆預測資料")
        
        # 輸出每家公司使用的模型
        print(f"\n=== 各公司使用的模型 ===")
        for company, summary in training_summary.items():
            if summary['model_name'] != 'FAILED':
                print(f"{company:<15}: {summary['model_name']}")
            else:
                print(f"{company:<15}: 訓練失敗")
        
        # 輸出預測摘要
        pred_df = pd.DataFrame(predictions)
        if not pred_df.empty:
            print(f"\n=== 預測結果摘要 ===")
            print(f"預測公司數: {pred_df['company'].nunique()}")
            print(f"預測期間: {pred_df['year_quarter'].min()} ~ {pred_df['year_quarter'].max()}")
            print(f"預測營收範圍: {pred_df['value'].min():.2f} ~ {pred_df['value'].max():.2f}")
        
    except Exception as e:
        print(f"執行失敗: {str(e)}")
        exit(1)
