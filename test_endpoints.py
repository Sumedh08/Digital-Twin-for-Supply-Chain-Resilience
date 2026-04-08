import urllib.request
import urllib.error
import json
try:
    req2 = urllib.request.Request("http://127.0.0.1:8000/ai/legal/vector", data=b'{"query": "Hello"}', headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req2) as response:
        print("AI:", response.read().decode())
except urllib.error.HTTPError as e:
    print("AI ERR BODY:", e.read().decode())
