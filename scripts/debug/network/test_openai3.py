"""调试 OpenAI SDK 发送的请求"""
import os
os.chdir(r'D:/app/work/wishSpace/workspace/yuanxi')

from dotenv import load_dotenv
load_dotenv()

import httpx

# 创建一个记录请求的 httpx 客户端
class DebugClient(httpx.Client):
    def send(self, request, **kwargs):
        print(f'--- Request ---')
        print(f'URL: {request.url}')
        print(f'Method: {request.method}')
        print(f'Headers: {dict(request.headers)}')
        print(f'Body: {request.content[:500]}')
        print(f'---------------')
        return super().send(request, **kwargs)

debug_client = DebugClient(verify=False)

from openai import OpenAI
client = OpenAI(
    api_key=os.getenv('OPENAI_API_KEY'),
    base_url=os.getenv('OPENAI_API_BASE'),
    http_client=debug_client,
)
try:
    r = client.chat.completions.create(
        model=os.getenv('OPENAI_MODEL_NAME'),
        messages=[{'role':'user','content':'Say hi'}],
        max_tokens=10
    )
    print('OK:', r.choices[0].message.content)
except Exception as e:
    print('Error:', type(e).__name__, str(e)[:300])
