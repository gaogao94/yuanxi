"""
最终修复方案：
1. 修改 httpx.HTTPTransport.handle_request 来修改请求头
2. 修改 httpx.Client.__init__ 来强制 verify=False
"""
import os
os.chdir(r'D:/app/work/wishSpace/workspace/yuanxi')

from dotenv import load_dotenv
load_dotenv()

import httpx

# 方案A：patch HTTPTransport.handle_request
orig_handle = httpx.HTTPTransport.handle_request
def patched_handle(self, request):
    request.headers['user-agent'] = 'curl/7.68.0'
    for h in list(request.headers.keys()):
        if h.startswith('x-stainless'):
            del request.headers[h]
    return orig_handle(self, request)
httpx.HTTPTransport.handle_request = patched_handle

# 方案B：强制 Client 使用 verify=False
orig_client_init = httpx.Client.__init__
def patched_client_init(self, **kw):
    kw['verify'] = False
    orig_client_init(self, **kw)
httpx.Client.__init__ = patched_client_init

# 测试 openai
from openai import OpenAI
client = OpenAI(
    api_key=os.getenv('OPENAI_API_KEY'),
    base_url=os.getenv('OPENAI_API_BASE'),
)
try:
    r = client.chat.completions.create(
        model=os.getenv('OPENAI_MODEL_NAME'),
        messages=[{'role':'user','content':'Say hello'}],
        max_tokens=10
    )
    print('OpenAI OK:', r.choices[0].message.content)
except Exception as e:
    print('OpenAI Error:', type(e).__name__, str(e)[:200])

# 测试 litellm
import litellm
litellm.api_base = os.getenv('OPENAI_API_BASE')
litellm.api_key = os.getenv('OPENAI_API_KEY')

try:
    r = litellm.completion(
        model='openai/' + os.getenv('OPENAI_MODEL_NAME'),
        messages=[{'role':'user','content':'Say hello'}],
        max_tokens=10,
    )
    print('LiteLLM OK:', r.choices[0].message.content)
except Exception as e:
    print('LiteLLM Error:', type(e).__name__, str(e)[:200])
