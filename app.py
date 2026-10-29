"""Offline CLI and loopback-only analysis workbench. Python 3.11+, no dependencies."""
import argparse,json,sys,hashlib
from pathlib import Path
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from engine import analyze
ROOT=Path(__file__).resolve().parent

def load(raw):
    def invalid(value):raise ValueError('Non-finite JSON number: '+value)
    return json.loads(raw,parse_constant=invalid)

def main():
    parser=argparse.ArgumentParser(description='Local analysis workbench')
    sub=parser.add_subparsers(dest='command',required=True)
    check=sub.add_parser('analyze');check.add_argument('input');check.add_argument('--output')
    server=sub.add_parser('serve');server.add_argument('--port',type=int,default=8080)
    args=parser.parse_args()
    if args.command=='analyze':
        try:result=analyze(load(Path(args.input).read_text()));text=json.dumps(result,indent=2,ensure_ascii=False,allow_nan=False)+'\n'
        except (ValueError,KeyError,TypeError,OverflowError,RecursionError,OSError) as e:parser.exit(2,'Invalid input: '+str(e)+'\n')
        if args.output:Path(args.output).write_text(text)
        else:print(text,end='')
        return
    if not 1024<=args.port<=65535:parser.error('port must be 1024..65535')
    class Handler(BaseHTTPRequestHandler):
        def reply(self,status,body,typ='application/json'):
            if not isinstance(body,bytes):body=body.encode()
            self.send_response(status);self.send_header('Content-Type',typ+'; charset=utf-8');self.send_header('Content-Length',str(len(body)));self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');self.send_header('Referrer-Policy','no-referrer');self.end_headers();self.wfile.write(body)
        def host_ok(self):return self.headers.get('Host') in [f'127.0.0.1:{args.port}',f'localhost:{args.port}']
        def do_GET(self):
            if not self.host_ok():return self.reply(403,'{"error":"Invalid host"}')
            if self.path=='/':return self.reply(200,(ROOT/'index.html').read_bytes(),'text/html')
            if self.path=='/example.json':return self.reply(200,(ROOT/'example.json').read_bytes())
            return self.reply(404,'{"error":"Not found"}')
        def do_POST(self):
            if not self.host_ok():return self.reply(403,'{"error":"Invalid host"}')
            if self.path!='/analyze':return self.reply(404,'{"error":"Not found"}')
            if self.headers.get('Content-Type','').split(';')[0]!='application/json':return self.reply(415,'{"error":"JSON required"}')
            origin=self.headers.get('Origin')
            if origin and origin not in [f'http://127.0.0.1:{args.port}',f'http://localhost:{args.port}']:return self.reply(403,'{"error":"Origin rejected"}')
            try:
                n=int(self.headers.get('Content-Length','0'))
                if not 0<n<=2*1024*1024:return self.reply(413,'{"error":"Input must be between 1 byte and 2 MB"}')
                result=analyze(load(self.rfile.read(n).decode('utf-8')));body=json.dumps(result,ensure_ascii=False,allow_nan=False)
                self.reply(200,body)
            except (ValueError,KeyError,TypeError,OverflowError,RecursionError,UnicodeError) as e:self.reply(400,json.dumps({'error':str(e)}))
        def log_message(self,*args):pass
    httpd=ThreadingHTTPServer(('127.0.0.1',args.port),Handler);print(f'Workbench ready: http://127.0.0.1:{args.port}',flush=True)
    try:httpd.serve_forever()
    except KeyboardInterrupt:pass
    finally:httpd.server_close()
if __name__=='__main__':main()
