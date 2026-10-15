"""Pocket: public Instagram resolver. No login, session cookies or access-control bypasses."""
import asyncio
import collections
import contextlib
import ipaddress
import json
import logging
import os
import re
import secrets
import shutil
import socket
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException
import seo
from pydantic import BaseModel, Field

ROOT = Path(__file__).parent
TTL = int(os.getenv('CACHE_TTL', '600'))
MAX_BYTES = int(os.getenv('MAX_MEDIA_BYTES', str(1024 * 1024 * 1024)))
BROWSER = os.getenv('ENABLE_BROWSER', 'false').lower() == 'true'
ORIGIN = os.getenv('PUBLIC_ORIGIN', '').rstrip('/')
UA = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'
log = logging.getLogger('pocket')
@contextlib.asynccontextmanager
async def lifespan(app):
    async def cleanup():
        while True:
            await asyncio.sleep(15)
            sweep()
    task = asyncio.create_task(cleanup())
    yield
    task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await task

app = FastAPI(title='Pocket · Public media resolver', docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan)
app.add_middleware(seo.PublicTextCompression)
CROSS_ORIGIN = os.getenv('ENABLE_CROSS_ORIGIN', 'false').lower() == 'true'
if CROSS_ORIGIN:
    if not seo.SITE_ORIGIN:
        raise RuntimeError('ENABLE_CROSS_ORIGIN requires a valid HTTPS PUBLIC_ORIGIN.')
    ORIGIN = seo.SITE_ORIGIN  # Normalize host casing/default port for the write-origin guard too.
    app.add_middleware(CORSMiddleware, allow_origins=[seo.SITE_ORIGIN],
                       allow_credentials=False, allow_methods=['GET', 'POST'],
                       allow_headers=['Content-Type', 'Range'],
                       expose_headers=['Content-Disposition', 'Content-Length', 'Retry-After', 'Content-Range', 'Accept-Ranges'])

class ResolveError(Exception):
    def __init__(self, code='upstream', message='Instagram is not sharing this media right now. Try again later.', status=502, retry_after=None):
        self.code, self.message, self.status, self.retry_after = code, message, status, retry_after

@app.exception_handler(ResolveError)
async def resolve_error(request, exc):
    return JSONResponse({'error': exc.code, 'message': exc.message, 'retry_after': exc.retry_after}, status_code=exc.status,
                        headers={'Retry-After': str(exc.retry_after)} if exc.retry_after else {})

@dataclass
class Target:
    kind: str
    key: str
    url: str

def parse_url(value: str) -> Target:
    try:
        p = urlparse(value.strip())
        if p.scheme != 'https' or p.hostname not in {'instagram.com', 'www.instagram.com', 'm.instagram.com'} or p.username or p.password or p.port not in (None, 443):
            raise ValueError()
        path = p.path.rstrip('/')
        m = re.fullmatch(r'/(p|reel|reels|tv)/([A-Za-z0-9_-]{5,64})', path)
        if m:
            typ, code = m.groups()
            typ = 'reel' if typ == 'reels' else typ
            return Target(typ, f'{typ}:{code}', f'https://www.instagram.com/{typ}/{code}/')
        m = re.fullmatch(r'/stories/highlights/(\d{5,30})', path)
        if m:
            return Target('highlight', 'highlight:' + m[1], f'https://www.instagram.com/stories/highlights/{m[1]}/')
        m = re.fullmatch(r'/stories/([A-Za-z0-9._]{1,30})/(\d{5,30})', path)
        if m:
            return Target('story', f'story:{m[1]}:{m[2]}', f'https://www.instagram.com/stories/{m[1]}/{m[2]}/')
    except (ValueError, AttributeError):
        pass
    raise ResolveError('invalid_url', 'Paste a full HTTPS Instagram post, Reel, video, Story or Highlight link.', 400)


def allowed_host(host):
    return bool(host and any(host == d or host.endswith('.' + d) for d in ('cdninstagram.com', 'fbcdn.net', 'instagram.com')))

async def safe_url(url):
    """Validate every hop, including DNS. Requests never accept caller-supplied media URLs."""
    try:
        p = urlparse(url)
        if p.scheme != 'https' or not allowed_host(p.hostname) or p.username or p.password or p.port not in (None, 443):
            raise ValueError()
        answers = await asyncio.get_running_loop().getaddrinfo(p.hostname, 443, type=socket.SOCK_STREAM)
        if not answers or any(not ipaddress.ip_address(a[4][0]).is_global for a in answers):
            raise ValueError()
    except (ValueError, OSError):
        raise ResolveError('unsafe_source', 'The media source could not be verified.', 502)

@contextlib.asynccontextmanager
async def upstream(url, timeout=25, byte_range=None):
    # Follow redirects ourselves so each destination is checked, never by an open proxy.
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=False, trust_env=False, headers={'User-Agent': UA, 'Referer': 'https://www.instagram.com/', 'Accept-Language': 'en-US,en;q=0.8', **({'Range': byte_range} if byte_range else {})}) as client:
        for _ in range(4):
            await safe_url(url)
            async with client.stream('GET', url) as response:
                if response.status_code in (301, 302, 303, 307, 308):
                    url = urljoin(url, response.headers.get('location', ''))
                    continue
                yield response
                return
        raise ResolveError('upstream', 'Instagram sent too many redirects.', 502)


def check_status(status):
    if status == 429:
        raise ResolveError('rate_limited', 'Instagram is receiving too many requests. Give it a little time.', 429, 60)
    if status == 404:
        raise ResolveError('not_found', 'This link may be deleted, expired or unavailable.', 404)
    if status in (401, 403):
        raise ResolveError('login_required', 'Instagram requires access to this content. Private and login-required media are not supported.', 403)
    if status >= 400:
        raise ResolveError()

@dataclass
class Asset:
    url: str
    ext: str
    quality: str
    size: int | None = None
    width: int | None = None
    height: int | None = None

@dataclass
class Media:
    kind: str
    author: str = ''
    caption: str = ''
    date: str | None = None
    thumbnail: str | None = None
    groups: list[list[Asset]] = field(default_factory=list)


def clean_url(url):
    return url if isinstance(url, str) and urlparse(url).scheme == 'https' and allowed_host(urlparse(url).hostname) else None


def ytdlp_sync(target):
    import yt_dlp
    class Quiet:
        def debug(self, msg): pass
        def warning(self, msg): pass
        def error(self, msg): pass
    try:
        with yt_dlp.YoutubeDL({'quiet': True, 'no_warnings': True, 'skip_download': True, 'socket_timeout': 12,
                              'retries': 0, 'extractor_retries': 0, 'logger': Quiet(), 'http_headers': {'User-Agent': UA},
                              'noplaylist': False, 'cachedir': False}) as ydl:
            info = ydl.extract_info(target.url, download=False)
    except Exception as exc:
        text = str(exc).lower()
        if '429' in text or 'rate-limit' in text or 'too many requests' in text:
            raise ResolveError('rate_limited', 'Instagram is temporarily limiting requests. Try again in a minute.', 429, 60)
        if 'private' in text:
            raise ResolveError('private', 'This account or post is private. Only public, accessible media can be downloaded.', 403)
        if 'not available' in text or 'not found' in text or '404' in text:
            raise ResolveError('not_found', 'This post may be deleted, expired or unavailable.', 404)
        if 'login' in text or 'cookie' in text:
            raise ResolveError('login_required', 'Instagram is asking for a login for this link. Try a different public post.', 403)
        raise ResolveError()
    if not info:
        raise ResolveError()
    entries = list(info.get('entries') or [info])
    result = Media('video', info.get('channel') or info.get('uploader') or '', (info.get('description') or '')[:10000], info.get('upload_date'), clean_url(info.get('thumbnail')))
    for entry in entries[:100]:
        if not entry:
            continue
        if not result.author:
            result.author = entry.get('channel') or entry.get('uploader') or ''
        if not result.caption:
            result.caption = (entry.get('description') or '')[:10000]
        if not result.thumbnail:
            result.thumbnail = clean_url(entry.get('thumbnail'))
        result.date = result.date or entry.get('upload_date')
        formats = entry.get('formats') or [entry]
        assets = []
        seen = set()
        for fmt in formats:
            url = clean_url(fmt.get('url'))
            ext = fmt.get('ext', 'mp4')
            # Separate video-only tracks are not represented as complete MP4 downloads.
            if not url or url in seen or ext not in ('mp4', 'jpg', 'jpeg', 'png', 'webp', 'm4a') or fmt.get('protocol') in ('m3u8_native', 'm3u8', 'http_dash_segments'):
                continue
            if fmt.get('vcodec') not in (None, 'none') and fmt.get('acodec') == 'none':
                continue
            seen.add(url)
            height = fmt.get('height')
            quality = f'{height}p' if height else ('Original image' if ext in ('jpg', 'jpeg', 'png', 'webp') else 'Original')
            assets.append(Asset(url, ext, quality, fmt.get('filesize') or fmt.get('filesize_approx'), fmt.get('width'), height))
        if assets:
            assets.sort(key=lambda a: a.height or 0, reverse=True)
            result.groups.append(assets)
    if not result.groups:
        raise ResolveError()
    result.kind = 'carousel' if len(result.groups) > 1 else ('image' if result.groups[0][0].ext in ('jpg', 'jpeg', 'png', 'webp') else 'video')
    return result

async def method_ytdlp(target):
    return await asyncio.to_thread(ytdlp_sync, target)


def parse_html(html):
    soup = BeautifulSoup(html, 'html.parser')
    def meta(name):
        el = soup.find('meta', property=name) or soup.find('meta', attrs={'name': name})
        return el.get('content', '') if el else ''
    result = Media('video', caption=meta('og:description')[:10000], thumbnail=clean_url(meta('og:image')))
    # Structured data is preferred. Handles nested graphs and carousel sidecars.
    candidates = []
    def walk(node):
        if isinstance(node, dict):
            if node.get('is_private') is True:
                raise ResolveError('private', 'This account is private. Only public content is supported.', 403)
            if node.get('edge_sidecar_to_children'):
                for edge in node['edge_sidecar_to_children'].get('edges', []):
                    walk(edge.get('node', {}))
                return
            url = node.get('video_url') or node.get('contentUrl') or node.get('content_url')
            typ = node.get('@type', '')
            image = node.get('display_url') or (node.get('url') if typ == 'ImageObject' else None)
            asset_url = clean_url(url) or clean_url(image)
            if asset_url:
                is_video = bool(url) and typ != 'ImageObject'
                candidates.append(Asset(asset_url, 'mp4' if is_video else 'jpg', 'Original'))
            owner = node.get('owner') or node.get('author')
            if isinstance(owner, dict):
                result.author = result.author or owner.get('username') or owner.get('name') or ''
            result.caption = node.get('caption') if isinstance(node.get('caption'), str) else result.caption
            result.date = result.date or node.get('uploadDate') or node.get('datePublished')
            for v in node.values():
                if isinstance(v, (dict, list)):
                    walk(v)
        elif isinstance(node, list):
            for item in node:
                walk(item)
    for script in soup.find_all('script'):
        text = script.string or ''
        if script.get('type') in ('application/ld+json', 'application/json'):
            try:
                walk(json.loads(text))
            except (json.JSONDecodeError, RecursionError):
                pass
        # Historical shared-data shape, parsed as JSON only, never evaluated.
        for pattern in (r'window\._sharedData\s*=\s*(\{.*?\});', r'window\.__additionalDataLoaded\([^,]+,\s*(\{.*\})\);'):
            m = re.search(pattern, text, re.S)
            if m:
                try:
                    walk(json.loads(m[1]))
                except (json.JSONDecodeError, RecursionError):
                    pass
    if not candidates:
        video = clean_url(meta('og:video:secure_url') or meta('og:video'))
        if video:
            candidates = [Asset(video, 'mp4', 'Original')]
        # An og:image alone may be a generic login page, not the requested image. Never infer success from it.
    seen = set()
    for a in candidates:
        if a.url not in seen:
            result.groups.append([a])
            seen.add(a.url)
    if not result.groups:
        if 'accounts/login' in html or 'login_required' in html:
            raise ResolveError('login_required', 'Instagram is requesting a login. This tool cannot access login-required content.', 403)
        raise ResolveError()
    result.kind = 'carousel' if len(result.groups) > 1 else ('image' if result.groups[0][0].ext == 'jpg' else 'video')
    return result

async def method_html(target):
    if target.kind in ('story', 'highlight'):
        raise ResolveError('login_required', 'Stories and Highlights often require an Instagram session, which this tool does not use.', 403)
    async with upstream(target.url + 'embed/captioned/') as response:
        check_status(response.status_code)
        buf = bytearray()
        async for chunk in response.aiter_bytes():
            buf.extend(chunk)
            if len(buf) > 5_000_000:
                raise ResolveError()
    return parse_html(buf.decode('utf-8', errors='replace'))

async def method_browser(target):
    """Optional rendering fallback. Never solves challenges or supplies login cookies."""
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=['--disable-dev-shm-usage'])
        try:
            context = await browser.new_context(user_agent=UA, service_workers='block')
            async def guard(route):
                try:
                    await safe_url(route.request.url)
                    # Block heavy resources. Extract structured metadata from the rendered DOM.
                    if route.request.resource_type in ('image', 'media', 'font'):
                        return await route.abort()
                    await route.continue_()
                except Exception:
                    await route.abort()
            await context.route('**/*', guard)
            page = await context.new_page()
            await page.goto(target.url, wait_until='domcontentloaded', timeout=20000)
            await page.wait_for_timeout(1500)
            return parse_html(await page.content())
        finally:
            await browser.close()

cache = {}
tokens = {}
buckets = {}
metrics = {name: {'success': 0, 'failure': 0, 'consecutive_failures': 0, 'open_until': 0} for name in ('ytdlp', 'html', 'browser')}
locks = {}
runtime_flags = {}

def engine_enabled(name):
    if name in runtime_flags:
        return runtime_flags[name]
    return (name != 'browser' or BROWSER) and os.getenv(f'DISABLE_{name.upper()}', 'false').lower() != 'true'

semaphore = asyncio.Semaphore(int(os.getenv('RESOLVER_CONCURRENCY', '3')))
active_downloads = 0


def sweep():
    now = time.monotonic()
    for store in (cache, tokens):
        for key in list(store):
            if store[key][0] <= now:
                del store[key]
    for key in list(buckets):
        if now - buckets[key][1] > 3600:
            del buckets[key]


def limit(request, action='resolve'):
    # Trust direct peer only. Configure edge limits separately when behind a reverse proxy.
    peer = request.client.host if request.client else 'unknown'
    trusted = {x.strip() for x in os.getenv('TRUST_PROXY_IPS', '').split(',') if x.strip()}
    if peer in trusted:
        forwarded = request.headers.get('x-forwarded-for', '').split(',')[-1].strip()
        try:
            peer = str(ipaddress.ip_address(forwarded))
        except ValueError:
            pass
    key = (peer, action)
    now = time.monotonic()
    capacity, refill = (12, 1 / 5) if action == 'resolve' else (40, 1)
    balance, updated = buckets.get(key, (capacity, now))
    balance = min(capacity, balance + (now - updated) * refill)
    if balance < 1:
        wait = max(1, int((1 - balance) / refill) + 1)
        raise ResolveError('rate_limited', 'A few too many requests at once. Please try again shortly.', 429, wait)
    buckets[key] = (balance - 1, now)


def issue(asset, filename, mode='file'):
    if len(tokens) > 20000:
        raise ResolveError('busy', 'The service is busy. Please try again shortly.', 503, 30)
    token = secrets.token_urlsafe(32)
    tokens[token] = (time.monotonic() + TTL, asset, filename, mode)
    return f'/api/{"preview" if mode == "preview" else "download"}?token={token}'


def serialize(media, target, method):
    items = []
    for i, group in enumerate(media.groups):
        for a in group:
            name = f'pocket-{target.key.split(":")[-1]}-{i+1}.{a.ext}'
            item = {'id': str(i), 'quality': a.quality, 'ext': a.ext, 'url': issue(a, name), 'size_estimate': a.size,
                    'width': a.width, 'height': a.height, 'preview_url': issue(a, name, 'preview')}
            items.append(item)
        # Audio is actual FFmpeg conversion, not an mp4 renamed to mp3.
        if shutil.which('ffmpeg') and group[0].ext == 'mp4':
            a = group[0]
            items.append({'id': str(i), 'quality': 'audio', 'ext': 'mp3', 'url': issue(a, f'pocket-{target.key.split(":")[-1]}-{i+1}.mp3', 'audio')})
    thumbnail = issue(Asset(media.thumbnail, 'jpg', 'thumbnail'), 'preview.jpg', 'preview') if media.thumbnail else None
    return {'type': media.kind, 'source_type': target.kind, 'author': media.author, 'caption': media.caption, 'date': media.date,
            'thumbnail': thumbnail, 'items': items, 'method': method, 'expires_in': TTL}

async def cascade(target):
    methods = [('ytdlp', method_ytdlp), ('html', method_html)]
    if engine_enabled('browser'):
        methods.append(('browser', method_browser))
    errors = []
    for name, fn in methods:
        if not engine_enabled(name):
            continue
        stat = metrics[name]
        if stat['open_until'] > time.monotonic():
            continue
        try:
            # to_thread is not cancellable: yt-dlp itself uses short socket timeouts and zero retries.
            media = await fn(target)
            stat['success'] += 1
            stat['consecutive_failures'] = 0
            log.info('resolver method=%s outcome=success', name)
            return media, name
        except Exception as exc:
            err = exc if isinstance(exc, ResolveError) else ResolveError()
            errors.append(err)
            stat['failure'] += 1
            if err.status >= 500:
                stat['consecutive_failures'] += 1
                if stat['consecutive_failures'] >= 5:
                    stat['open_until'] = time.monotonic() + 60
            log.info('resolver method=%s outcome=%s', name, err.code)
            if err.status == 429 or err.code == 'private':
                raise err  # Respect upstream limits and privacy; do not rotate around them.
    for code in ('private', 'login_required', 'not_found'):
        for err in errors:
            if err.code == code:
                raise err
    if target.kind in ('story', 'highlight'):
        raise ResolveError('login_required', 'Stories and Highlights generally require a session. This service never asks for Instagram credentials.', 403)
    raise ResolveError()

class ResolveBody(BaseModel):
    url: str = Field(min_length=1, max_length=2048)

@app.middleware('http')
async def security(request, call_next):
    path = request.url.path
    # Known duplicate documents only: combine host/scheme/path normalization in one hop.
    aliases = {'/index.html': '/', '/ops.html': '/ops'}
    preferred_path = aliases.get(path, path.rstrip('/') if path.rstrip('/') in ('/terms', '/privacy', '/ops') else path)
    peer = request.client.host if request.client else ''
    trusted = {x.strip() for x in os.getenv('TRUST_PROXY_IPS', '').split(',') if x.strip()}
    scheme = request.url.scheme
    if peer in trusted and request.headers.get('x-forwarded-proto') in ('https', 'http'):
        scheme = request.headers['x-forwarded-proto']
    public_resource = preferred_path in (*seo.PUBLIC_PATHS, '/ops', '/robots.txt', '/sitemap.xml', '/sw.js', '/manifest.webmanifest') or preferred_path.lstrip('/') in seo.ASSET_HASHES
    if CROSS_ORIGIN and (preferred_path == '/ops' or preferred_path.lstrip('/') in seo.ASSET_HASHES):
        public_resource = False  # Keep backend operations UI and its self-hosted assets usable.
    origin_mismatch = bool(seo.SITE_ORIGIN and public_resource and (request.headers.get('host', '').lower() != urlparse(seo.SITE_ORIGIN).netloc or scheme != 'https'))
    if request.method in ('GET', 'HEAD') and (preferred_path != path or origin_mismatch):
        suffix = ('?' + request.url.query) if request.url.query else ''
        target = (seo.SITE_ORIGIN if origin_mismatch else '') + preferred_path + suffix
        return RedirectResponse(target, status_code=308, headers={'Cache-Control': 'no-cache'})
    if request.method in ('POST', 'PATCH'):
        origin = request.headers.get('origin')
        expected = ORIGIN or f'{request.url.scheme}://{request.headers.get("host", "")}'
        # The dev preview proxy terminates HTTPS; allow that exact same host, never arbitrary origins.
        if origin and origin not in {expected, f'https://{request.headers.get("host", "")}'}:
            return JSONResponse({'message': 'Cross-origin requests are not allowed.'}, 403)
        try:
            length = int(request.headers.get('content-length', '0') or 0)
        except ValueError:
            return JSONResponse({'message': 'Invalid content length.'}, 400)
        if length > 8192:
            return JSONResponse({'message': 'Request too large.'}, 413)
        # Render's free path does not use our Caddy config. Bound chunked bodies here too.
        buffered = bytearray()
        async for chunk in request.stream():
            if len(buffered) + len(chunk) > 8192:
                return JSONResponse({'message': 'Request too large.'}, 413)
            buffered.extend(chunk)
        request._body = bytes(buffered)  # Starlette's cached request replays this to the route.
    response = await call_next(request)
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Referrer-Policy'] = 'no-referrer'
    response.headers['Permissions-Policy'] = 'camera=(), microphone=(), geolocation=()'
    response.headers.setdefault('Content-Security-Policy', seo.csp())
    if ORIGIN.startswith('https://'):
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    if path.startswith('/api/') or path in ('/ops', '/openapi.json'):
        response.headers['Cache-Control'] = 'no-store'
        response.headers['X-Robots-Tag'] = 'noindex, nofollow'
    elif path in seo.PUBLIC_PATHS:
        if not seo.public_indexable(path):
            response.headers['X-Robots-Tag'] = 'noindex, follow'
    elif response.status_code >= 400:
        response.headers['X-Robots-Tag'] = 'noindex, follow'
    name = path.lstrip('/')
    if name in seo.ASSET_HASHES and response.status_code == 200:
        response.headers['Cache-Control'] = ('public, max-age=31536000, immutable' if request.query_params.get('v') == seo.ASSET_HASHES[name] else 'public, max-age=3600, must-revalidate')
    return response

@contextlib.asynccontextmanager
async def keyed_lock(key):
    entry = locks.setdefault(key, {'lock': asyncio.Lock(), 'users': 0})
    entry['users'] += 1
    try:
        async with entry['lock']:
            yield
    finally:
        entry['users'] -= 1
        if entry['users'] == 0:
            locks.pop(key, None)

@app.post('/api/resolve')
async def resolve(body: ResolveBody, request: Request):
    limit(request)
    target = parse_url(body.url)
    sweep()
    if target.key in cache:
        _, media, method = cache[target.key]
        return serialize(media, target, method)
    if len(locks) > 200 or len(cache) > 2000:
        raise ResolveError('busy', 'The service is busy. Try again in a moment.', 503, 15)
    async with keyed_lock(target.key):
        if target.key in cache:
            _, media, method = cache[target.key]
            return serialize(media, target, method)
        try:
            await asyncio.wait_for(semaphore.acquire(), timeout=8)
        except TimeoutError:
            raise ResolveError('busy', 'The service is busy. Try again in a moment.', 503, 15)
        try:
            media, method = await cascade(target)
            cache[target.key] = (time.monotonic() + TTL, media, method)
            return serialize(media, target, method)
        finally:
            semaphore.release()

@app.get('/api/health')
async def health():
    return {'status': 'ok', 'engines': {name: engine_enabled(name) for name in metrics},
            'audio_conversion': bool(shutil.which('ffmpeg'))}

def authorized(request):
    secret = os.getenv('METRICS_TOKEN')
    return bool(secret) and secrets.compare_digest(request.headers.get('authorization', ''), 'Bearer ' + secret)

class EngineFlags(BaseModel):
    ytdlp: bool | None = None
    html: bool | None = None
    browser: bool | None = None

@app.patch('/api/admin/engines')
async def set_engines(flags: EngineFlags, request: Request):
    if not authorized(request):
        return JSONResponse({'message': 'Not found'}, 404)
    for name, enabled in flags.model_dump(exclude_none=True).items():
        runtime_flags[name] = enabled
        if enabled:
            metrics[name]['open_until'] = 0
            metrics[name]['consecutive_failures'] = 0
    return {'engines': {name: engine_enabled(name) for name in metrics}}

@app.get('/api/metrics')
async def get_metrics(request: Request):
    if not authorized(request):
        return JSONResponse({'message': 'Not found'}, 404)
    return {'methods': {name: {**stat, 'enabled': engine_enabled(name), 'cooldown_seconds': max(0, round(stat['open_until'] - time.monotonic()))} for name, stat in metrics.items()}, 'cached_posts': len(cache), 'active_downloads': active_downloads}

@app.get('/api/preview')
@app.get('/api/download')
async def download(request: Request, token: str = ''):
    global active_downloads
    limit(request, 'download')
    entry = tokens.get(token)
    if not entry or entry[0] <= time.monotonic():
        raise ResolveError('expired', 'This download link expired. Paste the Instagram link again to refresh it.', 410)
    _, asset, filename, mode = entry
    if (request.url.path.endswith('preview')) != (mode == 'preview'):
        raise ResolveError('invalid_token', 'Invalid download link.', 400)
    if active_downloads >= int(os.getenv('MAX_ACTIVE_DOWNLOADS', '12')):
        raise ResolveError('busy', 'Downloads are busy. Please try again shortly.', 503, 10)
    active_downloads += 1
    if mode == 'audio':
        return await audio_response(asset, filename)
    byte_range = request.headers.get('range')
    if byte_range and (not re.fullmatch(r'bytes=(?:\d+-\d*|-\d+)', byte_range)):
        active_downloads -= 1
        raise ResolveError('invalid_range', 'Invalid media byte range.', 416)
    cm = upstream(asset.url, timeout=45, byte_range=byte_range)
    try:
        response = await cm.__aenter__()
        check_status(response.status_code)
        ct = response.headers.get('content-type', '').split(';')[0]
        if not (ct.startswith('video/') or ct.startswith('image/') or ct.startswith('audio/') or ct == 'application/octet-stream'):
            raise ResolveError('unavailable', 'Instagram returned an unavailable media file. Resolve the link again.', 502)
        length = int(response.headers.get('content-length', 0))
        if length > MAX_BYTES:
            raise ResolveError('too_large', 'This file exceeds this server’s safe streaming capacity.', 413)
    except Exception:
        await cm.__aexit__(None, None, None)
        active_downloads -= 1
        raise
    async def chunks():
        global active_downloads
        total = 0
        try:
            async for chunk in response.aiter_bytes(65536):
                total += len(chunk)
                if total > MAX_BYTES:
                    break
                yield chunk
        finally:
            await cm.__aexit__(None, None, None)
            active_downloads -= 1
    headers = {'Content-Disposition': f'{"inline" if mode == "preview" else "attachment"}; filename="{filename}"', 'Cache-Control': 'no-store'}
    if length:
        headers['Content-Length'] = str(length)
    if response.status_code == 206 and response.headers.get('content-range'):
        headers['Content-Range'] = response.headers['content-range']
    if response.headers.get('accept-ranges') == 'bytes':
        headers['Accept-Ranges'] = 'bytes'
    return StreamingResponse(chunks(), media_type=ct, headers=headers, status_code=response.status_code)

async def audio_response(asset, filename):
    global active_downloads
    if not shutil.which('ffmpeg'):
        active_downloads -= 1
        raise ResolveError('audio_unavailable', 'Audio conversion is not installed on this server.', 503)
    folder = tempfile.TemporaryDirectory(prefix='pocket-')
    source, output = Path(folder.name) / 'source.mp4', Path(folder.name) / 'audio.mp3'
    try:
        async with upstream(asset.url, timeout=45) as response:
            check_status(response.status_code)
            if int(response.headers.get('content-length', 0)) > min(MAX_BYTES, 250_000_000):
                raise ResolveError('too_large', 'This video is too large for audio conversion on this server.', 413)
            total = 0
            with source.open('wb') as f:
                async for chunk in response.aiter_bytes(65536):
                    total += len(chunk)
                    if total > min(MAX_BYTES, 250_000_000):
                        raise ResolveError('too_large', 'This video is too large for audio conversion.', 413)
                    f.write(chunk)
        proc = await asyncio.create_subprocess_exec('ffmpeg', '-nostdin', '-v', 'error', '-protocol_whitelist', 'file,pipe', '-i', str(source), '-vn', '-codec:a', 'libmp3lame', '-q:a', '2', str(output), stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL)
        try:
            await asyncio.wait_for(proc.wait(), 90)
        except (TimeoutError, asyncio.CancelledError):
            proc.kill()
            await proc.wait()
            raise ResolveError('conversion', 'Audio conversion timed out. Try the original video instead.', 502)
        if proc.returncode != 0 or not output.exists():
            raise ResolveError('conversion', 'No usable audio track was found. Download the original video instead.', 422)
        async def stream():
            global active_downloads
            try:
                with output.open('rb') as f:
                    while chunk := f.read(65536):
                        yield chunk
            finally:
                folder.cleanup()
                active_downloads -= 1
        return StreamingResponse(stream(), media_type='audio/mpeg', headers={'Content-Disposition': f'attachment; filename="{filename}"', 'Content-Length': str(output.stat().st_size)})
    except BaseException:
        folder.cleanup()
        active_downloads -= 1
        raise

@app.api_route('/ops', methods=['GET', 'HEAD'])
async def ops():
    document = (ROOT / 'static' / 'ops.html').read_text()
    for name in ('style.css', 'ops.js'):
        document = document.replace('="/' + name + '"', '="' + seo.asset_url(name) + '"')
    return Response(document, media_type='text/html', headers={'Cache-Control': 'no-store'})

@app.api_route('/', methods=['GET', 'HEAD'])
@app.api_route('/terms', methods=['GET', 'HEAD'])
@app.api_route('/privacy', methods=['GET', 'HEAD'])
async def public_page(request: Request):
    return seo.render_page(request.url.path)

@app.api_route('/robots.txt', methods=['GET', 'HEAD'])
async def robots():
    return seo.robots_response()

@app.api_route('/sitemap.xml', methods=['GET', 'HEAD'])
async def sitemap():
    return seo.sitemap_response()

@app.api_route('/sw.js', methods=['GET', 'HEAD'])
async def sw():
    return seo.service_worker()

@app.api_route('/manifest.webmanifest', methods=['GET', 'HEAD'])
async def manifest():
    data = json.loads((ROOT / 'static' / 'manifest.webmanifest').read_text())
    for icon in data['icons']:
        icon['src'] = seo.asset_url(icon['src'].lstrip('/'))
    return Response(json.dumps(data), media_type='application/manifest+json', headers={'Cache-Control': 'no-cache'})

@app.exception_handler(StarletteHTTPException)
async def http_error(request, exc):
    if exc.status_code == 404 and not request.url.path.startswith('/api/'):
        return seo.not_found()
    return JSONResponse({'detail': exc.detail}, status_code=exc.status_code, headers=exc.headers)

class PublicStaticFiles(StaticFiles):
    async def get_response(self, path, scope):
        # Templates are served exclusively through the metadata-aware document routes.
        if path.endswith('.html'):
            raise StarletteHTTPException(404)
        return await super().get_response(path, scope)

app.mount('/', PublicStaticFiles(directory=ROOT / 'static'), name='static')
