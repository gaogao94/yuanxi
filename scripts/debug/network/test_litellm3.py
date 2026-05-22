"""调试 LiteLLM 连接错误"""
import os
os.chdir(r'D:/app/work/wishSpace/workspace/yuanxi')
os.environ['SSL_CERT_FILE'] = ''

# 先打补丁
import httpx
orig_init = httpx.Client.__init__
def patched_init(self, **kw):
    print(f'[DEBUG] httpx.Client.__init__ called with verify={kw.get("verify", "NOT SET")}')
    kw.setdefault('verify', False)
    kw.setdefault('timeout', httpx.Timeout(60.0))
    orig_init(self, **kw)
httpx.Client.__init__ = patched_init

# 加载配置
from dotenv import load_dotenv
load_dotenv()

# 测试直接用 openai 库（确认 httpx 补丁有效）
from openai import OpenAI
client = OpenAI(
    api_key=os.getenv('OPENAI_API_KEY'),
    base_url=os.getenv('OPENAI_API_BASE'),
)
print('[TEST] openai library test...')
try:
    r = client.chat.completions.create(
        model=os.getenv('OPENAI_MODEL_NAME'),
        messages=[{'role':'user','content':'Say hello'}],
        max_tokens=10
    )
    print('[TEST] openai OK:', r.choices[0].message.content)
except Exception as e:
    print('[TEST] openai Error:', type(e).__name__, str(e)[:200])

# 测试 LiteLLM
print('[TEST] litellm test...')
import litellm
litellm.set_verbose = True
litellm.api_base = os.getenv('OPENAI_API_BASE')
litellm.api_key = os.getenv('OPENAI_API_KEY')

model = 'openai/' + os.getenv('OPENAI_MODEL_NAME')
print(f'[TEST] Model: {model}')
try:
    r = litellm.completion(model=model, messages=[{'role':'user','content':'Say hello'}], max_tokens=10)
    print('[TEST] litellm OK:', r.choices[0].message.content)
except Exception as e:
    print('[TEST] litellm Error:', type(e).__name__)
    print(str(e)[:500])
