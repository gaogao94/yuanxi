"""调试 LiteLLM 调用"""
import os
os.chdir(r'D:/app/work/wishSpace/workspace/yuanxi')
os.environ['SSL_CERT_FILE'] = ''

import httpx

# 先打补丁，再导入 litellm
orig_init = httpx.Client.__init__
def patched_init(self, **kw):
    kw.setdefault('verify', False)
    orig_init(self, **kw)
httpx.Client.__init__ = patched_init

orig_send = httpx.Client.send
def patched_send(self, request, **kw):
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

# 使用 openai/ 前缀
model = 'openai/' + os.getenv('OPENAI_MODEL_NAME').lstrip('/')
print('Model:', model)

try:
    r = litellm.completion(model=model, messages=[{'role':'user','content':'Say hello'}], max_tokens=10)
    print('OK:', r.choices[0].message.content)
except Exception as e:
    print('Error:', type(e).__name__)
    print(str(e)[:400])
