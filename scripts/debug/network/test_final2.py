"""最终解决方案：monkey-patch 让 litellm 能工作"""
import os
os.chdir(r'D:/app/work/wishSpace/workspace/yuanxi')
os.environ['SSL_CERT_FILE'] = ''

import httpx
# 修复 SSL 和请求头
orig_handle = httpx.HTTPTransport.handle_request
def patched_handle(self, request):
    request.headers['user-agent'] = 'curl/7.68.0'
    for h in list(request.headers.keys()):
        if h.startswith('x-stainless'):
            del request.headers[h]
    return orig_handle(self, request)
httpx.HTTPTransport.handle_request = patched_handle

orig_client_init = httpx.Client.__init__
def patched_client_init(self, **kw):
    kw['verify'] = False
    orig_client_init(self, **kw)
httpx.Client.__init__ = patched_client_init

from dotenv import load_dotenv
load_dotenv()

# 给 ChatCompletion 对象添加 parse 方法，解决 litellm 兼容性问题
# litellm 尝试调用 response.parse() 但该方法只存在于 client.chat.completions 上
from openai.types.chat import ChatCompletion
def _chat_completion_parse_patch(self):
    raise NotImplementedError("Parsing not supported for this model")
ChatCompletion.parse = _chat_completion_parse_patch

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
    print('LiteLLM Error:', type(e).__name__, str(e)[:300])
