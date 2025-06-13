import pymongo
from pymongo.server_api import ServerApi
from pymongo.database import Database
from pymongo.collection import Collection
from typing import List, Dict, Optional, Union, Any, Set
from .logger import Logger


class MongoDBClient:
    def __init__(self, uri: str):
        """
        初始化 MongoDB 客戶端連接
        
        :param uri: MongoDB 連接字串
        """
        self.logger = Logger(name="MongoDBClientLogger")
        self.logger.info("初始化 MongoDB 客戶端")
        
        try:
            self.mongo_client = pymongo.MongoClient(
                uri,
                serverSelectionTimeoutMS=120000,
                connectTimeoutMS=60000,
                socketTimeoutMS=60000,
                server_api=ServerApi('1')
            )
            # 驗證連接是否成功
            self.mongo_client.admin.command('ping')
            self.logger.info("MongoDB 連接成功建立")
        except Exception as e:
            error_msg = f"MongoDB 連接失敗: {str(e)}"
            self.logger.error(error_msg)
            raise ConnectionError(error_msg)

    def get_db(self, db_name: str) -> Database:
        """
        取得指定的資料庫
        
        :param db_name: 資料庫名稱
        :return: MongoDB 資料庫物件
        """
        self.logger.info(f"嘗試獲取資料庫: {db_name}")
        try:
            if not db_name:
                error_msg = "資料庫名稱 (db_name) 不能為空"
                self.logger.error(error_msg)
                raise ValueError(error_msg)
                
            db = self.mongo_client[db_name]
            self.logger.info(f"成功獲取資料庫: {db_name}")
            return db
        except Exception as e:
            error_msg = f"獲取資料庫 {db_name} 時發生錯誤: {str(e)}"
            self.logger.error(error_msg)
            raise RuntimeError(error_msg)
        
    def get_collection(self, db_name: str, collection_name: str) -> Collection:
        """
        取得指定的集合
        
        :param db_name: 資料庫名稱
        :param collection_name: 集合名稱
        :return: MongoDB 集合物件
        """
        self.logger.info(f"嘗試獲取集合: {db_name}.{collection_name}")
        try:
            if not db_name:
                error_msg = "資料庫名稱 (db_name) 不能為空"
                self.logger.error(error_msg)
                raise ValueError(error_msg)
                
            if not collection_name:
                error_msg = "集合名稱 (collection_name) 不能為空"
                self.logger.error(error_msg)
                raise ValueError(error_msg)
                
            collection = self.get_db(db_name)[collection_name]
            self.logger.info(f"成功獲取集合: {db_name}.{collection_name}")
            return collection
        except ValueError as e:
            # 直接傳遞ValueError
            raise
        except Exception as e:
            error_msg = f"獲取集合 {db_name}.{collection_name} 時發生錯誤: {str(e)}"
            self.logger.error(error_msg)
            raise RuntimeError(error_msg)
    
    def close(self) -> None:
        """
        關閉 MongoDB 連接
        """
        self.logger.info("關閉 MongoDB 連接")
        try:
            self.mongo_client.close()
            self.logger.info("MongoDB 連接已成功關閉")
        except Exception as e:
            error_msg = f"關閉 MongoDB 連接時發生錯誤: {str(e)}"
            self.logger.error(error_msg)
            # 關閉連接失敗一般不需要阻止程序繼續執行
            self.logger.warning("連接關閉失敗，但程序將繼續執行")

    def list_fields(self, db_name: str, collection_name: str, sample_size: int = 100) -> List[str]:
        """
        檢查指定集合中的欄位名稱（取前 N 筆做統計）
        
        :param db_name: 資料庫名稱
        :param collection_name: 集合名稱
        :param sample_size: 取樣數量
        :return: 欄位名稱列表
        """
        self.logger.info(f"列出 {db_name}.{collection_name} 中的欄位，取樣數量: {sample_size}")
        try:
            if not db_name:
                error_msg = "資料庫名稱 (db_name) 不能為空"
                self.logger.error(error_msg)
                raise ValueError(error_msg)
                
            if not collection_name:
                error_msg = "集合名稱 (collection_name) 不能為空"
                self.logger.error(error_msg)
                raise ValueError(error_msg)
                
            if sample_size <= 0:
                error_msg = "取樣數量 (sample_size) 必須大於 0"
                self.logger.error(error_msg)
                raise ValueError(error_msg)

            collection = self.get_collection(db_name, collection_name)
            fields: Set[str] = set()
            cursor = collection.find({}, limit=sample_size)
            for doc in cursor:
                fields.update(doc.keys())
                
            field_list = list(fields)
            self.logger.info(f"找到 {len(field_list)} 個欄位")
            return field_list
        except ValueError:
            # 值錯誤直接向上傳遞
            raise
        except Exception as e:
            error_msg = f"獲取欄位列表時發生錯誤: {str(e)}"
            self.logger.error(error_msg)
            raise RuntimeError(error_msg)
    
    def get_distinct(self, db_name: str, collection_name: str, field: str, 
                    filter_dict: Optional[Dict[str, Any]] = None) -> List[Any]:
        """
        取得指定欄位的不重複值（distinct），可加條件篩選。
        
        :param db_name: 資料庫名稱
        :param collection_name: 集合名稱
        :param field: 欲查詢的欄位名稱（如 "company", "quarter"）
        :param filter_dict: 可選查詢條件（如 {"quarter": "2024_Q4"}）
        :return: 唯一值列表
        """
        self.logger.info(f"獲取 {db_name}.{collection_name} 中 {field} 欄位的不重複值")
        try:
            if field is None or not field:
                error_msg = "欄位名稱 (field) 不能為空。請提供欲查詢的欄位名稱。"
                self.logger.error(error_msg)
                raise ValueError(error_msg)
                
            if not db_name:
                error_msg = "資料庫名稱 (db_name) 不能為空"
                self.logger.error(error_msg)
                raise ValueError(error_msg)
                
            if not collection_name:
                error_msg = "集合名稱 (collection_name) 不能為空"
                self.logger.error(error_msg)
                raise ValueError(error_msg)
            
            collection = self.get_collection(db_name, collection_name)
            if filter_dict is None:
                filter_dict = {}
                
            result = collection.distinct(field, filter_dict)
            self.logger.info(f"成功獲取 {len(result)} 個不重複的 {field} 值")
            return result
        except ValueError:
            # 值錯誤直接向上傳遞
            raise
        except Exception as e:
            error_msg = f"獲取不重複值時發生錯誤: {str(e)}"
            self.logger.error(error_msg)
            raise RuntimeError(error_msg)

    def get_documents(self, db_name: str, collection_name: str, 
                     filter_dict: Optional[Dict[str, Any]] = None, 
                     limit: int = 0) -> List[Dict[str, Any]]:
        """
        取得符合條件的文檔
        
        :param db_name: 資料庫名稱
        :param collection_name: 集合名稱
        :param filter_dict: 篩選條件
        :param limit: 限制筆數，0 表示不限制
        :return: 文檔列表
        """
        self.logger.info(f"從 {db_name}.{collection_name} 獲取文件，篩選條件: {filter_dict}, 限制: {limit}")
        try:
            return self.query_by_fields(db_name, collection_name, filter_dict=filter_dict, fields=None, limit=limit)
        except Exception as e:
            error_msg = f"獲取文檔時發生錯誤: {str(e)}"
            self.logger.error(error_msg)
            raise RuntimeError(error_msg)
    
    def query_by_fields(self, db_name: str, collection_name: str, 
                       filter_dict: Optional[Dict[str, Any]] = None, 
                       fields: Optional[List[str]] = None, 
                       group_by: Optional[str] = None, 
                       limit: int = 0) -> Union[List[Dict[str, Any]], Dict[str, List[Dict[str, Any]]]]:
        """
        通用查詢方法，可根據條件查詢欄位，並選擇是否群組結果。
        
        :param db_name: 資料庫名稱
        :param collection_name: 集合名稱
        :param filter_dict: 查詢條件（如 {"company": "Netmarble"}）
        :param fields: 欲取回欄位（如 ["title", "quarter", "analysis"]），None 則回傳全部
        :param group_by: 若指定欄位（如 "company"），則回傳 {group_key: [doc...]}
        :param limit: 限制筆數，預設 0 表示全部
        :return: 文檔列表或依群組分類的文檔字典
        """
        query_info = f"查詢 {db_name}.{collection_name}"
        if filter_dict:
            query_info += f", 條件: {filter_dict}"
        if fields:
            query_info += f", 欄位: {fields}"
        if group_by:
            query_info += f", 分組依據: {group_by}"
        if limit:
            query_info += f", 限制: {limit} 筆"
            
        self.logger.info(query_info)
        
        try:
            if not db_name:
                error_msg = "資料庫名稱 (db_name) 不能為空"
                self.logger.error(error_msg)
                raise ValueError(error_msg)
                
            if not collection_name:
                error_msg = "集合名稱 (collection_name) 不能為空"
                self.logger.error(error_msg)
                raise ValueError(error_msg)
                
            if limit < 0:
                error_msg = "限制筆數 (limit) 不能為負數"
                self.logger.error(error_msg)
                raise ValueError(error_msg)
                
            collection = self.get_collection(db_name, collection_name)
            
            if filter_dict is None:
                filter_dict = {}

            projection = None
            if fields:
                projection = {field: 1 for field in fields}
                projection["_id"] = 0  # 通常不需要 ObjectId 可省略

            cursor = collection.find(filter_dict, projection, limit=limit)
            results = list(cursor)
            self.logger.info(f"查詢成功，共取得 {len(results)} 筆資料")

            if group_by:
                grouped: Dict[str, List[Dict[str, Any]]] = {}
                for doc in results:
                    key = str(doc.get(group_by, "UNKNOWN"))
                    if key not in grouped:
                        grouped[key] = []
                    grouped[key].append(doc)
                self.logger.info(f"已將結果分組為 {len(grouped)} 組")
                return grouped

            return results
        except ValueError:
            # 值錯誤直接向上傳遞
            raise
        except Exception as e:
            error_msg = f"查詢執行時發生錯誤: {str(e)}"
            self.logger.error(error_msg)
            raise RuntimeError(error_msg)