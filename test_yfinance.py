import urllib.request
import json
url = "https://query2.finance.yahoo.com/v8/finance/chart/KRBN?range=1mo&interval=1d"
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
with urllib.request.urlopen(req) as response:
    data = json.loads(response.read().decode())
    print(data["chart"]["result"][0]["meta"]["regularMarketPrice"])
