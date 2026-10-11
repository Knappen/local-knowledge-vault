"""Isolated privacy and health smoke test for the standalone server."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request


PORT = 13479
BASE = f'http://127.0.0.1:{PORT}'


def request(path, method='GET', headers=None, data=None):
    req = urllib.request.Request(BASE+path, method=method, headers=headers or {}, data=data)
    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()


with tempfile.TemporaryDirectory(prefix='knowledge-vault-') as private_data:
    env = os.environ.copy()
    env.update(AIWS_KNOWLEDGE_ROOT=private_data, AIWS_RAG_PYTHON=sys.executable,
               KNOWLEDGE_PORT=str(PORT), PYTHONUNBUFFERED='1')
    process = subprocess.Popen([sys.executable, str(Path(__file__).parent/'portable_server.py')],
                               cwd=Path(__file__).parent, env=env,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        for _ in range(50):
            try:
                if request('/health')[0] == 200: break
            except urllib.error.URLError: time.sleep(.1)
        else: raise AssertionError('Portable server did not become healthy.')
        status,page = request('/rag')
        assert status == 200 and b'PRIVATE KNOWLEDGE VAULT' in page and b'/harness' not in page
        bad = urllib.request.Request(BASE+'/health', headers={'Host':'example.com'})
        try: urllib.request.urlopen(bad, timeout=5)
        except urllib.error.HTTPError as exc: assert exc.code == 403
        else: raise AssertionError('Untrusted Host header was accepted.')
        status,body = request('/api/rag/search', 'POST', {'Content-Type':'application/json'},
                              json.dumps({'question':'private'}).encode())
        assert status == 403 and b'Same-origin' in body
        print('Portable server health, loopback Host validation, and same-origin writes passed.')
    finally:
        process.terminate()
        try: process.wait(timeout=10)
        except subprocess.TimeoutExpired: process.kill()
