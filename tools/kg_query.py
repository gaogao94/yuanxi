"""
NebulaGraph 知识图谱查询工具（惰性连接 + 模拟降级）
即使未安装 nebula3-python 或无法连接图数据库，也不会影响 Agent 的初始化与运行。
"""

import os
from typing import Type, Optional, Any
from pydantic import BaseModel, Field
from crewai.tools import BaseTool

# 只在类型检查时导入 ConnectionPool，避免运行时因缺少 nebula3 而报错
# 真正的导入会放在 _get_pool 方法里延迟执行
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from nebula3.gclient.net import ConnectionPool

class NebulaGraphQueryInput(BaseModel):
    query: str = Field(..., description="需要执行的 nGQL 查询语句，例如：'SHOW TAGS'")

class NebulaGraphQueryTool(BaseTool):
    name: str = "知识图谱查询"
    description: str = (
        "使用 nGQL 语句查询 NebulaGraph 图数据库，获取实体、关系等知识图谱信息。"
        "如果数据库不可用，会自动降级为模拟结果，确保流程不中断。"
    )
    args_schema: Type[BaseModel] = NebulaGraphQueryInput

    # 使用字符串形式的类型注解，避免直接依赖 ConnectionPool
    _connection_pool: Optional[Any] = None

    def _get_pool(self):
        """惰性初始化连接池，只在真正需要查询时才创建"""
        if self._connection_pool is not None:
            return self._connection_pool

        # 尝试导入并连接
        try:
            from nebula3.gclient.net import ConnectionPool
            from nebula3.Config import Config
        except ImportError:
            raise Exception("nebula3-python 未安装，无法连接图数据库。")

        nebula_address = os.getenv('NEBULA_ADDRESS', '127.0.0.1')
        nebula_port = int(os.getenv('NEBULA_PORT', 9669))
        
        config = Config()
        config.max_connection_pool_size = 10
        
        pool = ConnectionPool()
        if not pool.init([(nebula_address, nebula_port)], config):
            raise Exception(f"无法连接到 NebulaGraph {nebula_address}:{nebula_port}")
        
        self._connection_pool = pool
        return pool

    def _run(self, query: str) -> str:
        try:
            pool = self._get_pool()
            nebula_user = os.getenv('NEBULA_USER', 'root')
            nebula_password = os.getenv('NEBULA_PASSWORD', 'nebula')
            nebula_space = os.getenv('NEBULA_SPACE', 'your_space')

            with pool.session_context(nebula_user, nebula_password) as session:
                session.execute(f'USE {nebula_space}')
                result = session.execute(query)
                if result and result.is_succeeded():
                    rows = result.rows()
                    if not rows:
                        return "查询成功，但未返回任何数据。"
                    return f"查询成功。共 {len(rows)} 行数据。结果：{rows}"
                else:
                    return f"查询失败：{result.error_msg() if result else '未知错误'}"
        except Exception as e:
            # 连接失败时返回模拟数据，保证整体流程不中断
            return (
                f"【模拟图谱查询】当前数据库不可用（{str(e)}）。"
                "返回模拟结果：已锁定门店 SH001、SH002 与患者、预约关系，分析范围限定上海门店。"
            )