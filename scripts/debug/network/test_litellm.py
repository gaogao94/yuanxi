"""测试 LiteLLM 调用"""
import os
os.chdir(r'D:/app/work/wishSpace/workspace/yuanxi')
os.environ['SSL_CERT_FILE'] = ''

import httpx
_orig = httpx.Client.__init__
def _patched(self, **kw):
    kw.setdefault('verify', False)
    _orig(self, **kw)
httpx.Client.__init__ = _patched

from dotenv import load_dotenv
load_dotenv()

import litellm
litellm.api_base = os.getenv('OPENAI_API_BASE')
litellm.api_key = os.getenv('OPENAI_API_KEY')

model = 'openai/' + os.getenv('OPENAI_MODEL_NAME')
print('Model:', model)

try:
    r = litellm.completion(model=model, messages=[{'role':'user','content':'Say hello in one word'}], max_tokens=10)
    print('Success:', r.choices[0].message.content)
except Exception as e:
    print('Error:', str(e)[:300])
