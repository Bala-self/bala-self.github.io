# Pocket — Implementation & verification report

**Date:** October 15, 2026  
**Delivery status:** Working, tested release candidate with live preview. Not an audited/guaranteed production service. No claim of universal Instagram access.

## 1. What was built

- Responsive, centered paste-and-download UI: warm neutral/forest/lime design, light/dark themes, local sample mode, loading skeleton, URL validation, specific errors, retry countdown and media cards.
- Format chips, grouped carousel items, proxied image/video previews, native streaming original-file downloads and optional real MP3 conversion.
- Opt-in recent resolved links stored on the device only; no user accounts or tracking SDKs.
- Compact mobile input dock after the main input scrolls away; keyboard skip link, visible focus treatments, dialog Escape support and reduced-motion CSS.
- PWA manifest, PNG icons, GET share target and network-first shell service worker. API responses/media are excluded from the offline cache.
- FastAPI resolver/gateway, bounded concurrency, short metadata cache, opaque expiring media tokens, destination checks and byte-range pass-through.
- Aggregate operations dashboard at `/ops`, protected metrics and immediate authenticated runtime method switches.
- Terms and Privacy routes, rights/fair-use advisory and non-affiliation notice; no forced consent wall.
- Dockerfile, TLS reverse-proxy Compose configuration, environment template, update workflow, live-health script and test suite.

## 2. Fetch methods: actual implementation

| Order | Method | Implemented behavior | Verified boundary |
|---|---|---|---|
| 1 | **B: yt-dlp** | Python worker using the maintained Instagram extractor; reads formats/playlist metadata, maps supported direct assets into the API contract. | Resolved 2 historical live public fixtures. |
| 2 | **A: public HTML/embed** | Fetches canonical embed/captioned URL; parses JSON-LD, JSON script trees, historical shared-data wrappers, carousel nodes and OG video. Rejects generic OG-thumbnail-only pages. | Structured-data and mixed-carousel fixture tests pass. Direct live attempt on one fixture failed upstream. |
| 3 | **C: Playwright, opt-in** | Renders a public page then parses its DOM/structured data; only allowlisted public destinations, no user cookies or challenge solving. | Direct live attempt on one fixture reached a login-required response. Cascade behavior verified with controlled failures. |
| — | **D: aggregator** | Evaluated, not configured. | No paid API, external key or provider URL disclosure. |

**Default chain is B → A. Set `ENABLE_BROWSER=true` for B → A → C.** The renderer is installed in the supplied Docker image, but disabled unless configured. An explicit upstream rate limit or private-account result stops the chain rather than trying to evade it.

Why B first: maintained extractor coverage with less custom maintenance. A provides an inexpensive independent markup strategy. C may help with public JS-rendered metadata, but is slower and not a reliable answer to login gates. D adds ongoing cost and another data recipient, so it is not part of the free/private default.

Important distinction: fallback/circuit-breaker automation is implemented; **self-repairing extractor code is not**. Upstream structural changes still need reviewed updates.

## 3. Actual live results

Historical public URLs were taken from the installed yt-dlp Instagram extractor test definitions. Their current content availability was not independently certified. These results describe this host and this test session, not a general success-rate estimate.

| Live input | Resolution | Engine | Initial latency | Observation |
|---|---|---|---:|---|
| `https://www.instagram.com/p/BQ0eAlwhDrw/` | **200** | yt-dlp | 1.69 s | Caption/date and a carousel of 3 extracted video groups. Six selectable records when MP3 options are counted. |
| `https://www.instagram.com/reel/Chunk8-jurw/` | **200** | yt-dlp | 1.69 s | One original MP4 and an optional audio-conversion action. |
| `https://www.instagram.com/tv/BkfuX9UB-eK/` | **403** | no success | 1.00 s | Human-readable `login_required`; no credentials requested. |

**Metadata resolutions: 2/3 (66.7%), sample size only 3.** This is not evidence of general reliability for Stories, photos or all carousels.

### Actual file verification

The live Reel was downloaded through `/api/download`:

- HTTP **200**, attachment filename `pocket-Chunk8-jurw-1.mp4`.
- **918,120 bytes**, valid MP4/container detected by ffprobe.
- H.264 video, **480 × 854**, approximately **4.97 seconds**.
- No audio stream in this fixture. MP3 conversion returned **422** with a specific no-usable-audio message, not a mislabeled MP4.
- Chromium, Firefox and WebKit each saved the live MP4; ffprobe confirmed a video stream for all three saved downloads.
- No downloaded creator files are retained in project artifacts. Test files were removed after inspection.

The implementation does not invent 1080p options, upscale a source or claim it has all original renditions. It presents original quality when the extractor supplies no dimensions.

### Independent live fallback checks

On the first post fixture, Method A returned **502/upstream** in 0.35 s; Method C returned **403/login_required** in 3.05 s. These are recorded honestly as failures, not fallback successes. The default primary succeeded separately.

Evidence: `artifacts/live-results.json`, `artifacts/live-downloads.json`, `artifacts/live-fallbacks.json`, `artifacts/cross-browser.json`.

## 4. Automated backend verification

**44 tests passed**, one dependency deprecation warning, no test failures.

Covered:

- Post, Reel/reels, IGTV, Story and Highlight URL branches and canonicalization.
- Rejecting non-HTTPS, deceptive hostname suffixes, credentials, private IP URLs, unexpected ports/paths and unsupported profile links.
- Media domain checks and private DNS rejection.
- Forced B failure followed by A success; forced B/A failures followed by C success.
- No fallback around an upstream 429.
- JSON-LD video, structured mixed image/video carousel, explicit private data and generic-thumbnail rejection.
- Metadata cache reuse, grouping contract, CDN URL non-disclosure and token expiry.
- Attachment streaming, file bytes and content type, rejecting HTML masquerading as media.
- Burst limiter: 12 accepted invalid-input checks followed by 8 friendly 429s in a 20-request controlled burst.
- Cross-origin rejection, unauthenticated metrics protection and security headers.
- Circuit opening after consecutive upstream failures.
- Concurrent same-key lock serialization and cleanup.
- **Actual FFmpeg conversion** of a locally generated synthetic audio/video fixture to an MP3 with an ID3 header.
- Authenticated runtime flags and unauthenticated rejection.
- HTTP 206 and single byte-range pass-through.

The burst test validates limiter behavior; it is **not** a high-volume infrastructure load test.

Evidence: `artifacts/backend-tests.txt`, `tests/test_backend.py`.

## 5. Responsive, accessibility & browser checks

### Responsive layout

Chromium layout checks passed at **360, 390, 768, 1024, 1440 and 1920 px**, with no horizontal overflow. Real carousel output was also checked at mobile width. Screenshots are included under `artifacts/`.

### Accessibility

Axe WCAG 2 A/AA and WCAG 2.1 AA checks found **zero violations** in the tested light idle, dark idle and light sample-success states. Initial muted-text contrast failures were fixed and the audits rerun. Keyboard skip-link focus, dialog Escape dismissal and accessible URL/clear/theme controls were exercised. Reduced-motion behavior is included in CSS.

This is not a complete WCAG certification or a manual screen-reader audit. The axe run used test-only CSP bypass to inject its audit script; the delivered site keeps a strict self-only script policy.

### Browser execution

| Engine | Width | Sample SVG saved | Live MP4 saved & probed | Theme / keyboard | Page errors |
|---|---:|---|---|---|---:|
| Chromium | 390 | Pass | Pass | Pass | 0 |
| Firefox | 1440 | Pass | Pass | Pass | 0 |
| WebKit | 390 | Pass | Pass | Pass | 0 |

A repeated Blob-download problem was found in Firefox and fixed by using native browser downloads for original media. This preserves browser streaming and user activation instead of buffering large videos in JS memory. Progress for these originals is shown by the browser download manager. The app shows preparation/transfer progress for fetched sample/audio downloads where possible.

Additional executed UI flows: inline invalid URL, clear input, explicitly labeled demo, opt-in history dialog, Privacy dialog, 429 countdown/retry and malicious-looking caption/author text rendered without execution.

**Not executed:** branded desktop Edge, physical iPhone Safari/Android Chrome, installed PWA share delivery from the Instagram native app, OS-specific save sheets, VoiceOver/NVDA, offline installation lifecycle across upgrades, or deployed TLS/CORS on a production domain. Playwright WebKit at 390px is not a claim of testing a real iPhone.

Evidence: `artifacts/browser-results.json`, `artifacts/cross-browser.json`, `tests/browser_check.py`, `tests/cross_browser.py`.

## 6. Security, privacy & operating safeguards

Implemented:

- Strict Instagram HTTPS input allowlist, canonicalization, supported-path branching.
- Server-owned media tokens; no arbitrary media-URL query endpoint.
- Allowlisted media hosts, public DNS checks and redirect revalidation on the custom fetch/stream path.
- Per-IP token buckets, bounded queues/concurrency, byte ceilings and short-lived tokens/cache.
- Optional trusted-proxy IP allowlist; default does not trust caller forwarding headers.
- Captions rendered as text; no third-party keys/client tracking SDKs.
- Same-origin write checks, strict CSP, no-sniff, no-referrer and configured-production HSTS.
- No API/media caching by the service worker, no access logs in launch/Docker commands, aggregate-only method metrics.
- Optional MP3 uses temporary files, cleans normal success/failure and kills timed-out FFmpeg processes.

Deployment obligations:

- Keep the supplied Caddy body-size limit or an equivalent edge limit, including chunked requests.
- Enforce outbound firewall rules blocking private/link-local/cloud-metadata networks as additional SSRF protection, particularly for yt-dlp's own network stack and Chromium. Application DNS checks alone are not a formal rebinding-proof egress sandbox.
- Use one worker until state/rate buckets are distributed. Add resource/egress monitoring and an edge abuse/DDoS layer for a public service.
- Review dependency pins, legal pages, hosting policies and contact/rights-request process before launch.

No rotating residential proxies, CAPTCHA solving, user-agent evasion pool or account/session-cookie collection was added. A consistent browser-compatible user-agent is used. Upstream restrictions are surfaced, not circumvented.

## 7. Known limitations and completion boundary

1. **Public access is best-effort.** Even a public post can require login from a particular hosting IP. Private media is unsupported by design.
2. **Stories/Highlights:** URL branching and explicit best-effort/login errors exist. No successful live Story or Highlight was verified; no session mechanism is implemented.
3. **Photos/mixed albums:** Parser and UI support direct images and mixed groups and fixture tests pass. No live single-photo or mixed-image/video album success was verified. yt-dlp is video-oriented and can omit photos; complete album coverage is not guaranteed. The three-video live fixture does not prove mixed-carousel completeness.
4. **Metadata can be incomplete:** Missing author, date, caption, dimensions or quality variants cannot be reconstructed reliably. High-resolution source availability is not guaranteed.
5. **Audio:** Only offered with FFmpeg installed; silent sources can still fail conversion. No separate live audio-bearing fixture was verified. MP3 needs transient server disk and has resource ceilings.
6. **Native file failures:** Once a native download is handed off, the browser owns progress/error presentation. Expiry is checked on the client and server, but a later CDN failure may appear as a browser download failure rather than an in-card retry.
7. **Loading status:** Skeleton and elapsed-time messaging are implemented; this is not a server-pushed SSE per-method progress stream.
8. **Single-process state:** In-memory cache/locks/tokens/limits/flags; no Redis or distributed deployment implemented. Restart expires issued links. Cleanup runs every 15s as well as on resolve.
9. **Maintenance:** Update PR and health workflow code supplied; no external repository, Actions schedule, webhook or production host has been configured in this session. Operator activation is required.
10. **Deployment:** Docker/Compose files supplied but not executed because Docker is unavailable here. Local Python app and browser tests were executed. No production domain/TLS deployment is claimed.
11. **Monitoring:** Aggregate method dashboard and runtime switches work; persistent bandwidth/cost accounting and a full observability stack are not included.
12. **Legal:** Baseline advisory pages are included but must be customized for the actual operator and jurisdiction. Public availability does not authorize redistribution.

These boundaries are deliberate disclosures, not features hidden behind a future paid tier.

## 8. Deployment & maintenance handoff

Full commands and all environment variables are in **README.md**. Recommended initial deployment: single VPS, one FastAPI worker, Docker, Caddy HTTPS, optional renderer off, measured resource limits. No third-party API secrets or Instagram credentials are needed. Set `DOMAIN`, `PUBLIC_ORIGIN` (Compose derives it), and `METRICS_TOKEN`; configure trusted proxy addresses appropriately.

Weekly: run owned public fixtures, review aggregate success by method, accept tested yt-dlp update PRs and rebuild the image. Alert configuration requires `POCKET_BASE_URL`, `POCKET_TEST_URLS` and optional `POCKET_ALERT_WEBHOOK`. If a method breaks, disable it immediately in `/ops`, persist its environment kill switch, investigate and re-enable after validation. Do not auto-install unreviewed updates into the running container.

Before calling this a production launch: run the supplied container stack in staging, verify external HTTPS and headers, configure egress/abuse safeguards and legal contact details, test representative authorized public photos/mixed albums, test real phones and installed share-target behavior, and measure sustained throughput/bandwidth costs.
