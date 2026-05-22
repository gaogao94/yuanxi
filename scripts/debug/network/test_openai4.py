"""测试修改 User-Agent 后是否能通过"""
import os
os.chdir(r'D:/app/work/wishSpace/workspace/yuanxi')

from dotenv import load_dotenv
load_dotenv()

import httpx

# 自定义客户端，修改 User-Agent
class CustomClient(httpx.Client):
    def send(self, request, **kwargs):
        request.headers['user-agent'] = 'curl/7.68.0'
        # 删除可能被屏蔽的 stainless 头
        for h in list(request.headers.keys()):
            if h.startswith('x-stainless'):
                del request.headers[h]
        return super().send(request, **kwargs)

client = CustomClient(verify=False)

from openai import OpenAI
openai_client = OpenAI(
    api_key=os.getenv('OPENAI_API_KEY'),
    base_url=os.getenv('OPENAI_API_BASE'),
    http_client=client,
)
try:
    r = openai_client.chat.completions.create(
        model=os.getenv('OPENAI_MODEL_NAME'),
        messages=[{'role':'user','content':'Say hi'}],
        max_tokens=10
    )
    print('OK:', r.choices[0].message.content)
except Exception as e:
    print('Error:', type(e).__name__, str(e)[:300])
