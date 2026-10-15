"""Export only public UI to an origin-root GitHub Pages site. No secrets in output.
Usage: python scripts/export_pages.py --site-origin https://USERNAME.github.io \
       --backend-origin https://YOUR-SERVICE.onrender.com --output .pages-site
"""
import argparse
import hashlib
import html
import json
import os
import re
import shutil
import sys
from pathlib import Path
from urllib.parse import urlparse

ROOT=Path(__file__).resolve().parents[1]

def validate_origin(value,label):
    p=urlparse(value.strip())
    if (p.scheme!='https' or not p.hostname or p.username or p.password or p.port not in (None,443)
            or p.path not in ('','/') or p.query or p.fragment):
        raise ValueError(label+' must be an exact HTTPS origin, with no path, query or credentials.')
    host=p.hostname.lower()
    if len(host)>253 or not all(re.fullmatch(r'[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?',label) for label in host.split('.')):
        raise ValueError(label+' contains an invalid hostname.')
    return 'https://'+host

def export(site,backend,output,google='',bing=''):
    site=validate_origin(site,'Site URL');backend=validate_origin(backend,'Backend URL')
    host=urlparse(site).hostname
    if not re.fullmatch(r'[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.github\.io',host):
        raise ValueError('Use your origin-root USERNAME.github.io site, not a project /repository path.')
    if backend==site or not backend.endswith('.onrender.com'):
        raise ValueError('This free preset expects your exact HTTPS .onrender.com service origin.')
    output=Path(output).resolve()
    if output==ROOT or output in ROOT.parents or output==ROOT/'static' or output==ROOT/'content' or any(base in output.parents for base in (ROOT/'static',ROOT/'content')):
        raise ValueError('Choose a dedicated export folder, not the source directory.')
    if output.exists() and any(output.iterdir()) and not (output/'.pocket-export').exists():
        raise ValueError('Refusing to overwrite a non-empty folder not created by this exporter.')
    os.environ['PUBLIC_ORIGIN']=site;os.environ['SEO_INDEXING_ENABLED']='true'
    os.environ['GOOGLE_SITE_VERIFICATION']=google;os.environ['BING_SITE_VERIFICATION']=bing
    sys.path.insert(0,str(ROOT))
    import seo
    if not seo.SITE_ORIGIN:raise ValueError('Invalid public site origin.')
    # Set explicitly as this function is also used by isolated exporter tests.
    seo.SITE_ORIGIN=site;seo.INDEXING_ENABLED=True
    output.mkdir(parents=True,exist_ok=True)
    if (output/'.pocket-export').exists():
        for p in output.iterdir():
            if p.is_dir():shutil.rmtree(p)
            else:p.unlink()
    (output/'.pocket-export').write_text('Generated public frontend only. Never copy .env here.\n')
    for name in seo.ASSET_NAMES:
        if name!='ops.js':shutil.copyfile(ROOT/'static'/name,output/name)
    config='// Public endpoint only; no passwords, cookies or tokens.\nwindow.POCKET_API_BASE = '+json.dumps(backend)+';\n'
    (output/'client-config.js').write_text(config)
    seo.ASSET_HASHES['client-config.js']=hashlib.sha256(config.encode()).hexdigest()[:12]
    seo.BUILD_ID=hashlib.sha256((seo.BUILD_ID+site+backend+google+bing).encode()).hexdigest()[:12]
    def slash_policies(text):
        # GitHub Pages directory routes canonically include a trailing slash.
        for path in ('/privacy','/terms'):
            text=text.replace(site+path+'#',site+path+'/#')
            text=text.replace(site+path+'"',site+path+'/"')
            text=text.replace('href="'+path+'"','href="'+path+'/"')
        return text
    def prepare(text):
        text=slash_policies(text)
        match=re.search(r'<script type="application/ld\+json">(.*?)</script>',text,re.S)
        policy=seo.csp(match[1] if match else None)
        policy=policy.replace("frame-ancestors 'none'; ", '')  # Not supported in a CSP meta tag.
        policy=policy.replace("connect-src 'self';",f"connect-src 'self' {backend};")
        policy=policy.replace("img-src 'self' data: blob:;",f"img-src 'self' data: blob: {backend};")
        policy=policy.replace("media-src 'self' blob:;",f"media-src 'self' blob: {backend};")
        # GitHub Pages cannot set custom HTTP headers; meta CSP still protects the document.
        meta='<meta name="referrer" content="no-referrer"><meta http-equiv="Content-Security-Policy" content="'+html.escape(policy,quote=True)+'">'
        return text.replace('<meta charset="utf-8">','<meta charset="utf-8">'+meta,1)
    for path in seo.PUBLIC_PATHS:
        dest=output/('index.html' if path=='/' else path[1:]+'/index.html')
        dest.parent.mkdir(parents=True,exist_ok=True)
        dest.write_text(prepare(seo.render_page(path).body.decode()))
    (output/'404.html').write_text(prepare(seo.not_found().body.decode()))
    sitemap=seo.sitemap_response().body.decode()
    for path in ('/privacy','/terms'):sitemap=sitemap.replace(site+path+'</loc>',site+path+'/</loc>')
    (output/'sitemap.xml').write_text(sitemap)
    (output/'robots.txt').write_text(seo.robots_response().body.decode())
    manifest=json.loads((ROOT/'static/manifest.webmanifest').read_text())
    for icon in manifest['icons']:icon['src']=seo.asset_url(icon['src'].lstrip('/'))
    (output/'manifest.webmanifest').write_text(json.dumps(manifest))
    worker=seo.service_worker().body.decode()
    for path in ('/privacy','/terms'):worker=worker.replace(json.dumps(path),json.dumps(path+'/'))
    (output/'sw.js').write_text(worker)
    (output/'.nojekyll').write_text('')
    return output

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--site-origin',required=True);parser.add_argument('--backend-origin',required=True)
    parser.add_argument('--output',default='.pages-site');parser.add_argument('--google-token',default='');parser.add_argument('--bing-token',default='')
    args=parser.parse_args()
    try:
        out=export(args.site_origin,args.backend_origin,args.output,args.google_token,args.bing_token)
    except ValueError as exc:parser.error(str(exc))
    print('Public frontend exported to',out)
