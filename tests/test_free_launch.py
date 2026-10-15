"""Free profile tests are local simulations, not a live GitHub/Render deployment claim."""
import base64
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from xml.etree import ElementTree as ET
import pytest
from bs4 import BeautifulSoup
from fastapi.testclient import TestClient
import app as m
ROOT=Path(__file__).resolve().parents[1]

@pytest.fixture(scope='module')
def exported(tmp_path_factory):
    out=tmp_path_factory.mktemp('export')/'site'
    subprocess.run([sys.executable,'scripts/export_pages.py','--site-origin','https://pocket-export-fixture.github.io','--backend-origin','https://pocket-export-fixture.onrender.com','--output',str(out),'--google-token','fixture-verification-token'],cwd=ROOT,check=True,capture_output=True,text=True)
    return out

def test_static_export_has_real_html_and_no_runtime_backend_code(exported):
    for name in ('index.html','privacy/index.html','terms/index.html','404.html','robots.txt','sitemap.xml','sw.js','client-config.js','.nojekyll'):
        assert (exported/name).is_file()
    assert not (exported/'app.py').exists() and not (exported/'.env').exists() and not (exported/'ops.html').exists()
    for path in ('index.html','privacy/index.html','terms/index.html'):
        text=(exported/path).read_text();s=BeautifulSoup(text,'html.parser')
        assert '__SEO_HEAD__' not in text and '__THEME_SCRIPT__' not in text and s.select_one('h1')
        assert s.select_one('meta[name="robots"]')['content']=='index, follow'
        assert 'fixture-verification-token' in text if path=='index.html' else 'fixture-verification-token' not in text
        csp=s.select_one('meta[http-equiv="Content-Security-Policy"]')['content']
        assert 'connect-src \'self\' https://pocket-export-fixture.onrender.com' in csp
        for script in s.select('script:not([src])'):
            digest=base64.b64encode(hashlib.sha256(script.string.encode()).digest()).decode()
            assert "'sha256-"+digest+"'" in csp

def test_static_policy_urls_and_sitemap_match_pages_directories(exported):
    expected={'https://pocket-export-fixture.github.io/','https://pocket-export-fixture.github.io/privacy/','https://pocket-export-fixture.github.io/terms/'}
    tree=ET.fromstring((exported/'sitemap.xml').read_text())
    assert {n.text for n in tree.findall('{*}url/{*}loc')}==expected
    for path in ('privacy/index.html','terms/index.html'):
        s=BeautifulSoup((exported/path).read_text(),'html.parser')
        assert s.select_one('link[rel="canonical"]')['href'].endswith('/'+path.split('/')[0]+'/')
        data=json.loads(s.select_one('script[type="application/ld+json"]').string)
        for n in data['@graph']:
            if n['@type']=='WebPage':assert n['url'].endswith('/') and '/#webpage' in n['@id']
    assert 'Disallow: /' not in (exported/'robots.txt').read_text()
    assert 'Sitemap: https://pocket-export-fixture.github.io/sitemap.xml' in (exported/'robots.txt').read_text()

def test_static_backend_config_and_service_worker(exported):
    assert 'https://pocket-export-fixture.onrender.com' in (exported/'client-config.js').read_text()
    worker=(exported/'sw.js').read_text()
    assert '__BUILD_ID__' not in worker and '__SHELL_JSON__' not in worker
    assert 'client-config.js?v=' in worker and '"/privacy/"' in worker
    assert "url.pathname.startsWith('/api/')" in worker
    manifest=json.loads((exported/'manifest.webmanifest').read_text())
    assert manifest['share_target']['action']=='/'

@pytest.mark.parametrize('site,backend', [
    ('https://pocket-export-fixture.github.io/project','https://pocket-export-fixture.onrender.com'),
    ('https://example.com','https://pocket-export-fixture.onrender.com'),
    ('https://pocket-export-fixture.github.io','http://pocket-export-fixture.onrender.com'),
    ('https://pocket-export-fixture.github.io','https://user:pass@pocket-export-fixture.onrender.com'),
])
def test_export_rejects_invalid_configuration(tmp_path,site,backend):
    r=subprocess.run([sys.executable,'scripts/export_pages.py','--site-origin',site,'--backend-origin',backend,'--output',str(tmp_path/'site')],cwd=ROOT,capture_output=True,text=True)
    assert r.returncode!=0

def test_chunked_request_body_limit():
    with TestClient(m.app) as c:
        def chunks():
            for _ in range(20):yield b'x'*1024
        r=c.post('/api/resolve',content=chunks(),headers={'content-type':'application/json'})
        assert r.status_code==413

def test_cross_origin_profile_security_in_fresh_process():
    code='''
from fastapi.testclient import TestClient
import app
with TestClient(app.app,base_url='https://pocket-export-fixture.onrender.com') as c:
    pre=c.options('/api/resolve',headers={'Origin':'https://pocket-export-fixture.github.io','Access-Control-Request-Method':'POST','Access-Control-Request-Headers':'Content-Type'})
    assert pre.status_code==200 and pre.headers['access-control-allow-origin']=='https://pocket-export-fixture.github.io'
    r=c.post('/api/resolve',json={'url':'invalid'},headers={'Origin':'https://pocket-export-fixture.github.io'})
    assert r.status_code==400 and r.headers['access-control-allow-origin']=='https://pocket-export-fixture.github.io'
    r=c.post('/api/resolve',json={'url':'invalid'},headers={'Origin':'https://evil.invalid'})
    assert r.status_code==403 and 'access-control-allow-origin' not in r.headers
    r=c.get('/api/download?token=missing',headers={'Origin':'https://pocket-export-fixture.github.io'})
    assert r.status_code==410 and r.headers['access-control-allow-origin']=='https://pocket-export-fixture.github.io'
    assert r.headers['cache-control']=='no-store'
    assert c.get('/ops',follow_redirects=False).status_code==200
    for path in ('/ops.js','/style.css','/theme.js','/icon.svg'):
        assert c.get(path,follow_redirects=False).status_code==200
    r=c.get('/',follow_redirects=False)
    assert r.status_code==308 and r.headers['location']=='https://pocket-export-fixture.github.io/'
    r=c.options('/api/admin/engines',headers={'Origin':'https://pocket-export-fixture.github.io','Access-Control-Request-Method':'PATCH'})
    assert r.status_code==400
'''
    env={**os.environ,'PUBLIC_ORIGIN':'https://POCKET-EXPORT-FIXTURE.github.io:443/','SEO_INDEXING_ENABLED':'false','ENABLE_CROSS_ORIGIN':'true'}
    r=subprocess.run([sys.executable,'-c',code],cwd=ROOT,env=env,capture_output=True,text=True)
    assert r.returncode==0,r.stdout+r.stderr
