import asyncio
import contextlib
import json
import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import app as m
import httpx
import pytest
from fastapi.testclient import TestClient

@pytest.fixture(autouse=True)
def reset():
    m.cache.clear(); m.tokens.clear(); m.buckets.clear(); m.locks.clear()
    for stat in m.metrics.values():
        for key in stat: stat[key] = 0
    m.active_downloads = 0
    m.runtime_flags.clear()

@pytest.mark.parametrize('path,kind', [('p/ABC_def-1','p'),('reel/ABC_def-1','reel'),('reels/ABC_def-1','reel'),('tv/ABC_def-1','tv'),('stories/alice/123456789','story'),('stories/highlights/123456789','highlight')])
def test_parse_supported(path,kind):
    t=m.parse_url('https://www.instagram.com/'+path+'/?utm_source=test')
    assert t.kind == kind and '?' not in t.url

@pytest.mark.parametrize('url', ['http://www.instagram.com/p/ABCDEF/', 'https://instagram.com.evil.org/p/ABCDEF/', 'https://instagram.com@evil.org/p/ABCDEF/', 'https://evil.org/p/ABCDEF/', 'https://127.0.0.1/p/ABCDEF/', 'https://instagram.com:8080/p/ABCDEF/', 'https://instagram.com/accounts/login/', 'https://instagram.com/alice/', 'https://instagram.com/p/../../etc/passwd', 'file:///etc/passwd', 'https://instagram.com/p/a/', 'https://instagram.com/p/ABCDEF/extra', 'https://user:pass@instagram.com/p/ABCDEF/'])
def test_reject_unsafe_inputs(url):
    with pytest.raises(m.ResolveError) as exc: m.parse_url(url)
    assert exc.value.status == 400

@pytest.mark.parametrize('host,ok', [('scontent.cdninstagram.com',True),('video.xx.fbcdn.net',True),('www.instagram.com',True),('evilinstagram.com',False),('instagram.com.evil.org',False),('localhost',False),('127.0.0.1',False)])
def test_media_allowlist(host,ok): assert m.allowed_host(host) == ok

@pytest.mark.asyncio
async def test_reject_private_dns(monkeypatch):
    async def lookup(*a,**k): return [(2,1,6,'',('127.0.0.1',443))]
    monkeypatch.setattr(asyncio.get_running_loop(),'getaddrinfo',lookup)
    with pytest.raises(m.ResolveError): await m.safe_url('https://www.instagram.com/p/ABCDEF/')

@pytest.mark.asyncio
async def test_fallback_order(monkeypatch):
    calls=[]
    async def fail(t): calls.append('B'); raise m.ResolveError()
    async def ok(t): calls.append('A'); return m.Media('image',groups=[[m.Asset('https://a.cdninstagram.com/a.jpg','jpg','Original')]])
    monkeypatch.setattr(m,'method_ytdlp',fail);monkeypatch.setattr(m,'method_html',ok)
    result,method=await m.cascade(m.parse_url('https://instagram.com/p/ABCDEF/'))
    assert calls==['B','A'] and method=='html' and result.kind=='image'

@pytest.mark.asyncio
async def test_browser_fallback(monkeypatch):
    calls=[]
    async def fail(t): calls.append('fail');raise m.ResolveError()
    async def ok(t): calls.append('C');return m.Media('video',groups=[[m.Asset('https://x.fbcdn.net/a.mp4','mp4','Original')]])
    monkeypatch.setattr(m,'BROWSER',True);monkeypatch.setattr(m,'method_ytdlp',fail);monkeypatch.setattr(m,'method_html',fail);monkeypatch.setattr(m,'method_browser',ok)
    _,method=await m.cascade(m.parse_url('https://instagram.com/reel/ABCDEF/'))
    assert calls==['fail','fail','C'] and method=='browser'

@pytest.mark.asyncio
async def test_rate_limit_does_not_evade(monkeypatch):
    async def blocked(t): raise m.ResolveError('rate_limited','Wait',429,60)
    async def forbidden(t): pytest.fail('Must not fall through upstream 429')
    monkeypatch.setattr(m,'method_ytdlp',blocked);monkeypatch.setattr(m,'method_html',forbidden)
    with pytest.raises(m.ResolveError) as exc: await m.cascade(m.parse_url('https://instagram.com/p/ABCDEF/'))
    assert exc.value.status==429

def test_carousel_html():
    data={'owner':{'username':'creator'},'edge_sidecar_to_children':{'edges':[{'node':{'display_url':'https://x.cdninstagram.com/a.jpg'}},{'node':{'video_url':'https://x.fbcdn.net/b.mp4'}}]}}
    html='<script type="application/json">'+json.dumps(data)+'</script>'
    media=m.parse_html(html)
    assert media.kind=='carousel' and len(media.groups)==2
    assert [g[0].ext for g in media.groups]==['jpg','mp4']

def test_jsonld_video():
    media=m.parse_html('<script type="application/ld+json">{"@type":"VideoObject","contentUrl":"https://x.fbcdn.net/a.mp4","author":{"name":"alice"}}</script>')
    assert media.kind=='video' and media.author=='alice'

def test_generic_og_image_not_a_result():
    with pytest.raises(m.ResolveError):m.parse_html('<meta property="og:image" content="https://x.fbcdn.net/generic.jpg">')

def test_private_json():
    with pytest.raises(m.ResolveError) as exc:m.parse_html('<script type="application/json">{"is_private":true}</script>')
    assert exc.value.code=='private'

def test_contract_cache_and_no_cdn_exposure(monkeypatch):
    count=0
    async def fake(target):
        nonlocal count
        count+=1
        return m.Media('image',author='alice',caption='<script>alert(1)</script>',thumbnail='https://x.fbcdn.net/a.jpg',groups=[[m.Asset('https://x.fbcdn.net/a.jpg','jpg','Original')]]),'html'
    monkeypatch.setattr(m,'cascade',fake)
    with TestClient(m.app) as c:
        a=c.post('/api/resolve',json={'url':'https://instagram.com/p/ABCDEF/'});b=c.post('/api/resolve',json={'url':'https://instagram.com/p/ABCDEF/'})
        assert a.status_code==b.status_code==200 and count==1
        data=a.json();assert data['items'][0]['url'].startswith('/api/download?token=')
        assert 'fbcdn.net' not in a.text and data['items'][0]['id']=='0'
        assert c.get('/api/download?token=not-real').status_code==410

def test_token_expiry():
    a=m.Asset('https://x.fbcdn.net/a.jpg','jpg','Original');path=m.issue(a,'photo.jpg');token=path.split('=')[1]
    entry=m.tokens[token];m.tokens[token]=(time.monotonic()-1,*entry[1:])
    with TestClient(m.app) as c: assert c.get(path).status_code==410

def test_stream_attachment(monkeypatch):
    payload=b'\xff\xd8jpeg-test'
    @contextlib.asynccontextmanager
    async def fake(*a,**k):
        yield httpx.Response(200,headers={'content-type':'image/jpeg','content-length':str(len(payload))},content=payload)
    monkeypatch.setattr(m,'upstream',fake)
    path=m.issue(m.Asset('https://x.fbcdn.net/a.jpg','jpg','Original'),'pocket-photo.jpg')
    with TestClient(m.app) as c:
        r=c.get(path);assert r.status_code==200 and r.content==payload
        assert r.headers['content-disposition']=='attachment; filename="pocket-photo.jpg"'
        assert m.active_downloads==0

def test_no_html_download(monkeypatch):
    @contextlib.asynccontextmanager
    async def fake(*a,**k):yield httpx.Response(200,headers={'content-type':'text/html'},content=b'login')
    monkeypatch.setattr(m,'upstream',fake)
    path=m.issue(m.Asset('https://x.fbcdn.net/a.mp4','mp4','Original'),'video.mp4')
    with TestClient(m.app) as c:assert c.get(path).status_code==502
    assert m.active_downloads==0

def test_burst_and_cors():
    with TestClient(m.app) as c:
        assert c.post('/api/resolve',headers={'Origin':'https://evil.test'},json={'url':'x'}).status_code==403
        codes=[c.post('/api/resolve',json={'url':'not-a-url'}).status_code for _ in range(20)]
        assert codes.count(400)==12 and codes.count(429)==8
        assert c.get('/api/metrics').status_code==404
        assert c.get('/api/health').status_code==200
        assert c.get('/').headers['x-content-type-options']=='nosniff'

@pytest.mark.asyncio
async def test_circuit_opens_after_failures(monkeypatch):
    async def fail(t):raise m.ResolveError()
    monkeypatch.setattr(m,'method_ytdlp',fail);monkeypatch.setattr(m,'method_html',fail)
    for i in range(6):
        with pytest.raises(m.ResolveError):await m.cascade(m.parse_url('https://instagram.com/p/ABCDEF/'))
    assert m.metrics['ytdlp']['failure']==5 and m.metrics['ytdlp']['open_until']>time.monotonic()

@pytest.mark.asyncio
async def test_keyed_lock_coalesces_and_releases():
    running=0;maximum=0
    async def task():
        nonlocal running,maximum
        async with m.keyed_lock('same'):
            running+=1;maximum=max(maximum,running)
            await asyncio.sleep(.001)
            running-=1
    await asyncio.gather(*(task() for _ in range(20)))
    assert maximum==1 and not m.locks

def test_audio_conversion_real_ffmpeg(monkeypatch,tmp_path):
    import shutil,subprocess
    if not shutil.which('ffmpeg'):pytest.skip('ffmpeg not installed')
    path=tmp_path/'tone.mp4'
    subprocess.run(['ffmpeg','-nostdin','-v','error','-f','lavfi','-i','color=c=green:s=64x64:d=0.3','-f','lavfi','-i','sine=frequency=440:duration=0.3','-c:v','libx264','-c:a','aac','-shortest',str(path)],check=True)
    @contextlib.asynccontextmanager
    async def fake(*a,**k):yield httpx.Response(200,headers={'content-type':'video/mp4'},content=path.read_bytes())
    monkeypatch.setattr(m,'upstream',fake)
    link=m.issue(m.Asset('https://x.fbcdn.net/a.mp4','mp4','Original'),'audio.mp3','audio')
    with TestClient(m.app) as c:
        r=c.get(link);assert r.status_code==200 and r.headers['content-type']=='audio/mpeg'
        assert r.content[:3]==b'ID3' and m.active_downloads==0


def test_admin_flags_require_auth(monkeypatch):
    monkeypatch.setenv('METRICS_TOKEN','unit-test-secret')
    with TestClient(m.app) as c:
        assert c.patch('/api/admin/engines',json={'ytdlp':False}).status_code==404
        headers={'Authorization':'Bearer unit-test-secret'}
        assert c.patch('/api/admin/engines',headers=headers,json={'ytdlp':False}).json()['engines']['ytdlp'] is False
        assert c.get('/api/metrics',headers=headers).json()['methods']['ytdlp']['enabled'] is False
        assert c.get('/api/health').json()['engines']['ytdlp'] is False

def test_media_range_passthrough(monkeypatch):
    @contextlib.asynccontextmanager
    async def fake(url,timeout=25,byte_range=None):
        assert byte_range=='bytes=0-1'
        yield httpx.Response(206,headers={'content-type':'video/mp4','content-length':'2','content-range':'bytes 0-1/200','accept-ranges':'bytes'},content=b'00')
    monkeypatch.setattr(m,'upstream',fake)
    path=m.issue(m.Asset('https://x.fbcdn.net/a.mp4','mp4','Original'),'clip.mp4')
    with TestClient(m.app) as c:
        r=c.get(path,headers={'Range':'bytes=0-1'})
        assert r.status_code==206 and r.content==b'00' and r.headers['content-range']=='bytes 0-1/200'
