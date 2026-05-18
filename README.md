# yuanxi

## 项目结构

```
├── agents/
│   ├── __init__.py
│   ├── agent1.py          # 调度精灵
│   └── agent2.py          # 干活精灵
├── tools/
│   ├── __init__.py
│   ├── kg_query.py        # NebulaGraph 工具（按需）
│   └── ...
├── integration.py         # 集成入口（重点！）
├── .env.example           # 配置文件
├── .gitignore             # 提交代码需要忽略的文件名称
├── requirements.txt
└── README.md
```

## Python 旧版本切换到新版本

```bash
# 1. 退出当前虚拟环境（如果已激活）
deactivate

# 2. 删除基于 Python 3.9 的旧虚拟环境
rm -rf venv

# 3. 切换到 Python 3.12.7（你之前已安装）
pyenv shell 3.12.7

# 4. 确认版本（必须显示 3.12.7）
python3 --version

# 5. 重新创建虚拟环境
python3 -m venv venv

# 6. 激活虚拟环境
source venv/bin/activate

# 7. 安装依赖
pip install -r requirements.txt
```