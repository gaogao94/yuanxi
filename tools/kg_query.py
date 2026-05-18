import os
from typing import Type, Optional
from pydantic import BaseModel, Field
from crewai.tools import BaseTool

# nebula3 的导入可能失败（如果你还没装），这里做一下保护
try:
    from nebula3.gclient.net import ConnectionPool
    from nebula3.Config import Config
    NEBULA_AVAILABLE = True
except ImportError:
    NEBULA_AVAILABLE = False

class NebulaGraphQueryInput(BaseModel):
    query: str = Field(..., description="需要执行的 nGQL 查询语句")

class NebulaGraphQueryTool(BaseTool):
    name: str = "知识图谱查询"
    description: str = "使用 nGQL 查询 NebulaGraph。如果数据库不可用，会返回模拟数据。"
    args_schema: Type[BaseModel] = NebulaGraphQueryInput

    # 类变量，用来保存单例连接池
    _connection_pool: Optional[ConnectionPool] = None

    def _get_pool(self):
        """惰性初始化连接池，只在真正查询时才创建"""
        if self._connection_pool is not None:
            return self._connection_pool

        if not NEBULA_AVAILABLE:
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
                        return "查询成功，但无数据。"
                    return f"查询成功，{len(rows)} 行：{rows}"
                else:
                    return f"查询失败：{result.error_msg() if result else '未知错误'}"
        except Exception as e:
            # 如果连接失败或任何异常，返回模拟信息，保证流程不中断
            return f"【模拟图谱查询】当前数据库不可用（{str(e)}），返回模拟结果：已锁定门店SH001、SH002与患者、预约关系。"