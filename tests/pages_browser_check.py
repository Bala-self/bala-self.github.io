"""Local static frontend + local HTTPS fixture backend, not a provider deployment.
Covers the actual cross-origin browser transport/CSP and Content-Disposition handling.
No Instagram request is made. A disposable certificate is used only in this test.
"""
import json
import ssl
import subprocess
import sys
import tempfile
import threading
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler,BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
report=[]
with tempfile.TemporaryDirectory(prefix='pocket-export-test-') as temp:
    temp=Path(temp);site=temp/'site'
    subprocess.run([sys.executable,'scripts/export_pages.py','--site-origin','https://pocket-export-fixture.github.io','--backend-origin','https://pocket-export-fixture.onrender.com','--output',str(site)],cwd=ROOT,check=True,capture_output=True)
    class Static(SimpleHTTPRequestHandler):
        def __init__(self,*a,**kw):super().__init__(*a,directory=str(site),**kw)
        def log_message(self,*a):pass
    front=ThreadingHTTPServer(('127.0.0.1',0),Static)
    base=f'http://127.0.0.1:{front.server_port}'
    calls=[];warming=[True]
    class Backend(BaseHTTPRequestHandler):
        def log_message(self,*a):pass
        def reply(self,body=b'',mime='application/json',attachment=False,status=200):
            self.send_response(status)
            self.send_header('Content-Type',mime);self.send_header('Content-Length',str(len(body)))
            self.send_header('Access-Control-Allow-Origin',base)
            self.send_header('Access-Control-Allow-Methods','GET,POST,OPTIONS')
            self.send_header('Access-Control-Allow-Headers','content-type,range')
            self.send_header('Access-Control-Expose-Headers','Content-Disposition,Content-Length')
            if attachment:self.send_header('Content-Disposition','attachment; filename="pocket-fixture.png"')
            self.end_headers();self.wfile.write(body)
        def do_OPTIONS(self):self.reply()
        def do_GET(self):
            path=urlparse(self.path).path;calls.append(('GET',path))
            if path=='/api/health':
                if warming[0]:
                    warming[0]=False;self.reply(b'<html>Starting fixture</html>','text/html',status=503)
                else:self.reply(b'{"status":"ok"}')
            elif path in ('/api/download','/api/preview'):self.reply((ROOT/'static/icon-192.png').read_bytes(),'image/png',path.endswith('download'))
            else:self.send_error(404)
        def do_POST(self):
            calls.append(('POST',urlparse(self.path).path))
            data=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            assert data['url'].startswith('https://www.instagram.com/p/')
            self.reply(json.dumps({'type':'image','author':'fixture','caption':'Locally simulated media, not fetched from Instagram.','expires_in':600,'items':[{'id':'0','quality':'Original','ext':'png','width':192,'height':192,'url':'/api/download?token=fixture','preview_url':'/api/preview?token=fixture'}]}).encode())
    back=ThreadingHTTPServer(('127.0.0.1',0),Backend)
    subprocess.run(['openssl','req','-x509','-newkey','rsa:2048','-keyout',str(temp/'key.pem'),'-out',str(temp/'cert.pem'),'-days','1','-nodes','-subj','/CN=localhost'],check=True,capture_output=True)
    sslcontext=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);sslcontext.load_cert_chain(temp/'cert.pem',temp/'key.pem');back.socket=sslcontext.wrap_socket(back.socket,server_side=True)
    backend=f'https://127.0.0.1:{back.server_port}'
    # Only the temporary test export points at loopback; deliverables never do.
    for file in [site/'client-config.js',site/'index.html',site/'privacy/index.html',site/'terms/index.html']:
        file.write_text(file.read_text().replace('https://pocket-export-fixture.onrender.com',backend))
    for server in (front,back):threading.Thread(target=server.serve_forever,daemon=True).start()
    try:
        with sync_playwright() as p:
            for engine,width in [(p.chromium,390),(p.firefox,1440),(p.webkit,390)]:
                calls.clear();warming[0]=True;browser=engine.launch()
                context=browser.new_context(viewport={'width':width,'height':900},accept_downloads=True,service_workers='block',ignore_https_errors=True)
                page=context.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
                page.goto(base);assert not calls # No background keep-awake traffic.
                assert page.locator('h1').count()==1 and page.evaluate('document.documentElement.scrollWidth <= innerWidth')
                page.locator('#url').fill('https://www.instagram.com/p/ABCDEF/');page.locator('#submit').click()
                assert page.locator('.loading-description').inner_text().startswith('The free server may be asleep')
                page.locator('#results:not([hidden])').wait_for()
                assert ('GET','/api/health') in calls and ('POST','/api/resolve') in calls
                assert page.locator('.media-item img').get_attribute('src').startswith(backend+'/api/preview')
                with page.expect_download(timeout=10000) as e:page.locator('.download-button').first.click()
                assert e.value.suggested_filename=='pocket-fixture.png'
                page.locator('footer a[href="/privacy/"]').click();assert page.locator('h1').inner_text()=='Privacy policy'
                page.locator('#theme').click();assert page.evaluate('document.documentElement.dataset.theme')=='dark'
                assert not errors
                report.append({'engine':engine.name,'width':width,'exported_ui':'pass','local_https_cross_origin_resolve':'pass','local_https_cross_origin_file_save':'pass','cold_start_retry_fixture':'pass','policy_navigation':'pass','page_errors':errors})
                if engine.name=='chromium':
                    offline=browser.new_context(ignore_https_errors=True)
                    tab=offline.new_page();tab.goto(base)
                    tab.evaluate('async()=>await navigator.serviceWorker.ready')
                    tab.wait_for_function('!!navigator.serviceWorker.controller')
                    keys=tab.evaluate('async()=>{let a=[];for(const n of await caches.keys()){for(const r of await(await caches.open(n)).keys())a.push(new URL(r.url).pathname);}return a;}')
                    assert '/privacy/' in keys and '/terms/' in keys
                    assert '/client-config.js' in keys and not any(k.startswith('/api/') for k in keys)
                    offline.set_offline(True);tab.goto(base+'/privacy/');assert tab.locator('h1').inner_text()=='Privacy policy'
                    report[-1]['offline_policy_shell']='pass, no API cache'
                print('Passed',engine.name,flush=True);browser.close()
    finally:
        for server in (front,back):server.shutdown();server.server_close()
Path('artifacts/free-launch').mkdir(parents=True,exist_ok=True)
Path('artifacts/free-launch/export-browser.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
