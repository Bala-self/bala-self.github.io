"""Server-rendered public documents and conservative, configuration-driven SEO.

Never derive a canonical from an untrusted Host/X-Forwarded-Host header. No production
hostname is shipped: without a valid PUBLIC_ORIGIN the site is an explicitly noindex preview.
"""
import base64
import hashlib
import html
import json
import os
import re
from pathlib import Path
from urllib.parse import urlparse
from xml.sax.saxutils import escape

from fastapi.responses import HTMLResponse, Response
from starlette.middleware.gzip import GZipMiddleware

ROOT = Path(__file__).parent
STATIC = ROOT / 'static'
PUBLIC_PATHS = ('/', '/privacy', '/terms')
PAGES = {
    '/': {
        'title': 'Free Instagram Downloader for Reels & Videos | Pocket',
        'description': 'Save public Instagram Reels, videos and available photos with Pocket. Free, no account or added watermark. Paste a link to check what Instagram makes accessible.',
        'name': 'Instagram media downloader',
    },
    '/privacy': {
        'title': 'Privacy Policy — Links, Cache & Local History | Pocket',
        'description': 'Learn how Pocket handles Instagram links, temporary media conversion, expiring caches and optional local history. No user accounts or tracking SDKs.',
        'name': 'Privacy policy',
    },
    '/terms': {
        'title': 'Terms of Use — Public Media & Creator Rights | Pocket',
        'description': 'Read the terms for using Pocket: public-content access, creator rights, download permissions, fair use and the technical limits of a free Instagram downloader.',
        'name': 'Terms of use',
    },
}


def validated_origin(value):
    """Fail closed for missing, placeholder or malformed production configuration."""
    try:
        p = urlparse(value.strip())
        host = (p.hostname or '').lower()
        if (p.scheme != 'https' or not host or '.' not in host or p.username or p.password
                or p.port not in (None, 443) or p.path not in ('', '/') or p.query or p.fragment
                or host in {'example.com', 'example.org', 'example.net'}
                or any(host.endswith('.' + d) for d in ('example.com', 'example.org', 'example.net'))
                or host.endswith(('.test', '.invalid', '.localhost', '.local', '.example'))
                or len(host) > 253 or not all(re.fullmatch(r'[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?', label) for label in host.split('.'))):
            return ''
        import ipaddress
        try:
            ipaddress.ip_address(host)
            return ''
        except ValueError:
            pass
        return 'https://' + host
    except ValueError:
        return ''


SITE_ORIGIN = validated_origin(os.getenv('PUBLIC_ORIGIN', ''))
INDEXING_ENABLED = os.getenv('SEO_INDEXING_ENABLED', 'true').lower() == 'true'
POLICIES = json.loads((ROOT / 'content' / 'policies.json').read_text())
HOME_TEMPLATE = (STATIC / 'index.html').read_text()
POLICY_TEMPLATE = (STATIC / 'policy.html').read_text()
ERROR_TEMPLATE = (STATIC / '404.html').read_text()
THEME_SCRIPT = (STATIC / 'theme.js').read_text()

ASSET_NAMES = ('style.css', 'app.js', 'client-config.js', 'theme.js', 'ops.js', 'icon.svg', 'icon-192.png', 'icon-512.png', 'social-card.png', 'sample.svg')
ASSET_HASHES = {name: hashlib.sha256((STATIC / name).read_bytes()).hexdigest()[:12] for name in ASSET_NAMES}
BUILD_ID = hashlib.sha256((''.join(ASSET_HASHES.values()) + HOME_TEMPLATE + POLICY_TEMPLATE + json.dumps(POLICIES) + json.dumps(PAGES)).encode()).hexdigest()[:12]


def asset_url(name):
    return '/' + name + '?v=' + ASSET_HASHES[name]


def public_indexable(path):
    return bool(SITE_ORIGIN and INDEXING_ENABLED and path in PUBLIC_PATHS)


def canonical(path):
    return SITE_ORIGIN + path if SITE_ORIGIN else ''


def schema_for(path):
    if not SITE_ORIGIN or path not in PUBLIC_PATHS:
        return None
    site_id = SITE_ORIGIN + '/#website'
    url = canonical(path)
    page = {'@type': 'WebPage', '@id': url + '#webpage', 'url': url,
            'name': PAGES[path]['title'], 'description': PAGES[path]['description'],
            'isPartOf': {'@id': site_id}, 'inLanguage': 'en'}
    graph = [page]
    if path == '/':
        graph.insert(0, {'@type': 'WebSite', '@id': site_id, 'name': 'Pocket', 'url': canonical('/'), 'inLanguage': 'en'})
    else:
        crumb_id = url + '#breadcrumb'
        page['breadcrumb'] = {'@id': crumb_id}
        graph.append({'@type': 'BreadcrumbList', '@id': crumb_id, 'itemListElement': [
            {'@type': 'ListItem', 'position': 1, 'name': 'Home', 'item': canonical('/')},
            {'@type': 'ListItem', 'position': 2, 'name': PAGES[path]['name'], 'item': url},
        ]})
    return {'@context': 'https://schema.org', '@graph': graph}


def csp(schema_text=None):
    theme_hash = base64.b64encode(hashlib.sha256(THEME_SCRIPT.encode()).digest()).decode()
    script = "'self' 'sha256-" + theme_hash + "'"
    if schema_text:
        digest = base64.b64encode(hashlib.sha256(schema_text.encode()).digest()).decode()
        script += " 'sha256-" + digest + "'"
    return f"default-src 'self'; script-src {script}; style-src 'self'; img-src 'self' data: blob:; media-src 'self' blob:; connect-src 'self'; object-src 'none'; base-uri 'self'; form-action 'self'"


def head_markup(path, title=None, description=None):
    page = PAGES.get(path, {})
    title = title or page.get('title', 'Pocket')
    description = description or page.get('description', '')
    robots = 'index, follow' if public_indexable(path) else 'noindex, follow'
    def meta(name, content, prop=False):
        return f'<meta {"property" if prop else "name"}="{name}" content="{html.escape(content, quote=True)}">'
    parts = [f'<title>{html.escape(title)}</title>', meta('description', description), meta('robots', robots),
             meta('og:type', 'website', True), meta('og:site_name', 'Pocket', True),
             meta('og:title', title, True), meta('og:description', description, True),
             meta('og:locale', 'en_US', True), meta('twitter:card', 'summary_large_image'),
             meta('twitter:title', title), meta('twitter:description', description)]
    if SITE_ORIGIN and path in PUBLIC_PATHS:
        url = canonical(path)
        parts += [f'<link rel="canonical" href="{html.escape(url, quote=True)}">', meta('og:url', url, True),
                  meta('og:image', SITE_ORIGIN + '/social-card.png', True),
                  meta('og:image:width', '1200', True), meta('og:image:height', '630', True),
                  meta('og:image:alt', 'Pocket — Good moments, kept. Free public Instagram media downloader.', True),
                  meta('twitter:image', SITE_ORIGIN + '/social-card.png'),
                  meta('twitter:image:alt', 'Pocket — Good moments, kept. Free public Instagram media downloader.')]
    for env, name in [('GOOGLE_SITE_VERIFICATION', 'google-site-verification'), ('BING_SITE_VERIFICATION', 'msvalidate.01')]:
        value = os.getenv(env, '')
        if path == '/' and value and re.fullmatch(r'[A-Za-z0-9_-]{8,256}', value):
            parts.append(meta(name, value))
    data = schema_for(path)
    schema_text = json.dumps(data, ensure_ascii=False, separators=(',', ':')).replace('<', '\\u003c') if data else None
    if schema_text:
        parts.append('<script type="application/ld+json">' + schema_text + '</script>')
    return '\n'.join(parts), csp(schema_text)


def render_page(path):
    metadata, policy = head_markup(path)
    if path == '/':
        document = HOME_TEMPLATE
    else:
        key = path[1:]
        document = POLICY_TEMPLATE.replace('__POLICY_TITLE__', PAGES[path]['name']).replace('__POLICY_SUBTITLE__', html.escape(POLICIES[key]['title'])).replace('__POLICY_BODY__', POLICIES[key]['body'])
    document = document.replace('__SEO_HEAD__', metadata).replace('__THEME_SCRIPT__', THEME_SCRIPT)
    for name in ASSET_NAMES:
        document = document.replace('="/' + name + '"', '="' + asset_url(name) + '"')
    return HTMLResponse(document, headers={'Cache-Control': 'no-cache', 'Content-Security-Policy': policy})


def not_found():
    metadata, policy = head_markup('/404', 'Page Not Found | Pocket', 'This Pocket page is not available. Return to the Instagram downloader or read our privacy policy and terms.')
    document = ERROR_TEMPLATE.replace('__SEO_HEAD__', metadata).replace('__THEME_SCRIPT__', THEME_SCRIPT)
    for name in ASSET_NAMES:
        document = document.replace('="/' + name + '"', '="' + asset_url(name) + '"')
    return HTMLResponse(document, status_code=404, headers={'Cache-Control': 'no-cache', 'Content-Security-Policy': policy})


def robots_response():
    text = '# Public resources remain crawlable so crawlers can see noindex directives.\nUser-agent: *\nAllow: /\n'
    if SITE_ORIGIN and INDEXING_ENABLED:
        text += '\nSitemap: ' + SITE_ORIGIN + '/sitemap.xml\n'
    else:
        text += '\n# Preview mode: public HTML carries noindex; no production sitemap is advertised.\n'
    return Response(text, media_type='text/plain', headers={'Cache-Control': 'no-cache'})


def sitemap_response():
    if not SITE_ORIGIN or not INDEXING_ENABLED:
        return Response('Production sitemap unavailable: configure a valid PUBLIC_ORIGIN and enable SEO_INDEXING_ENABLED.\n', status_code=503, media_type='text/plain', headers={'Retry-After': '3600', 'Cache-Control': 'no-store', 'X-Robots-Tag': 'noindex'})
    urls = ''.join('<url><loc>' + escape(canonical(p)) + '</loc></url>' for p in PUBLIC_PATHS)
    return Response('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' + urls + '</urlset>\n', media_type='application/xml', headers={'Cache-Control': 'no-cache'})


def service_worker():
    shell = list(PUBLIC_PATHS) + [asset_url(n) for n in ('style.css', 'app.js', 'client-config.js', 'theme.js', 'icon.svg', 'icon-192.png', 'icon-512.png')] + ['/manifest.webmanifest']
    text = (STATIC / 'sw.js').read_text().replace('__BUILD_ID__', BUILD_ID).replace('__SHELL_JSON__', json.dumps(shell))
    return Response(text, media_type='application/javascript', headers={'Cache-Control': 'no-cache'})


class PublicTextCompression:
    """Compress only public text; never buffer/compress API, ranged or media streams."""
    def __init__(self, app):
        self.app = app
        self.compressed = GZipMiddleware(app, minimum_size=700, compresslevel=6)

    async def __call__(self, scope, receive, send):
        path = scope.get('path', '')
        textual = (path in PUBLIC_PATHS or path in ('/ops', '/robots.txt', '/sitemap.xml', '/sw.js', '/manifest.webmanifest')
                   or path.endswith(('.css', '.js', '.svg', '.html')))
        target = self.compressed if scope['type'] == 'http' and textual and not path.startswith('/api/') else self.app
        await target(scope, receive, send)
