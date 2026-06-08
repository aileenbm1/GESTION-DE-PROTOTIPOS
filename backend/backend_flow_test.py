import requests
import json
from pathlib import Path

base = 'http://127.0.0.1:8000'

print('health', requests.get(f'{base}/health').status_code, requests.get(f'{base}/health').json())
print('api health', requests.get(f'{base}/api/health').status_code, requests.get(f'{base}/api/health').json())

res = requests.post(f'{base}/api/projects', json={'name': 'Test Proyecto Flux'})
print('create', res.status_code)
print(res.json())
project = res.json()
project_id = project['id']

p = Path('test_upload2.txt')
p.write_text('dummy video content', encoding='utf-8')
with open(p, 'rb') as f:
    files = {'file': ('test_upload2.txt', f, 'text/plain')}
    resp = requests.post(f'{base}/api/projects/{project_id}/upload', files=files)
    print('upload', resp.status_code)
    print(resp.json())

resp = requests.post(f'{base}/api/projects/{project_id}/run-initial')
print('run_initial', resp.status_code)
print(resp.json())

resp = requests.post(f'{base}/api/projects/{project_id}/screens/generate')
print('generate_screens', resp.status_code)
print(resp.text)

resp = requests.post(f'{base}/api/projects/{project_id}/architecture')
print('generate_architecture', resp.status_code)
print(resp.text)

resp = requests.post(f'{base}/api/projects/{project_id}/code')
print('generate_code', resp.status_code)
print(resp.text)

resp = requests.post(f'{base}/api/projects/{project_id}/package')
print('package', resp.status_code)
print(resp.text)

resp = requests.get(f'{base}/api/projects/{project_id}/download')
print('download', resp.status_code, resp.headers.get('content-type'))
