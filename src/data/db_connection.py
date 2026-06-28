"""
MongoDB 数据库连接模块
用于存储策略运行数据、交易记录和资产曲线
"""
import logging
import json
import pandas as pd
from pymongo import MongoClient

logger = logging.getLogger(__name__)


class ATSDBClient:
    """
    MongoDB 数据库客户端

    数据库: HJATS
    集合命名: {策略名}_{时间戳}_data   (K线数据)
              {策略名}_{时间戳}_trade  (交易记录)
              {策略名}_{时间戳}_profit (资产曲线)
    """

    def __init__(self, dbconfig: dict = None):
        self.dbclient = None
        self.database = None
        self.db_name = 'HJATS'

        # 集合引用
        self.namelist_of_collections = None
        self.collection_data = None
        self.collection_trade = None
        self.collection_profit = None

        self._open_db(dbconfig)

    def _open_db(self, dbconfig: dict = None):
        """打开数据库连接"""
        if dbconfig is None:
            # 尝试从 .env 加载 MongoDB 凭据
            uri = 'mongodb://localhost:27017/'
            env_mongo = self._load_mongo_from_env()
            if env_mongo:
                u = env_mongo['user']
                p = env_mongo['passwd']
                h = env_mongo['host']
                pt = env_mongo['port']
                a = env_mongo.get('authSource', 'admin')
                uri = f'mongodb://{u}:{p}@{h}:{pt}/?authSource={a}'
                logger.info(f"[DB] Remote MongoDB (from .env): {h}:{pt}")
            else:
                logger.info("[DB] Local MongoDB (no .env credentials found)")
        else:
            user = dbconfig['user']
            passwd = dbconfig['passwd']
            host = dbconfig['host']
            port = dbconfig['port']
            auth_source = dbconfig.get('authSource', 'admin')
            uri = f'mongodb://{user}:{passwd}@{host}:{port}/?authSource={auth_source}'
            logger.info(f"[DB] Remote MongoDB: {host}:{port}")

        self.dbclient = MongoClient(uri)
        self.database = self.dbclient[self.db_name]
        logger.info(f"[DB] Database '{self.db_name}' connected!")

    def create_record_collections(self, base_name: str):
        """
        创建记录集合

        Args:
            base_name: 集合基础名称 (策略名_时间戳)
        """
        self.namelist_of_collections = (
            base_name,
            f"{base_name}_data",
            f"{base_name}_trade",
            f"{base_name}_profit",
        )
        self.collection_data = self.database[f"{base_name}_data"]
        self.collection_trade = self.database[f"{base_name}_trade"]
        self.collection_profit = self.database[f"{base_name}_profit"]
        logger.info(f"[DB] Collections created: {base_name}")

    def df_to_collection(self, df_data, collection_name, db_name=None):
        """
        将 DataFrame 写入 MongoDB 集合

        Args:
            df_data: 要写入的 DataFrame
            collection_name: 集合名称
            db_name: 数据库名称（默认使用 self.db_name）
        """
        if db_name is None:
            db_name = self.db_name

        def df_to_bson(df):
            """DataFrame 转为 BSON 格式"""
            dftemp = df.reset_index()
            data = json.loads(dftemp.T.to_json(date_unit='ns')).values()
            return data

        my_db = self.dbclient[db_name]
        bson_data = df_to_bson(df_data)
        my_posts = my_db[collection_name]
        result = my_posts.insert_many(bson_data)
        logger.debug(f"[DB] Inserted {len(bson_data)} records into {collection_name}")
        return result

    def collection_to_df(self, collection_name, query=None, db_name=None,
                         no_id=True):
        """
        从 MongoDB 集合查询并返回 DataFrame

        Args:
            collection_name: 集合名称
            query: 查询条件
            db_name: 数据库名称
            no_id: 是否移除 _id 字段

        Returns:
            DataFrame
        """
        if query is None:
            query = {}
        if db_name is None:
            db_name = self.db_name

        collection = self.dbclient[db_name][collection_name]
        cursor = collection.find(query)
        df = pd.DataFrame(list(cursor))
        if no_id and '_id' in df.columns:
            del df['_id']
        return df

    def list_all_collections(self):
        """列出当前数据库所有集合"""
        collections = self.database.list_collection_names()
        logger.info(f"[DB] Collections: {collections}")
        return collections

    def drop_collection(self, name: str):
        """删除指定集合"""
        collection = self.database[name]
        collection.drop()
        logger.info(f"[DB] Collection dropped: {name}")

    @staticmethod
    def _load_mongo_from_env() -> dict:
        """从 .env 文件加载 MongoDB 凭据"""
        import os
        env_path = os.path.join(os.getcwd(), '.env')
        if not os.path.exists(env_path):
            return None
        creds = {}
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line.startswith('MONGODB_USER='):
                    creds['user'] = line.split('=', 1)[1].strip().strip("'\"")
                elif line.startswith('MONGODB_PASSWD='):
                    creds['passwd'] = line.split('=', 1)[1].strip().strip("'\"")
                elif line.startswith('MONGODB_HOST='):
                    creds['host'] = line.split('=', 1)[1].strip().strip("'\"")
                elif line.startswith('MONGODB_PORT='):
                    creds['port'] = line.split('=', 1)[1].strip().strip("'\"")
                elif line.startswith('MONGODB_AUTH_SOURCE='):
                    creds['authSource'] = line.split('=', 1)[1].strip().strip("'\"")
        if creds.get('user') and creds.get('passwd') and creds.get('host'):
            return creds
        return None

    def close(self):
        """关闭数据库连接"""
        if self.dbclient:
            self.dbclient.close()
            logger.info("[DB] Connection closed")
