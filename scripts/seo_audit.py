"""Repeatable local/public crawl. No rankings, field CWV, ownership or indexing claims.
Usage: python scripts/seo_audit.py [https://your-real-domain] [output.json]
"""
import json
import sys
from pathlib import Path
from urllib.parse import urljoin, urlparse
import httpx
from bs4 import BeautifulSoup

base=(sys.argv[1] if len(sys.argv)>1 else 'http://127.0.0.1:8000').rstrip('/')
output=Path(sys.argv[2] if len(sys.argv)>2 else 'artifacts/seo/final-crawl.json')
paths=['/','/privacy','/terms','/ops','/index.html','/ops.html','/privacy/','/terms/','/robots.txt','/sitemap.xml','/openapi.json','/not-a-real-page','/?utm_source=audit','/?url=https%3A%2F%2Fwww.instagram.com%2Freel%2FABCDEF%2F']
report={'base_url':base,'mode':'live HTTP crawl, not Search Console/indexing verification','routes':[],'broken_internal_links':[],'broken_resources':[]}
with httpx.Client(base_url=base,follow_redirects=False,timeout=20) as client:
    for path in paths:
        r=client.get(path);is_html='text/html' in r.headers.get('content-type','');s=BeautifulSoup(r.text,'html.parser') if is_html else None
        row={'path':path,'status':r.status_code,'head_status':client.head(path).status_code,'location':r.headers.get('location'),'title':s.title.text if s and s.title else None,'description':[n.get('content') for n in s.select('meta[name="description"]')] if s else [],'h1':[n.get_text(' ',strip=True) for n in s.select('h1')] if s else [],'canonical':[n.get('href') for n in s.select('link[rel="canonical"]')] if s else [],'robots_meta':[n.get('content') for n in s.select('meta[name="robots"]')] if s else [],'x_robots_tag':r.headers.get('x-robots-tag'),'content_type':r.headers.get('content-type'),'content_encoding':r.headers.get('content-encoding'),'cache_control':r.headers.get('cache-control'),'decoded_bytes':len(r.content),'content_length':r.headers.get('content-length')}
        report['routes'].append(row)
        if path not in ['/','/privacy','/terms'] or not s:continue
        for a in s.select('a[href]'):
            href=a['href']
            if href.startswith('#'):
                if not s.find(id=href[1:]):report['broken_internal_links'].append({'page':path,'href':href,'reason':'missing fragment'})
            elif href.startswith('/'):
                result=client.get(href)
                if result.status_code!=200:report['broken_internal_links'].append({'page':path,'href':href,'status':result.status_code})
        for asset in s.select('script[src],link[rel="stylesheet"],link[rel="icon"],link[rel="apple-touch-icon"],img[src]'):
            src=asset.get('src') or asset['href'];result=client.get(src)
            if result.status_code!=200:report['broken_resources'].append({'page':path,'src':src,'status':result.status_code})
output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
if report['broken_internal_links'] or report['broken_resources']:sys.exit(1)
