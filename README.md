# Pocket — Good moments, kept.

A no-account public Instagram media utility: responsive web UI, public-access fallback resolver, tokenized streaming proxy, optional MP3 extraction and installable PWA shell.

**Status: implemented and tested release candidate, not a promise that every Instagram link will work.** Instagram can block logged-out access at any time. Private posts and login-required content are not bypassed. See [REPORT.md](REPORT.md) for actual live results and outstanding launch checks.

## Free public hobby launch — start here

Follow **[FREE_LAUNCH_GUIDE.md](FREE_LAUNCH_GUIDE.md)** for the new GitHub Pages frontend + Render Free API preset and Google Search Console steps. No purchased domain or paid API is required. This is not guaranteed-uptime production hosting: limits, upstream blocks and legal clearance still matter. See **FREE_LAUNCH_REPORT.md** for exactly what was tested.

## Run locally

Python 3.13 recommended. FFmpeg is needed for MP3; Chromium is optional.

```sh
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.lock
# Optional renderer; install OS dependencies on Linux too:
python -m playwright install --with-deps chromium
# Install ffmpeg using your OS package manager.
uvicorn app:app --host 0.0.0.0 --port 8000 --no-access-log --no-proxy-headers
```

Visit port **8000**. Relative API paths work behind Arena's live-preview proxy. The sample is explicitly a locally authored illustration, not a fabricated Instagram response. In the default same-origin mode, original media downloads stream through the server into the browser download manager; the app never redirects a download to Instagram.

## Architecture and method evaluation

| Strategy | Decision | Trade-off |
|---|---|---|
| **B · yt-dlp** | Primary | Maintained extractor, lowest bespoke reverse-engineering burden. Real server required; logged-out success varies. Photo completeness depends on extractor output. |
| **A · Public HTML/embed** | Second | Cheap independent structured-data parser: JSON-LD, JSON scripts, shared-data blobs, sidecars and OG video. Frequently returns incomplete/gated markup. A generic OG thumbnail is deliberately **not** treated as a downloadable post. |
| **C · Playwright** | Optional third | Renders the public page before structured-data parsing. Expensive; no login cookies, challenge solving or CAPTCHA bypass. Does not indiscriminately collect arbitrary recommendation-network media. Disabled by default. |
| **D · Aggregator** | Evaluated, not implemented | Paid dependency, URL disclosure and vendor uptime undermine this free/private default. Add only after provider review and privacy-policy update. |

```text
Browser/PWA → same-origin FastAPI → B → A → C (if enabled)
                                  ↓
                      TTL metadata cache + expiring tokens
                                  ↓
               /api/download → validated CDN → streamed file
```

One Python service serves both the frontend and resolver rather than adding a Node gateway. This reduces operating overhead and avoids duplicate contracts. Blocking yt-dlp runs off the event loop, with bounded resolver concurrency. In-memory storage is intentional for a **single worker**. Do not scale to multiple workers or replicas without moving cache, token records, keyed locks, flags and rate buckets to Redis/shared storage or implementing sticky routing.

## Production deployment: one VPS + Docker + Caddy

1. Install Docker Engine and Compose plugin on a Linux VPS (start with 2 vCPU / 2–4 GB RAM; measure your workload).
2. Point an A/AAAA record for your domain at the VPS; permit ports 80 and 443.
3. Copy `.env.example` to `.env`; set `DOMAIN` and a random `METRICS_TOKEN`.
4. Review Terms/Privacy and add operator identity, contact and a rights-request process before a public launch.
5. Run `docker compose up --build -d`. Caddy terminates HTTPS and renews certificates automatically.
6. Verify `https://your-domain/api/health`, one authorized public link, and an actual saved file from an external browser.
7. Visit `/ops` and enter your operations token to view aggregate method health and toggle methods without redeploying.

Docker was **not available in this workspace**, so this Compose deployment has not been built or run here. Test it on a staging host before launch. The dedicated Compose subnet is `172.29.87.0/24`; change it and `TRUST_PROXY_IPS` together if it conflicts with your infrastructure. Only Caddy's exact private IP is trusted for per-client `X-Forwarded-For`. The app port is not published. Do not trust arbitrary forwarding headers.

For a managed-container host: build the same Dockerfile, publish port 8000 through the host's HTTPS routing, set `PUBLIC_ORIGIN`, and configure trusted proxy addresses for that host. A serverless-only/edge deployment is not suitable for the Python extractor, FFmpeg or Chromium. For the implemented free split-site preset, use `Dockerfile.free`, `render.yaml`, `scripts/export_pages.py` and `.github/workflows/pages.yml` as described in FREE_LAUNCH_GUIDE.md instead. Do not publish raw `static/index.html`; it is a server template. Exact-origin CORS is opt-in, never wildcard.

## Environment

| Variable | Default | Meaning |
|---|---|---|
| `PUBLIC_ORIGIN` | empty (same-host dev) | Production HTTPS origin used for write-request origin checks and HSTS |
| `CACHE_TTL` | `600` | Metadata and opaque-token lifetime in seconds; 15-second background cleanup interval |
| `ENABLE_BROWSER` | `false` | Enable public Chromium rendering fallback |
| `DISABLE_YTDLP`, `DISABLE_HTML`, `DISABLE_BROWSER` | `false` | Persistent method kill switches; restart process after changing |
| `RESOLVER_CONCURRENCY` | `3` | Maximum concurrent resolutions; queue wait capped at 8 seconds |
| `ENABLE_CROSS_ORIGIN` | `false` | Opt into public frontend → backend CORS for the exact validated `PUBLIC_ORIGIN`; free split preset only |
| `MAX_ACTIVE_DOWNLOADS` | `12` | Concurrent media request ceiling; free preset uses 2 |
| `MAX_MEDIA_BYTES` | `1073741824` | Safe server stream ceiling (1 GiB), not a paid tier |
| `METRICS_TOKEN` | unset | Enables bearer-authenticated aggregate metrics and runtime switches |
| `TRUST_PROXY_IPS` | empty | Comma-separated exact direct proxy IPs allowed to supply client IPs |

No Instagram credentials or third-party API keys are required. No proxies are rotated around upstream restrictions. An upstream 429 stops the cascade and returns a retry interval. Private-account errors also stop it. Technical safety limits are explicit: 12-request resolver burst, refill 1 request/5s/IP; 40 media requests burst, refill 1/s/IP; 12 active media requests; 1 GiB stream ceiling; 250 MB input ceiling and 90-second timeout for MP3 conversion. Adjust only after capacity testing. Preview requests share the media rate bucket.

## API

### `POST /api/resolve`

```json
{"url":"https://www.instagram.com/reel/SHORTCODE/"}
```

Returns `type`, `source_type`, `author`, `caption`, `date`, proxied `thumbnail`, `method`, `expires_in`, and `items` with `id`, `quality`, `ext`, `url`, optional `preview_url`, dimensions and estimated size. Matching `id` values are renditions of the same carousel item, not additional carousel entries. MP3 is advertised only when FFmpeg is available; conversion can still fail for silent/unsupported source tracks. Original quality is shown honestly when dimensions/renditions are not supplied by the extractor.

Errors include: 400 invalid URL, 403 private/login required, 404 deleted/unavailable, 410 expired token, 413 resource ceiling, 429 throttled, 502 upstream/conversion error and 503 busy. Deleted versus gated content cannot always be distinguished from Instagram's response.

### Media routes

- `GET /api/download?token=…`: opaque-token lookup, validated CDN GET, attachment filename and streaming response; no redirect. Original files and previews support a single byte range when the CDN does. MP3 is a real FFmpeg transcode in temporary storage.
- `GET /api/preview?token=…`: inline version, distinct preview token; source URLs are not returned to the client.
- `GET /api/health`: public capabilities, no metadata or secrets.
- `GET /api/metrics`: `Authorization: Bearer METRICS_TOKEN`; aggregates only.
- `PATCH /api/admin/engines`: same bearer header, JSON such as `{"ytdlp":false,"html":true}`. Runtime flags apply to new requests; they reset at restart. Cached successful results remain until expiry.

## Security and retention

Strict HTTPS Instagram input hostname/path allowlist; canonical URLs strip query tracking. Media fetches accept only known Instagram/Meta domains and public DNS addresses, validate redirects, reject HTML masquerading as media and enforce byte/concurrency limits. Opaque 256-bit tokens are bearer capabilities: do not log or share them. Captions/author fields are rendered using DOM text, not HTML. Security headers include CSP, no-sniff, no-referrer and production HSTS. Write requests reject unapproved origins. Default mode emits no CORS header; explicit split-site mode allows only the configured public frontend for GET/POST, without credentials or cross-origin administration.

Both the app and Caddy cap write-request bodies at 8 KB, including bodies without Content-Length. Retain edge resource limits on public deployments. Add an outbound firewall denying internal/link-local/metadata networks as defense in depth: DNS validation is not a substitute for an egress boundary, particularly around yt-dlp's own network stack and optional Chromium. Bound resource ceilings are not a full DDoS solution.

Raw pasted URLs are not persisted. Canonical targets/metadata/CDN addresses stay in a bounded transient cache; download tokens expire with their own TTL. Records are swept every 15s or on resolve, and disappear on restart. Temporary audio files are deleted on completion/failure; periodically clean orphaned system temp files after abnormal termination. Access logging is disabled so token query strings do not enter logs. Aggregate method logs omit content identifiers. Local history is opt-in and can be cleared. Theme preferences are local. The PWA caches only the public interface, never `/api/` responses or downloads.

## Tests

```sh
pytest -q
# Browser tests need installed browser binaries and optional axe dependency:
npm ci
python -m playwright install --with-deps chromium firefox webkit
python tests/browser_check.py
python tests/cross_browser.py
# Isolated static export + local HTTPS fixture backend, no Instagram traffic:
python tests/pages_browser_check.py
# Requires the local server; uses historical public yt-dlp test URLs:
python tests/live_probe.py
```

The original browser scripts use port 8000. `pages_browser_check.py` creates disposable local HTTP/HTTPS servers and does not use real provider accounts. `browser_check.py` injects axe with CSP bypass enabled **only in the audit context**; production CSP remains strict. Cross-browser tests use normal CSP and save actual live MP4s to temporary directories for ffprobe verification, then delete them.

## Maintenance

- Weekly GitHub workflow upgrades yt-dlp in an isolated runner, tests, and opens an update PR. Review live owned fixtures before merging; rebuild/redeploy after merge. No untested package mutation in production.
- Add Actions variable `POCKET_BASE_URL`, secret `POCKET_TEST_URLS` (comma-separated public media you own/are authorized to test), and optional `POCKET_ALERT_WEBHOOK` to enable weekly live health checks. The webhook receives counts, not URLs. No alert is configured until you supply these.
- Failure circuit opens a method for 60 seconds after 5 consecutive upstream/server failures. An operator can disable a broken method at `/ops` immediately, or persist that flag in environment settings.
- Check aggregate success rates and bandwidth/CPU/memory at the host. Cache and circuit breakers reduce work; they do not self-rewrite broken extractors. No bandwidth cost accounting dashboard is included.
- Before scale-out, add Redis, distributed limiting and explicit job isolation. Before launch, run real-device Safari/Chrome/Edge, screen-reader and installed-share-target tests. See report for the exact verification boundary.

## SEO implementation (October 15, 2026)

See **SEO_REPORT.md** for the source audit, fixes, measurements, scorecard and remaining owner tasks; **SEO_GUIDE.md** for production-domain, indexing and Search Console/Bing configuration. Public policies are now separate server-rendered documents. Production metadata, sitemap and robots settings are driven by a validated `PUBLIC_ORIGIN`. No domain was supplied for this preview: it deliberately carries `noindex`, and its sitemap returns 503 until a valid production origin is configured. Set `SEO_INDEXING_ENABLED=false` on staging. Optional verification tokens are `GOOGLE_SITE_VERIFICATION` and `BING_SITE_VERIFICATION`.

Browser/performance QA now uses Node 22.19+ (the website runtime is still Python-only). `scripts/seo_audit.py` checks routes/links/metadata locally; `tests/test_seo.py` tests production and preview branches with an explicitly simulated test hostname. `tests/seo_browser_check.py` covers policy/no-JS/mobile/a11y/CSP/offline-shell behavior. Rebuild/restart after changing server-rendered templates, policy content or frontend files so version hashes and the service worker update together.
#   P o c k e t . g i t h u b . i o  
 