"""测试通过自定义 transport 层解决"""
import os
os.chdir(r'D:/app/work/wishSpace/workspace/yuanxi')

from dotenv import load_dotenv
load_dotenv()

import httpx

# 创建自定义 transport，在发送前修改请求
class CustomTransport(httpx.BaseTransport):
    def __init__(self):
        self._transport = httpx.HTTPTransport(verify=False)
    
    def handle_request(self, request):
        # 修改请求头
        request.headers['user-agent'] = 'curl/7.68.0'
        for h in list(request.headers.keys()):
            if h.startswith('x-stainless'):
                del request.headers[h]
        return self._transport.handle_request(request)

# 创建使用自定义 transport 的 client
transport = CustomTransport()
client = httpx.Client(transport=transport)

# 用这个 client 调用 OpenAI
from openai import OpenAI
openai_client = OpenAI(
    api_key=os.getenv('OPENAI_API_KEY'),
    base_url=os.getenv('OPENAI_API_BASE'),
    http_client=client,
)
try:
    r = openai_client.chat.completions.create(
        model=os.getenv('OPENAI_MODEL_NAME'),
        messages=[{'role':'user','content':'Say hello'}],
        max_tokens=10
    )
    print('OK:', r.choices[0].message.content)
except Exception as e:
    print('Error:', type(e).__name__, str(e)[:200])

# 测试 LiteLLM 也使用这个 transport
# LiteLLM 允许传递 litellm.client_session 或通过环境变量配置
import litellm
litellm.api_base = os.getenv('OPENAI_API_BASE')
litellm.api_key = os.getenv('OPENAI_API_KEY')
# 设置默认的 httpx 客户端
try:
    r = litellm.completion(
        model='openai/' + os.getenv('OPENAI_MODEL_NAME'),
        messages=[{'role':'user','content':'Say hello'}],
        max_tokens=10,
        client=client  # 传递自定义 client
    )
    print('LiteLLM OK:', r.choices[0].message.content)
except Exception as e:
    print('LiteLLM Error:', type(e).__name__, str(e)[:200])
