"""MongoDB連接工具"""
from pymongo import MongoClient
import logging
from config.settings import Settings

def create_mongodb_client(settings: Settings):
    """創建MongoDB客戶端
    
    Args:
        settings: 設定物件
        
    Returns:
        MongoClient: MongoDB客戶端
    """
    try:
        uri = settings.get('mongodb.uri')
        if not uri:
            raise ValueError("MongoDB URI未設定")
        
        client = MongoClient(uri)
        
        # 測試連接
        client.admin.command('ping')
        logging.info("MongoDB連接成功")
        
        return client
    except Exception as e:
        logging.error(f"MongoDB連接失敗: {e}")
        raise

def get_database_and_collections(client, settings: Settings):
    """獲取資料庫和集合
    
    Args:
        client: MongoDB客戶端
        settings: 設定物件
        
    Returns:
        tuple: (database, embedding_collection, revenue_collection)
    """
    database_name = settings.get('mongodb.database_name')
    embedding_collection_name = settings.get('mongodb.collections.embeddings')
    revenue_collection_name = settings.get('mongodb.collections.revenue')
    
    if not all([database_name, embedding_collection_name, revenue_collection_name]):
        raise ValueError("MongoDB資料庫或集合名稱未正確設定")
    
    database = client[database_name]
    embedding_collection = database[embedding_collection_name]
    revenue_collection = database[revenue_collection_name]
    
    return database, embedding_collection, revenue_collection

def create_indexes(revenue_collection):
    """創建必要的索引
    
    Args:
        revenue_collection: 營收集合
    """
    try:
        revenue_collection.create_index([
            ("company", 1),
            ("year_quarter", 1)
        ], name="company_quarter_index")
        
        logging.info("成功創建索引")
    except Exception as e:
        logging.warning(f"創建索引時發生錯誤: {e}")