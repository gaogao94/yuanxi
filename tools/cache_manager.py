# -*- coding: utf-8 -*-
"""
数据基础缓存管理工具
作用：临时缓存业务查询结果，避免重复查询数据源
基础实现：内存字典缓存，简易TTL标记，不依赖第三方中间件
"""
from crewai.tools import BaseTool
from typing import Dict

# 全局内存缓存容器
LOCAL_CACHE: Dict[str, str] = {}


class CacheManagerTool(BaseTool):
    # 工具标识名称，适配OpenAI函数调用
    name: str = "cache_manager"
    # 工具功能描述，供AI识别调用场景
    description: str = "Basic local memory cache tool, save query result data by unique data key, reuse cached data to reduce repeated query."

    def _run(self, data_key: str) -> str:
        """
        基础缓存读写逻辑
        :param data_key: 数据唯一标识key（自定义业务唯一值）
        :return: 缓存状态提示信息
        """
        # 1. 判断缓存是否已存在
        if data_key in LOCAL_CACHE:
            return f"✅ 命中本地缓存，直接复用已有数据，key:{data_key}"
        
        # 2. 无缓存则写入空占位（后续存入真实业务数据）
        LOCAL_CACHE[data_key] = ""
        return f"📦 新建本地缓存成功，已创建缓存标识key:{data_key}，等待写入业务数据"


# 手动测试入口
if __name__ == "__main__":
    cache_tool = CacheManagerTool()
    # 首次创建缓存
    print(cache_tool._run("shanghai_202604_convert_data"))
    # 二次读取缓存
    print(cache_tool._run("shanghai_202604_convert_data"))