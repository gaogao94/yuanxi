"""测试 API 请求"""
import os
os.chdir(r'D:/app/work/wishSpace/workspace/yuanxi')

from dotenv import load_dotenv
load_dotenv()

import requests
import json

base = os.getenv('OPENAI_API_BASE')
key = os.getenv('OPENAI_API_KEY')
model = os.getenv('OPENAI_MODEL_NAME')

print('Base:', base)
print('Model:', model)
print('Key:', key[:20] + '...')

# 先查模型列表
r = requests.get(f'{base}/models', headers={'Authorization': f'Bearer {key}'}, verify=False)
print('Models:', r.status_code)
if r.status_code == 200:
    data = r.json()
    for m in data['data']:
        print('  -', m['id'])

# 用模型列表中的 ID 测试
for m in data['data']:
    mid = m['id']
    print(f'\nTrying model: {mid}')
    r = requests.post(f'{base}/chat/completions',
        json={'model': mid, 'messages': [{'role':'user','content':'hi'}], 'max_tokens': 10},
        headers={'Authorization': f'Bearer {key}'},
        verify=False, timeout=30)
    print(f'  Status: {r.status_code}')
    if r.status_code == 200:
        print(f'  Response: {r.json()["choices"][0]["message"]["content"]}')
        break
    else:
        print(f'  Error: {r.text[:200]}')
