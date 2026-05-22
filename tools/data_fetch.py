# tools/data_fetch.py
"""
数据库取数工具 - 真实连接版本
- 基于 SQLAlchemy + PyMySQL
- 自动连接池
- 只允许 SELECT 查询
- 对患者姓名、电话等字段自动脱敏
"""

import os
from typing import List, Dict
from sqlalchemy import create_engine, text, pool
from dotenv import load_dotenv
from crewai.tools import BaseTool

load_dotenv()

# 敏感字段列表（需要脱敏的列名，可自定义）
SENSITIVE_COLUMNS = {"patient_name", "phone", "mobile", "id_card", "email"}

# 全局数据库引擎（惰性初始化）
_engine = None

def _get_engine():
    """创建或返回数据库连接引擎（连接池）"""
    global _engine
    if _engine is not None:
        return _engine

    host = os.getenv("DB_HOST")
    port = os.getenv("DB_PORT", "3306")
    user = os.getenv("DB_USER")
    password = os.getenv("DB_PASSWORD")
    database = os.getenv("DB_NAME")

    if not all([host, user, password, database]):
        raise ValueError("数据库连接信息不完整，请检查 .env 文件（DB_HOST, DB_USER, DB_PASSWORD, DB_NAME）")

    url = f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}?charset=utf8mb4"

    _engine = create_engine(
        url,
        poolclass=pool.QueuePool,
        pool_size=5,
        max_overflow=10,
        pool_recycle=3600,   # 1小时回收连接
        echo=False           # 生产环境保持 False，调试时可设为 True 查看 SQL
    )
    return _engine

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

def execute_query(sql: str) -> List[Dict]:
    """
    执行 SELECT 查询，返回字典列表，自动脱敏敏感字段。
    非 SELECT 语句会被拦截。
    """
    # 1. 安全拦截：只允许只读查询
    clean_sql = sql.strip()
    if not clean_sql.upper().startswith("SELECT"):
        raise ValueError("只允许执行 SELECT 查询，当前语句已被拒绝。")
    # 可选：更严格的黑名单
    forbidden = ["drop", "delete", "insert", "update", "alter", "truncate", "create"]
    if any(word in clean_sql.lower() for word in forbidden):
        raise ValueError(f"SQL 包含禁止的关键字，已被拦截。")

    engine = _get_engine()
    try:
        with engine.connect() as conn:
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
    except Exception as e:
        raise Exception(f"数据库查询失败: {str(e)}") from e

class DataFetchTool(BaseTool):
    name: str = "data_fetch"
    description: str = "从业务宽表中执行安全的只读查询，返回行数和字段名，敏感字段自动脱敏。"

    def _run(self, sql: str) -> str:
        try:
            rows = execute_query(sql)
            if not rows:
                return "查询成功，但未返回数据。"
            fields = list(rows[0].keys())
            return f"查询成功。返回 {len(rows)} 行，字段：{fields}，首行示例：{rows[0]}"
        except Exception as e:
            return f"数据库查询失败：{str(e)}"


# 可选：手动关闭连接池（通常不需要，进程结束会释放）
def close_pool():
    global _engine
    if _engine:
        _engine.dispose()
        _engine = None