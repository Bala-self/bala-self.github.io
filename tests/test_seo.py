"""SEO contract checks. pocket.test is an isolated fixture, never the site's production URL."""
import base64
import hashlib
import json
import sys
from pathlib import Path
from urllib.parse import urlparse
from xml.etree import ElementTree as ET
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import app as m
import seo
import pytest
from bs4 import BeautifulSoup
from fastapi.testclient import TestClient

@pytest.fixture
def prod(monkeypatch):
    monkeypatch.setattr(seo, 'SITE_ORIGIN', 'https://pocket.test')
    monkeypatch.setattr(seo, 'INDEXING_ENABLED', True)
    with TestClient(m.app, base_url='https://pocket.test') as c:
        yield c

@pytest.mark.parametrize('value', ['', 'http://pocket.com', 'https://example.com', 'https://pocket.example.com', 'https://localhost', 'https://127.0.0.1', 'https://user:pass@pocket.com', 'https://pocket.com/path', 'https://pocket.com?x=1', 'https://pocket.com:8443', 'https://pocket.invalid', 'https://pocket.test', 'https://pocket.com/#frag'])
def test_invalid_or_placeholder_production_origin(value):
    assert seo.validated_origin(value) == ''

@pytest.mark.parametrize('value', ['https://pocket-download.com', 'https://www.pocket-download.com/', 'https://POCKET-DOWNLOAD.COM:443'])
def test_origin_validation(value):
    assert seo.validated_origin(value) == value.lower().rstrip('/').replace(':443', '')

@pytest.mark.parametrize('path', seo.PUBLIC_PATHS)
def test_public_metadata_and_head(prod,path):
    response=prod.get(path);s=BeautifulSoup(response.text,'html.parser')
    assert response.status_code==200
    assert prod.head(path).status_code==200 and prod.head(path).content==b''
    assert len(s.select('title'))==len(s.select('meta[name="description"]'))==len(s.select('link[rel="canonical"]'))==1
    assert s.title.text==seo.PAGES[path]['title']
    assert s.select_one('link[rel="canonical"]')['href']=='https://pocket.test'+path
    assert s.select_one('meta[name="robots"]')['content']=='index, follow'
    assert 'noindex' not in response.headers.get('x-robots-tag','')
    assert len(s.select('h1'))==1
    assert s.select_one('meta[property="og:url"]')['content']=='https://pocket.test'+path
    assert s.select_one('meta[property="og:image"]')['content']=='https://pocket.test/social-card.png'
    assert s.select_one('meta[name="twitter:card"]')['content']=='summary_large_image'
    assert '__SEO_HEAD__' not in response.text
    assert prod.get('/social-card.png').status_code==200

def test_unique_pages_and_no_js_policy_dependency(prod):
    titles=[];descriptions=[];bodies=[]
    for path in seo.PUBLIC_PATHS:
        s=BeautifulSoup(prod.get(path).text,'html.parser')
        titles.append(s.title.text);descriptions.append(s.select_one('meta[name="description"]')['content']);bodies.append(s.select_one('main').text)
        if path!='/':
            assert not s.select('dialog')
            assert not s.select('script[src*="app.js"]')
            assert s.select_one('.policy-content h2')
            assert s.select_one('.policy-content').get_text().find('October 15, 2026')>=0
    assert len(set(titles))==len(set(descriptions))==len(set(bodies))==3

def test_sitemap_and_robots(prod):
    r=prod.get('/sitemap.xml');root=ET.fromstring(r.text)
    locations=[n.text for n in root.findall('{*}url/{*}loc')]
    assert r.status_code==200 and set(locations)=={'https://pocket.test'+p for p in seo.PUBLIC_PATHS}
    assert len(locations)==3 and not root.findall('{*}url/{*}lastmod')
    for u in locations:
        r=prod.get(urlparse(u).path);assert r.status_code==200 and 'noindex' not in r.headers.get('x-robots-tag','')
    robots=prod.get('/robots.txt')
    assert robots.status_code==200 and 'Sitemap: https://pocket.test/sitemap.xml' in robots.text
    assert 'Disallow:' not in robots.text
    assert prod.head('/sitemap.xml').status_code==prod.head('/robots.txt').status_code==200

@pytest.mark.parametrize('enabled', [True,False])
def test_preview_safety(monkeypatch,enabled):
    monkeypatch.setattr(seo,'SITE_ORIGIN','' if enabled else 'https://pocket.test')
    monkeypatch.setattr(seo,'INDEXING_ENABLED',enabled)
    with TestClient(m.app,base_url='https://pocket.test') as c:
        for path in seo.PUBLIC_PATHS:
            r=c.get(path);s=BeautifulSoup(r.text,'html.parser')
            assert 'noindex' in r.headers['x-robots-tag']
            assert s.select_one('meta[name="robots"]')['content']=='noindex, follow'
            if enabled: assert not s.select('link[rel="canonical"]') and not s.select('script[type="application/ld+json"]')
        assert c.get('/sitemap.xml').status_code==503
        assert 'Sitemap:' not in c.get('/robots.txt').text

@pytest.mark.parametrize('old,new', [('/index.html','/'),('/ops.html','/ops'),('/terms/','/terms'),('/privacy/','/privacy'),('/ops/','/ops')])
def test_known_duplicates_one_hop(prod,old,new):
    r=prod.get(old,follow_redirects=False)
    assert r.status_code==308 and r.headers['location']==new
    assert prod.get(r.headers['location'],follow_redirects=False).status_code==200

def test_host_https_and_path_normalized_together(prod):
    r=prod.get('http://other.test/privacy/?utm_source=x',follow_redirects=False)
    assert r.status_code==308 and r.headers['location']=='https://pocket.test/privacy?utm_source=x'
    s=BeautifulSoup(prod.get(r.headers['location']).text,'html.parser')
    assert s.select_one('link[rel="canonical"]')['href']=='https://pocket.test/privacy'

def test_no_forwarded_header_trust(prod):
    r=prod.get('http://pocket.test/',headers={'X-Forwarded-Proto':'https','X-Forwarded-Host':'evil.test'},follow_redirects=False)
    assert r.status_code==308 and r.headers['location']=='https://pocket.test/'

def test_trusted_proxy_no_loop(prod,monkeypatch):
    monkeypatch.setenv('TRUST_PROXY_IPS','testclient')
    r=prod.get('http://pocket.test/',headers={'X-Forwarded-Proto':'https'},follow_redirects=False)
    assert r.status_code==200

def test_queries_canonicalize_without_breaking_share_target(prod):
    for suffix in ['?utm_source=x','?url=https%3A%2F%2Fwww.instagram.com%2Freel%2FABCDEF%2F','?shared=example']:
        r=prod.get('/'+suffix,follow_redirects=False);s=BeautifulSoup(r.text,'html.parser')
        assert r.status_code==200 and s.select_one('link[rel="canonical"]')['href']=='https://pocket.test/'
    manifest=prod.get('/manifest.webmanifest').json()
    assert manifest['share_target']['params']['url']=='url'

@pytest.mark.parametrize('path', ['/ops','/api/health','/api/metrics','/api/download?token=invalid','/api/preview?token=invalid'])
def test_utility_not_indexable(prod,path):
    r=prod.get(path);assert 'noindex' in r.headers['x-robots-tag'] and r.headers['cache-control']=='no-store'

@pytest.mark.parametrize('path', ['/no-such-page','/policy.html','/404.html','/openapi.json','/docs','/reels/no-such-page'])
def test_true_404_not_soft_404(prod,path):
    r=prod.get(path);s=BeautifulSoup(r.text,'html.parser')
    assert r.status_code==404 and 'noindex' in r.headers['x-robots-tag']
    assert s.select_one('h1') and 'got away' in s.select_one('h1').text
    assert not s.select('link[rel="canonical"]')

@pytest.mark.parametrize('path', seo.PUBLIC_PATHS)
def test_structured_data_and_csp_hash(prod,path):
    r=prod.get(path);s=BeautifulSoup(r.text,'html.parser');scripts=s.select('script[type="application/ld+json"]')
    assert len(scripts)==1
    text=scripts[0].string;data=json.loads(text)
    assert data['@context']=='https://schema.org'
    types={n['@type'] for n in data['@graph']}
    assert types==({'WebSite','WebPage'} if path=='/' else {'WebPage','BreadcrumbList'})
    assert not any(k in r.text for k in ['aggregateRating','reviewCount','SearchAction'])
    digest=base64.b64encode(hashlib.sha256(text.encode()).digest()).decode()
    assert "'sha256-"+digest+"'" in r.headers['content-security-policy']
    if path!='/':
        assert s.select_one('[aria-label="Breadcrumb"]')
        items=next(x for x in data['@graph'] if x['@type']=='BreadcrumbList')['itemListElement']
        assert [x['position'] for x in items]==[1,2]
        assert items[-1]['item']=='https://pocket.test'+path

def test_crawlable_internal_links_and_resources(prod):
    for path in seo.PUBLIC_PATHS:
        s=BeautifulSoup(prod.get(path).text,'html.parser')
        for a in s.select('a[href]'):
            href=a['href']
            if href.startswith('#'):
                assert s.find(id=href[1:]) is not None
            elif href.startswith('/'):
                assert prod.get(href,follow_redirects=False).status_code==200
        for node in s.select('script[src],link[rel="stylesheet"],link[rel="icon"],link[rel="apple-touch-icon"],img[src]'):
            assert prod.get(node.get('src') or node['href']).status_code==200

def test_compression_cache_and_token_stream_exclusion(prod):
    r=prod.get('/',headers={'Accept-Encoding':'gzip'})
    assert r.headers['content-encoding']=='gzip' and 'accept-encoding' in r.headers['vary'].lower()
    assert r.headers['cache-control']=='no-cache'
    for name in seo.ASSET_NAMES:
        r=prod.get(seo.asset_url(name));assert r.status_code==200 and 'immutable' in r.headers['cache-control']
        assert 'immutable' not in prod.get('/'+name+'?v=wrong').headers['cache-control']
    r=prod.get('/api/health',headers={'Accept-Encoding':'gzip'})
    assert 'content-encoding' not in r.headers
    assert prod.get('/ops').headers['cache-control']=='no-store'

def test_service_worker_version_and_privacy(prod):
    r=prod.get('/sw.js');text=r.text
    assert r.status_code==200 and '__BUILD_ID__' not in text and '__SHELL_JSON__' not in text
    assert seo.BUILD_ID in text and seo.asset_url('theme.js') in text
    assert "url.pathname.startsWith('/api/')" in text
    assert 'cache:\'reload\'' in text and r.headers['cache-control']=='no-cache'

def test_optional_verification_tokens(prod,monkeypatch):
    monkeypatch.setenv('GOOGLE_SITE_VERIFICATION','test-verification-token')
    monkeypatch.setenv('BING_SITE_VERIFICATION','123456789ABC')
    s=BeautifulSoup(prod.get('/').text,'html.parser')
    assert s.select_one('meta[name="google-site-verification"]')['content']=='test-verification-token'
    assert s.select_one('meta[name="msvalidate.01"]')['content']=='123456789ABC'
    assert 'test-verification-token' not in prod.get('/terms').text


def test_hashed_inline_theme_not_extra_blocking_request(prod):
    r=prod.get('/');s=BeautifulSoup(r.text,'html.parser')
    inline=next(n.string for n in s.select('script:not([src])') if 'localStorage' in (n.string or ''))
    digest=base64.b64encode(hashlib.sha256(inline.encode()).digest()).decode()
    assert "'sha256-"+digest+"'" in r.headers['content-security-policy']
    assert not s.select('script[src*="theme.js"]')

def test_accurate_download_and_rights_disclosures(prod):
    home=BeautifulSoup(prod.get('/').text,'html.parser').get_text(' ',strip=True)
    terms=BeautifulSoup(prod.get('/terms').text,'html.parser').get_text(' ',strip=True)
    privacy=BeautifulSoup(prod.get('/privacy').text,'html.parser').get_text(' ',strip=True)
    assert 'No added watermark' in home
    assert 'Files pass through this server' in home
    assert 'does not remove marks already present' in home
    assert 'or redistribute posts' not in home
    assert 'Instagram restricts automated access' in terms
    assert 'This technical design does not itself grant copyright permission' in terms
    assert 'about one hour' in privacy
