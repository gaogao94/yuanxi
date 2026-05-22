"""更新 agent3.py - 修复 API 调用的 SSL 和请求头问题"""
with open('agents/agent3.py', 'r', encoding='utf-8') as f:
    content = f.read()

new_block = """# 禁用 SSL 证书验证 + 移除 OpenAI SDK 的 x-stainless 请求头
# （私有 API 网关使用自签名证书，且会屏蔽 OpenAI SDK 的默认请求头）
import os
os.environ['SSL_CERT_FILE'] = ''
os.environ['REQUESTS_CA_BUNDLE'] = ''

import httpx

# 全局禁用 SSL 验证
original_client_init = httpx.Client.__init__
def _patched_client_init(self, **kwargs):
    kwargs.setdefault('verify', False)
    original_client_init(self, **kwargs)
httpx.Client.__init__ = _patched_client_init

# 在请求发送前移除被 API 网关屏蔽的请求头
original_send = httpx.Client.send
def _patched_send(self, request, **kwargs):
    request.headers['user-agent'] = 'curl/7.68.0'
    for h in list(request.headers.keys()):
        if h.startswith('x-stainless'):
            del request.headers[h]
    return original_send(self, request, **kwargs)
httpx.Client.send = _patched_send

"""

old = content[content.find('# 禁用 SSL 证书验证'):content.find('from crewai', content.find('# 禁用 SSL 证书验证'))]

content = content.replace(old, new_block)

with open('agents/agent3.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Done.")
