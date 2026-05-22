"""测试 OpenAI 库 vs requests"""
import os
os.chdir(r'D:/app/work/wishSpace/workspace/yuanxi')

from dotenv import load_dotenv
load_dotenv()

import httpx
from openai import OpenAI

# 用 httpx 测试
http_client = httpx.Client(verify=False)
r = http_client.post(
    url=os.getenv('OPENAI_API_BASE') + '/chat/completions',
    json={
        'model': os.getenv('OPENAI_MODEL_NAME'),
        'messages': [{'role':'user','content':'Say hi'}],
        'max_tokens': 10
    },
    headers={'Authorization': f'Bearer {os.getenv("OPENAI_API_KEY")}'}
)
print('httpx Status:', r.status_code)
if r.status_code != 200:
    print('httpx Error:', r.text[:300])
else:
    print('httpx OK')

# 用 OpenAI 库测试
client = OpenAI(
    api_key=os.getenv('OPENAI_API_KEY'),
    base_url=os.getenv('OPENAI_API_BASE'),
    http_client=http_client,
)
try:
    r = client.chat.completions.create(
        model=os.getenv('OPENAI_MODEL_NAME'),
        messages=[{'role':'user','content':'Say hi'}],
        max_tokens=10
    )
    print('OpenAI SDK OK:', r.choices[0].message.content)
except Exception as e:
    print('OpenAI SDK Error:', type(e).__name__, str(e)[:300])
