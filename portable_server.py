"""Privacy-first standalone HTTP server for the local Knowledge Vault."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import ipaddress
import json
import logging
import mimetypes
import os
from pathlib import Path
import sqlite3
from urllib.parse import parse_qs, urlsplit

# Portable defaults are established before importing the RAG module. The
# workstation portal may supply its own environment without changing these.
ROOT = Path(__file__).resolve().parent
os.environ.setdefault('AIWS_KNOWLEDGE_ROOT',str(ROOT/'data'))
os.environ.setdefault('HF_HOME',str(ROOT/'.cache/huggingface'))
os.environ.setdefault('AIWS_FASTEMBED_CACHE',str(ROOT/'.cache/fastembed'))
os.environ.setdefault('AIWS_ACTIVE_BACKEND','http://127.0.0.1:11434')
os.environ.setdefault('AIWS_PROFILE_ROUTER',os.environ['AIWS_ACTIVE_BACKEND'])
os.environ.setdefault('AIWS_RAG_PYTHON',os.sys.executable)

import rag


PUBLIC = ROOT / 'public'
HOST = os.environ.get('KNOWLEDGE_HOST', '127.0.0.1')
PORT = int(os.environ.get('KNOWLEDGE_PORT', '1337'))
ALLOWED_HOSTS = {f'127.0.0.1:{PORT}', f'localhost:{PORT}'}
STATIC = {'/rag':'rag.html','/rag.js':'rag.js','/rag.css':'rag.css','/favicon.svg':'favicon.svg'}


class Handler(BaseHTTPRequestHandler):
    server_version = 'LocalKnowledgeVault/1.0'

    def log_message(self, fmt, *args):
        logging.info('%s %s', self.client_address[0], fmt % args)

    def trusted(self, write=False):
        if not ipaddress.ip_address(self.client_address[0]).is_loopback:
            return False
        host = self.headers.get('Host','')
        if host not in ALLOWED_HOSTS:
            return False
        origin = self.headers.get('Origin')
        if write:
            content = self.headers.get('Content-Type','')
            valid_type = content.startswith('application/json') or (
                self.path.startswith('/api/rag/chunk?') and content == 'application/octet-stream')
            return origin == 'http://' + host and valid_type
        return not origin or origin == 'http://' + host

    def send_data(self, status, data, content_type='application/json; charset=utf-8'):
        if not isinstance(data, bytes):
            data = json.dumps(data, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        for key,value in {
            'Content-Type':content_type,'Content-Length':str(len(data)),'Cache-Control':'no-store',
            'X-Content-Type-Options':'nosniff','X-Frame-Options':'DENY','Referrer-Policy':'no-referrer',
            'Content-Security-Policy':("default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
        }.items(): self.send_header(key,value)
        self.end_headers()
        try: self.wfile.write(data)
        except (BrokenPipeError,ConnectionResetError,ConnectionAbortedError): pass

    def send_file(self, path):
        size=path.stat().st_size;start,end,status=0,size-1,200
        header=self.headers.get('Range')
        if header:
            try:
                unit,values=header.split('=',1);a,b=values.split('-',1)
                if unit!='bytes' or ',' in values: raise ValueError
                start=int(a) if a else max(0,size-int(b));end=int(b) if b else size-1
                if start<0 or end<start or start>=size: raise ValueError
                end=min(end,size-1);status=206
            except (ValueError,TypeError):
                return self.send_data(416,{'error':'Invalid byte range.'})
        self.send_response(status)
        self.send_header('Content-Type',mimetypes.guess_type(path.name)[0] or 'application/octet-stream')
        self.send_header('Content-Length',str(end-start+1));self.send_header('Accept-Ranges','bytes')
        self.send_header('Content-Disposition',f'inline; filename="{path.name}"')
        self.send_header('Cache-Control','private, no-store');self.send_header('X-Content-Type-Options','nosniff')
        if status==206:self.send_header('Content-Range',f'bytes {start}-{end}/{size}')
        self.end_headers()
        with path.open('rb') as stream:
            stream.seek(start);remaining=end-start+1
            while remaining:
                block=stream.read(min(1024*1024,remaining))
                if not block:break
                self.wfile.write(block);remaining-=len(block)

    def do_GET(self):
        if not self.trusted(): return self.send_data(403,{'error':'Loopback access only.'})
        path=urlsplit(self.path).path
        if path=='/':
            self.send_response(302);self.send_header('Location','/rag');self.send_header('Content-Length','0');self.end_headers();return
        try:
            if path=='/health':return self.send_data(200,{'status':'ok','service':'Local Knowledge Vault'})
            if path=='/api/rag/status':return self.send_data(200,rag.listing())
            if path=='/api/rag/models':return self.send_data(200,rag.models())
            if path=='/api/rag/file':
                document_id=parse_qs(urlsplit(self.path).query).get('id',[''])[0]
                return self.send_file(rag.file_path(document_id))
            if path in STATIC:
                file=PUBLIC/STATIC[path]
                kind=(mimetypes.guess_type(file.name)[0] or 'application/octet-stream')
                if kind.startswith('text/') or kind=='application/javascript':kind+='; charset=utf-8'
                data=file.read_bytes()
                if path=='/rag':
                    page=data.decode('utf-8').replace('Knowledge Vault / AIWS','Local Knowledge Vault')
                    page=page.replace('<header><a href="/">&larr; Workstation overview</a><span>AIWS / KNOWLEDGE VAULT</span><a href="/harness">DeepSeek Harness &nearr;</a></header>',
                        '<header><a href="/rag">LOCAL ONLY</a><span>PRIVATE KNOWLEDGE VAULT</span><a href="/health">Health</a></header>')
                    data=page.encode('utf-8')
                return self.send_data(200,data,kind)
            return self.send_data(404,{'error':'Not found'})
        except ValueError as exc:return self.send_data(404,{'error':str(exc)})
        except (OSError,RuntimeError,sqlite3.Error) as exc:return self.send_data(503,{'error':str(exc)[:500]})

    def do_POST(self):
        if not self.trusted(write=True):return self.send_data(403,{'error':'Same-origin loopback request required.'})
        path=urlsplit(self.path).path
        if not path.startswith('/api/rag/'):return self.send_data(404,{'error':'Not found'})
        try:
            if path=='/api/rag/chunk':
                params=parse_qs(urlsplit(self.path).query);length=int(self.headers.get('Content-Length','0'))
                result=rag.chunk(params.get('id',[''])[0],int(params.get('offset',['-1'])[0]),self.rfile,length)
            else:
                length=int(self.headers.get('Content-Length','0'))
                if not 0<length<=4096:raise ValueError('Invalid request size.')
                data=json.loads(self.rfile.read(length))
                if path=='/api/rag/begin':result=rag.begin(data)
                elif path=='/api/rag/finish':result=rag.finish(data.get('id'))
                elif path=='/api/rag/retry':result=rag.retry(data.get('kind'),data.get('id'))
                elif path=='/api/rag/search':result=rag.search(data.get('question'),int(data.get('limit',8)))
                elif path=='/api/rag/ask':result=rag.ask(data.get('question'),data.get('model'))
                else:return self.send_data(404,{'error':'Not found'})
            return self.send_data(200,result)
        except (ValueError,TypeError,KeyError) as exc:return self.send_data(400,{'error':str(exc)})
        except (OSError,RuntimeError,sqlite3.Error) as exc:
            logging.exception('RAG request failed');return self.send_data(503,{'error':str(exc)[:500]})


if __name__=='__main__':
    if HOST not in ('127.0.0.1','localhost'):
        raise SystemExit('Refusing non-loopback bind. Set KNOWLEDGE_HOST to 127.0.0.1 or localhost.')
    logging.basicConfig(level=logging.INFO,format='%(asctime)s %(levelname)s %(message)s')
    print(f'Local Knowledge Vault: http://127.0.0.1:{PORT}/rag')
    ThreadingHTTPServer((HOST,PORT),Handler).serve_forever()
