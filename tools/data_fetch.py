# tools/data_fetch.py
"""
数据库取数工具 - 真实连接版本
- 基于 SQLAlchemy + PyMySQL
- 自动连接池（带连接验证）
- 只允许 SELECT 查询
- 对患者姓名、电话等字段自动脱敏
- 支持连接重试和自动重连
"""

import os
import time
from typing import List, Dict
from sqlalchemy import create_engine, text, pool
from sqlalchemy.exc import OperationalError
from dotenv import load_dotenv
from crewai.tools import BaseTool

load_dotenv()

# 敏感字段列表（需要脱敏的列名，可自定义）
SENSITIVE_COLUMNS = {"patient_name", "patientName","姓名", "phone", "mobile", "id_card", "email"}

# 全局数据库引擎（惰性初始化）- 支持多数据库
_engines = {}

def _get_engine(db: str = "default"):
    """创建或返回指定数据库的连接引擎（连接池）
    
    Args:
        db: 数据库标识，支持 "default" 和 "dwd"（数仓）
    """
    global _engines
    if db in _engines and _engines[db] is not None:
        return _engines[db]

    # 根据 db 参数选择不同的数据库配置
    if db == "dwd" or db == "数仓":
        # 数仓数据库配置
        host = os.getenv("DWD_DB_HOST", "139.196.228.171")
        port = os.getenv("DWD_DB_PORT", "9030")
        user = os.getenv("DWD_DB_USER", "root")
        password = os.getenv("DWD_DB_PASSWORD", "123456")
        database = os.getenv("DWD_DB_NAME", "")
        db_name = "数仓"
    else:
        # 默认业务数据库配置
        host = os.getenv("DB_HOST")
        port = os.getenv("DB_PORT", "3306")
        user = os.getenv("DB_USER")
        password = os.getenv("DB_PASSWORD")
        database = os.getenv("DB_NAME")
        db_name = "业务库"

    if not all([host, user, password]):
        raise ValueError(f"{db_name}连接信息不完整，请检查 .env 文件")

    # 构建连接 URL（数仓可能不需要指定 database）
    if database:
        url = f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}?charset=utf8mb4"
    else:
        url = f"mysql+pymysql://{user}:{password}@{host}:{port}/?charset=utf8mb4"

    _engines[db] = create_engine(
        url,
        poolclass=pool.QueuePool,
        pool_size=5,
        max_overflow=10,
        pool_recycle=3600,   # 1小时回收连接
        echo=False           # 生产环境保持 False，调试时可设为 True 查看 SQL
    )
    return _engines[db]

def _mask_value(value: str) -> str:
    """对字符串进行脱敏：保留首尾，中间用 * 替代"""
    if not isinstance(value, str) or len(value) <= 2:
        return value
    return value[0] + "*" * (len(value) - 2) + value[-1]

def _mask_row(row: Dict, columns: List[str]) -> Dict:
    """对一行数据中的敏感字段进行脱敏"""
    for col in columns:
        if col.lower() in SENSITIVE_COLUMNS and col in row and row[col] is not None:
            row[col] = _mask_value(str(row[col]))
    return row

def _reconnect_engine(db: str):
    """重新创建指定数据库的连接引擎"""
    global _engines
    if db in _engines:
        try:
            _engines[db].dispose()
        except:
            pass
        _engines[db] = None
    return _get_engine(db)

def execute_query(sql: str, db: str = "default", max_retries: int = 3) -> List[Dict]:
    """
    执行 SELECT 查询，返回字典列表，自动脱敏敏感字段。
    非 SELECT 语句会被拦截。支持连接重试机制。
    
    Args:
        sql: SQL 查询语句
        db: 数据库标识，"default" 表示业务库，"dwd" 表示数仓
        max_retries: 最大重试次数，默认 3 次
    """
    # 1. 安全拦截：只允许只读查询
    clean_sql = sql.strip()
    if not clean_sql.upper().startswith("SELECT"):
        raise ValueError("只允许执行 SELECT 查询，当前语句已被拒绝。")
    # 可选：更严格的黑名单
    forbidden = ["drop", "delete", "insert", "update", "alter", "truncate", "create"]
    if any(word in clean_sql.lower() for word in forbidden):
        raise ValueError(f"SQL 包含禁止的关键字，已被拦截。")

    engine = _get_engine(db)
    last_exception = None
    
    for attempt in range(max_retries):
        try:
            with engine.connect() as conn:
                # 验证连接有效性
                conn.execute(text("SELECT 1"))
                
                result = conn.execute(text(clean_sql))
                # 获取列名
                columns = list(result.keys()) if hasattr(result, 'keys') else result.keys()
                rows = []
                for row in result:
                    row_dict = dict(zip(columns, row))
                    # 脱敏处理
                    row_dict = _mask_row(row_dict, columns)
                    rows.append(row_dict)
                return rows
        except OperationalError as e:
            last_exception = e
            if "Lost connection" in str(e) or "2013" in str(e):
                # 连接丢失，尝试重新连接
                if attempt < max_retries - 1:
                    print(f"⚠️  数据库连接丢失，正在尝试重新连接（第 {attempt + 1} 次重试）...")
                    engine = _reconnect_engine(db)
                    time.sleep(1)  # 等待 1 秒后重试
                    continue
            raise Exception(f"数据库查询失败: {str(e)}") from e
        except Exception as e:
            last_exception = e
            raise Exception(f"数据库查询失败: {str(e)}") from e
    
    if last_exception:
        raise Exception(f"数据库查询失败（已重试 {max_retries} 次）: {str(last_exception)}")

class DataFetchTool(BaseTool):
    name: str = "data_fetch"
    description: str = "从业务宽表或数仓中执行安全的只读查询，返回行数和字段名，敏感字段自动脱敏。"

    def _run(self, sql: str, db: str = "default") -> str:
        """
        执行数据库查询
        
        Args:
            sql: SQL 查询语句（仅支持 SELECT）
            db: 数据库标识，可选值："default"（业务库）、"dwd"（数仓），默认为 "default"
        """
        try:
            rows = execute_query(sql, db)
            db_label = "数仓" if db == "dwd" else "业务库"
            if not rows:
                return f"[{db_label}] 查询成功，但未返回数据。"
            fields = list(rows[0].keys())
            return f"[{db_label}] 查询成功。返回 {len(rows)} 行，字段：{fields}，首行示例：{rows[0]}"
        except Exception as e:
            return f"数据库查询失败：{str(e)}"


# 可选：手动关闭连接池（通常不需要，进程结束会释放）
def close_pool(db: str = None):
    global _engines
    if db:
        if db in _engines and _engines[db]:
            _engines[db].dispose()
            _engines[db] = None
    else:
        # 关闭所有连接池
        for key in _engines:
            if _engines[key]:
                _engines[key].dispose()
        _engines = {}