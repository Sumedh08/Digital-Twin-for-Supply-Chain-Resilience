
import http.server, socketserver
from pathlib import Path
base = '/Digital-Twin-for-Supply-Chain-Resilience'
root = Path(r'C:\Users\Sumed\Downloads\globaltradedigitaltwin\dist')
class Handler(http.server.SimpleHTTPRequestHandler):
    def translate_path(self, path):
        if path.startswith(base):
            rel = path[len(base):] or '/'
        else:
            rel = path
        rel = rel.split('?',1)[0].split('#',1)[0]
        rel = rel.lstrip('/')
        return str(root / rel)
    def do_GET(self):
        spa_paths = [base, base + '/', base + '/digital-twin/india-steel', base + '/tradegpt', base + '/vector-rag', base + '/rag-comparison']
        if self.path in spa_paths or self.path.startswith(base + '/digital-twin/'):
            self.path = base + '/index.html'
        return super().do_GET()
PORT = 4173
with socketserver.TCPServer(('127.0.0.1', PORT), Handler) as httpd:
    httpd.serve_forever()
