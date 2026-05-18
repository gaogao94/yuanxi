# yuanxi
# 项目结构
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