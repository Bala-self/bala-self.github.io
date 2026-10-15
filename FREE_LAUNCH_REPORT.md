# Pocket — free-launch implementation and verification

**15 October 2026 · source inspection + official hosting documentation + local validation**

## Verdict

A practical **GitHub Pages public frontend + Render Free backend** hobby-deployment preset is now implemented, with a beginner guide in **FREE_LAUNCH_GUIDE.md**. It avoids paid domains, paid scraping APIs and mandatory local developer tools.

**Not yet published:** no actual GitHub username, repository, production address or account access was supplied. The GitHub connector lookup returned unsupported; no repository was created and no deployment/account settings were changed. Search Console ownership, sitemap acceptance, Google indexing and real host billing remain unverified. This is not a 100%-uptime, unlimited-capacity, legally cleared production service.

## Source gaps found and changes made

| Verified gap | Implemented change |
|---|---|
| GitHub Pages cannot run the Python app; raw index.html contains SSR placeholders | `scripts/export_pages.py` produces only finished public HTML, assets, policies, custom 404, manifest, robots, sitemap and service worker. No Python source, admin page or secrets enter the public deployment artifact. Source remains public in the repository by design. |
| Client assumed same-origin `/api` and relative token URLs | New versioned `static/client-config.js`; client resolves API/media URLs against the configured HTTPS backend while preserving the default same-origin mode. |
| No approved cross-origin transport | Explicit `ENABLE_CROSS_ORIGIN=true` enables exact validated frontend-origin CORS for GET/POST, without credentials, wildcard origins or cross-origin admin PATCH. Origin casing/default ports are normalized. Default mode remains same-origin. |
| Render TLS proxy can conflict with canonical document redirects | Public backend documents point toward the configured frontend; API paths bypass canonical-document redirects. Backend `/ops` and its self-hosted assets remain usable without trusting arbitrary forwarding headers. |
| Existing Docker image installs Chromium and has a fixed port | `Dockerfile.free` excludes optional browser/test packages, retains pinned runtime versions and FFmpeg, runs nonroot, and launches a single worker through `scripts/start_free.py`, honoring the platform's PORT. Original Docker/Compose route remains available. |
| No beginner cloud configuration | `render.yaml` contains an optional Free Blueprint; `.github/workflows/pages.yml` exports/deploys the root user Pages site from main using repository variables. Manual setup is fully documented. |
| GitHub directory URLs differ from FastAPI policy routes | Exported canonical/schema/internal policy links, sitemap and offline shell use `/privacy/` and `/terms/`; default FastAPI URLs are unchanged. No existing public site/domain was supplied or migrated. |
| Static host cannot attach the app's security response headers | Export embeds hashed-script CSP and no-referrer metadata. It admits only the configured backend for API/images/media. Unsupported meta `frame-ancestors` is omitted; **full custom HTTP-header parity is not claimed**. |
| Sleeping backend can return HTML before API JSON is ready | User-triggered health/wake retries and an explanatory loading state; no page-load keep-awake polling. |
| Cross-origin native attachment opened instead of saved in WebKit | Split mode uses the existing bounded fetch/progress/Blob download path; default same-origin originals retain native streaming. The free preset caps server files at 100 MiB; split-mode client buffering can strain phones. Oversize native fallback opens separately rather than replacing the website. |
| Render path lacks the Caddy request-body ceiling | App now bounds write bodies, including requests without Content-Length, to 8 KiB before route processing. |
| Small free backend needs explicit resource limits | Configurable active-media ceiling (default remains 12); free preset sets 2 active media requests, 1 resolver and a 100 MiB server ceiling. No signup, forced ads, paid tier or daily quota was introduced. |
| Existing instructions said static split was not wired | README/environment documentation now describes both modes and links the current beginner guide. |

## Validation performed

- **105 pytest tests passed**, including 9 new free-launch tests: static content/metadata/CSP hashes, policy canonical/schema/sitemap agreement, backend configuration/service worker generation, rejected invalid export settings, chunked body ceiling, and a fresh-process split-profile CORS/origin/ops-assets regression check.
- One **Starlette TestClient deprecation warning** remains; it is not a failed test.
- **Chromium, Firefox and WebKit** passed exported-interface tests against a **local HTTPS fixture backend**: cross-origin health/resolve, a simulated cold-start retry, image preview, file saving with the attachment filename, policy navigation and theme switching. No page JavaScript errors; no horizontal overflow at the tested 390/1440-pixel viewports.
- Chromium additionally verified exported policy navigation offline and that the public shell caches configuration/policies but not API responses or media.
- Reran the original same-origin SEO browser regression: **18 page/width checks**, **6 page/theme axe checks with zero violations**, no-JavaScript content, strict-CSP theme interaction and offline privacy-page checks passed.
- Python compilation and JavaScript syntax checks passed. Both new cloud YAML files parsed successfully. **Parsing is not provider-side deployment validation.**

Evidence logs are in the workspace; the clean upload ZIP intentionally omits QA artifacts. Evidence: `artifacts/free-launch/tests.txt`, `export-browser.json`, `export-browser-output.txt`, `same-origin-browser.txt`; underlying SEO browser JSON remains under `artifacts/seo/`. Browser fixture URLs and disposable TLS certificates were only used locally, not deployed or shipped as live production configuration.

### Verification boundary

Docker is unavailable in this workspace: the new image was **not built or run**. Neither the Pages workflow nor Render settings have been executed in a real account. No new live Instagram download was attempted as part of this launch work; browser transport tests used a locally authored image fixture, not fabricated Instagram success. Real-device tests, actual platform deploys, an authorized Instagram download, saving the actual returned file, external Google crawl checks and account billing review are still owner actions. Earlier SEO/Lighthouse reports are historical, not fresh production performance measurements.

## Official-resource findings that affect this design

- Render Free sleeps after 15 idle minutes, wakes in about a minute, supplies 750 shared workspace instance hours/month, and may suspend for unusually high service-initiated public-internet traffic. While asleep, `/robots.txt` returns a disallow-all response without waking. Render explicitly discourages production use of free instances. [1](https://render.com/docs/free)
- Render can bill supplementary bandwidth/build usage when a payment method exists; without one, its documented behavior is suspension/build disablement rather than the supplementary charge. No-card free settings reduce billing risk but do not provide capacity or availability guarantees. [1](https://render.com/docs/free)
- GitHub Pages is static hosting, available for public repositories on GitHub Free, subject to site/bandwidth/policy limits. It is not allowed as hosting for an online business/commercial SaaS. This preset does not constitute host-policy approval. [1](https://docs.github.com/en/pages/getting-started-with-github-pages/creating-a-github-pages-site) [1](https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits)
- Standard GitHub-hosted runner usage for public repositories/Pages is free; paid larger runners and additional storage/services are outside this preset. [1](https://docs.github.com/en/billing/concepts/product-billing/github-actions)
- Search Console supports URL-prefix verification through an HTML tag. Submitting a sitemap or requesting indexing does not guarantee indexing or ranking. [1](https://support.google.com/webmasters/answer/34592?hl=en) [5](https://support.google.com/webmasters/answer/9008080?hl=en) [1](https://support.google.com/webmasters/answer/7451001?hl=en) [1](https://support.google.com/webmasters/answer/9012289?hl=en)

## Remaining owner decisions and risks

1. Resolve the access/copyright/music/privacy/operator/contact/complaints issues documented in **LEGAL_RISK_REVIEW.md**. Free/public/disclaimers do not supply permissions.
2. Supply actual accounts and origins and follow **FREE_LAUNCH_GUIDE.md**; never overwrite an existing root Pages site without planning its URLs.
3. Verify Free/no-payment-method account settings and current host policies. Resource exhaustion, shared-IP throttling, data-center IP blocks and service suspension can make downloads unavailable even when the frontend is online.
4. Keep optional browser fallback disabled in this small image. Do not enable admin browser flags expecting Chromium to be installed.
5. Keep a single worker/replica; tokens/caches/limits remain in memory and reset on restart. Without a documented trusted-proxy configuration, per-peer limits are deliberately conservative and can aggregate visitors behind the host proxy.
6. Validate actual deployments and files, then verify Search Console and monitor results. No guarantee of every link, unlimited use, zero future costs, permanent free offerings, legal clearance or Google inclusion is made.
