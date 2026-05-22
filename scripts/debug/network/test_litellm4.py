"""调试 httpx 补丁"""
import os
os.chdir(r'D:/app/work/wishSpace/workspace/yuanxi')
os.environ['SSL_CERT_FILE'] = ''

import httpx

# 强制 verify=False，即使调用方传了 SSLContext
orig_init = httpx.Client.__init__
def patched_init(self, **kw):
    old_verify = kw.get('verify', 'NOT SET')
    kw['verify'] = False  # 强制覆盖
    print(f'[PATCH] Client.__init__: verify was {old_verify}, now False')
    orig_init(self, **kw)
httpx.Client.__init__ = patched_init

# 确认 send 补丁生效
orig_send = httpx.Client.send
def patched_send(self, request, **kw):
    old_ua = request.headers.get('user-agent', 'NONE')
    has_stainless = any(h.startswith('x-stainless') for h in request.headers)
    print(f'[PATCH] Client.send: UA={old_ua}, has_x_stainless={has_stainless}')
    request.headers['user-agent'] = 'curl/7.68.0'
    for h in list(request.headers.keys()):
        if h.startswith('x-stainless'):
            del request.headers[h]
    return orig_send(self, request, **kw)
httpx.Client.send = patched_send

from dotenv import load_dotenv
load_dotenv()
import litellm
litellm.api_base = os.getenv('OPENAI_API_BASE')
litellm.api_key = os.getenv('OPENAI_API_KEY')

model = 'openai/' + os.getenv('OPENAI_MODEL_NAME')
print(f'Model: {model}')
try:
    r = litellm.completion(model=model, messages=[{'role':'user','content':'Say hello'}], max_tokens=10)
    print('OK:', r)
except Exception as e:
    print('Error:', type(e).__name__)
