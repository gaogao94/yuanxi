#!/usr/bin/env python3
"""测试 NebulaGraph 查询工具的连接情况"""

import os
import sys
from dotenv import load_dotenv

load_dotenv()

print("=" * 60)
print("NebulaGraph 连接测试")
print("=" * 60)

# 检查环境变量
graph_api_key = os.getenv("GRAPH_API_KEY", "").strip()
graph_api_base_url = os.getenv("GRAPH_API_BASE_URL", "https://graph.automed.cn")
graph_api_url = os.getenv("GRAPH_API_URL", "https://graph.automed.cn")

print(f"\n1. 环境变量检查:")
print(f"   GRAPH_API_BASE_URL: {graph_api_base_url}")
print(f"   GRAPH_API_URL: {graph_api_url}")
print(f"   GRAPH_API_KEY: {'已设置' if graph_api_key else '未设置'}")
if graph_api_key:
    print(f"   GRAPH_API_KEY (前20字符): {graph_api_key[:20]}...")

# 检查 nebula_graph_query 模块是否可以导入
print(f"\n2. 模块导入检查:")
try:
    from tools.nebula_graph_query import NebulaGraphQueryTool
    print("   ✓ nebula_graph_query 模块导入成功")
except Exception as e:
    print(f"   ✗ nebula_graph_query 模块导入失败: {e}")
    sys.exit(1)

# 检查 graph_api 模块是否可以导入
try:
    from tools.graph_api import GraphAPIClient
    print("   ✓ graph_api 模块导入成功")
except Exception as e:
    print(f"   ✗ graph_api 模块导入失败: {e}")

print(f"\n3. GraphAPI 客户端测试:")
if not graph_api_key:
    print("   ⚠️  跳过 GraphAPI 测试（GRAPH_API_KEY 未设置）")
else:
    try:
        client = GraphAPIClient()
        print(f"   ✓ GraphAPIClient 初始化成功")
        
        # 测试 health 接口
        print(f"\n   测试 health 接口...")
        health_response = client.health()
        print(f"   ✓ Health 检查成功: {health_response}")
        
        # 测试 spaces 接口
        print(f"\n   测试 spaces 接口...")
        spaces = client.list_spaces()
        print(f"   ✓ 可用空间: {spaces}")
        
        if spaces:
            # 测试第一个空间的 tags
            print(f"\n   测试第一个空间 ({spaces[0]}) 的 tags...")
            tags = client.list_tags(space=spaces[0])
            print(f"   ✓ Tags: {tags}")
            
    except Exception as e:
        print(f"   ✗ GraphAPI 测试失败: {e}")

print(f"\n4. NebulaGraphQueryTool 测试:")
try:
    tool = NebulaGraphQueryTool()
    print(f"   ✓ NebulaGraphQueryTool 初始化成功")
    
    if not graph_api_key:
        print(f"   ⚠️  跳过实际查询测试（GRAPH_API_KEY 未设置）")
    else:
        print(f"\n   尝试执行简单查询（SHOW EDGES）...")
        result = tool._run(
            query="SHOW EDGES",
            output_format="json"
        )
        print(f"   ✓ 查询成功")
        print(f"   结果长度: {len(result)} 字符")
        
except Exception as e:
    print(f"   ✗ NebulaGraphQueryTool 测试失败: {e}")
    import traceback
    print(f"   错误详情:\n{traceback.format_exc()}")

print("\n" + "=" * 60)
print("测试完成")
print("=" * 60)
