"""测试 OpenAI 库（带自定义 http_client）"""
import os
os.chdir(r'D:/app/work/wishSpace/workspace/yuanxi')
os.environ['SSL_CERT_FILE'] = ''

import httpx
from dotenv import load_dotenv
load_dotenv()

from openai import OpenAI

# 创建不验证 SSL 的 httpx 客户端
http_client = httpx.Client(verify=False)

client = OpenAI(
    api_key=os.getenv('OPENAI_API_KEY'),
    base_url=os.getenv('OPENAI_API_BASE'),
    http_client=http_client,
)

try:
    r = client.chat.completions.create(
        model=os.getenv('OPENAI_MODEL_NAME'),
        messages=[{'role':'user','content':'Say hello in one word'}],
        max_tokens=10
    )
    print('Success:', r.choices[0].message.content)
except Exception as e:
    print('Error:', type(e).__name__, str(e)[:300])
