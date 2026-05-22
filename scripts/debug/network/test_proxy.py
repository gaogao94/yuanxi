"""测试修改后的请求是否真的被发送"""
import os
os.chdir(r'D:/app/work/wishSpace/workspace/yuanxi')

import socketserver
import threading
import json

# 启动一个本地代理来查看实际发送的请求
import http.server

class ProxyHandler(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)
        print(f'=== PROXY RECEIVED ===')
        print(f'Headers: {dict(self.headers)}')
        print(f'Body: {body[:200]}')
        print(f'=======================')
        self.send_response(200)
        self.end_headers()
        self.wfile.write(json.dumps({"choices":[{"message":{"content":"ok"}}]}).encode())

# 在实际环境中，我们无法启动代理服务器。改用 urllib 直接测试
import urllib.request
import ssl

ssl_ctx = ssl.create_default_context()
ssl_ctx.check_hostname = False
ssl_ctx.verify_mode = ssl.CERT_NONE

from dotenv import load_dotenv
load_dotenv()

# 直接用原始 httpx 测试（确认 API 是否真的工作）
import httpx
client = httpx.Client(verify=False)
r = client.post(
    url=os.getenv('OPENAI_API_BASE') + '/chat/completions',
    json={'model': os.getenv('OPENAI_MODEL_NAME'), 'messages': [{'role':'user','content':'hi'}], 'max_tokens': 10},
    headers={'Authorization': f'Bearer {os.getenv("OPENAI_API_KEY")}', 'user-agent': 'curl/7.68.0'},
)
print(f'Raw httpx status: {r.status_code}')
print(f'Raw httpx response: {r.text[:200]}')
