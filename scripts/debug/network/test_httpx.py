"""测试原始 httpx 请求是否正常工作"""
import os
os.chdir(r'D:/app/work/wishSpace/workspace/yuanxi')

from dotenv import load_dotenv
load_dotenv()

import httpx

base = os.getenv('OPENAI_API_BASE')
key = os.getenv('OPENAI_API_KEY')
model = os.getenv('OPENAI_MODEL_NAME')

# 直接 httpx 请求
r = httpx.post(
    base + '/chat/completions',
    json={'model': model, 'messages': [{'role':'user','content':'hi'}], 'max_tokens': 10},
    headers={'Authorization': f'Bearer {key}'},
    verify=False,
    timeout=30
)
print(f'httpx verify=False: {r.status_code}')
print(r.text[:200])

# 用自定义 SSL context
import ssl
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

r2 = httpx.post(
    base + '/chat/completions',
    json={'model': model, 'messages': [{'role':'user','content':'hi'}], 'max_tokens': 10},
    headers={'Authorization': f'Bearer {key}'},
    verify=ctx,
    timeout=30
)
print(f'httpx verify=SSLContext: {r2.status_code}')
print(r2.text[:200])
