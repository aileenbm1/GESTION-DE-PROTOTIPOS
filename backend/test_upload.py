import requests
from pathlib import Path
p = Path('test_upload.txt')
p.write_text('dummy video content', encoding='utf-8')
with open(p, 'rb') as f:
    files = {'file': ('test_upload.txt', f, 'text/plain')}
    resp = requests.post('http://127.0.0.1:8000/api/projects/proj_6e1591baf0/upload', files=files)
    print(resp.status_code)
    print(resp.text)
