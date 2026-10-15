# Pocket — SEO Audit, Implementation & Validation

**Audited and implemented:** October 15, 2026  
**Scope:** the actual FastAPI application, all public/utility routes, static HTML/CSS/JavaScript, resolver interfaces, PWA, deployment configuration, existing tests and policy content.  
**Status:** safe code fixes implemented and locally validated. Production indexing is **not activated or verified**: no real preferred domain, hosting/account access or Search Console property was supplied.

## Executive result

Pocket retains its original design and downloader. The largest defects were duplicate, client-only policy pages and absent canonical/discovery infrastructure—not a heavy JavaScript framework. Those defects are fixed. The three public documents now have server-rendered content and unique metadata; normal links work without JavaScript. Canonicals, sitemap, schema and absolute social URLs share a single production-origin configuration. Duplicate aliases normalize, unknown paths remain genuine 404s, private utility resources carry noindex, and public text is compressed/version-cached without interfering with downloads.

**95 Python tests pass.** All 3 public pages pass horizontal-overflow checks at 6 widths and the tested light/dark axe checks. Chromium, Firefox and WebKit still save a live MP4 successfully. Current Lighthouse 13.5 mobile homepage runs score **100 Performance / 100 Accessibility / 100 Best Practices**; median lab LCP is **1.04 s**, CLS **0**, TBT **4 ms**.

**Important:** this preview intentionally has `noindex`. Its Lighthouse SEO score is **63**, not 100; policy pages score 66 for the same intentional indexing restriction. `/robots.txt` is 200; `/sitemap.xml` is intentionally **503** until a valid production origin is configured. This is disclosed rather than publishing invented canonical/sitemap URLs or removing staging protection to inflate a score.

---

# A. Audit summary — verified conditions before edits

The mandatory sequence was followed: **discover → inspect → audit → prioritize → plan → implement → validate → test → regression check → report**. The pre-edit plan, route crawl, Lighthouse result and a source snapshot are in `artifacts/seo/`.

| Severity | Verified issue | Affected area | Root cause / disposition |
|---|---|---|---|
| High | `/privacy` and `/terms` return homepage content, title, description and H1 | `app.py`, `index.html`, `app.js` | All three routes serve the same file; actual policy text lives in JS dialogs. Replaced with distinct server-rendered policy documents. |
| High | No preferred production domain is configured; preview had no indexing guard | Configuration / public documents | Only a placeholder domain exists. Added fail-closed preview behavior and explicit production activation; real-domain activation still requires the owner. |
| High | No canonicals; `/index.html` is a 200 duplicate; query variants unconsolidated | Public routes/static mount | No metadata renderer or alias strategy. Added query-free self-canonicals and known one-hop aliases. |
| Medium | `/robots.txt` and `/sitemap.xml` are 404 | Server routes | Neither endpoint exists. Added dynamic, configuration-aware responses. |
| Medium | HEAD returns 404 on valid GET pages | `/`, `/privacy`, `/terms`, `/ops` | GET-only FastAPI handlers fall through to StaticFiles for HEAD. Added correct GET/HEAD routes. |
| Medium | No OG/Twitter metadata or JSON-LD | Public document heads | Brand-only static head. Added page metadata, original social artwork and relevant schema. |
| Medium | API/download resources have no response indexing policy; generated OpenAPI is exposed | API, `/ops`, `/openapi.json` | Ops has a meta noindex, but middleware does not protect other utility responses. Added X-Robots-Tag/no-store and disabled unused OpenAPI generation. |
| Medium | No text compression or explicit static freshness | Public responses / CSS / JS | No compression middleware or versioned asset strategy. Added selective gzip and fingerprinted immutable assets. |
| Medium | Mobile recent-downloads button is unnamed | Header/history button | The text is hidden by mobile CSS, leaving a decorative icon. Explicit accessible name added. Lighthouse Accessibility was 93. |
| Low | Dynamic previews have no explicit dimensional reservations; generic alt fallbacks | Media-card JS/CSS | Added known dimensions, stable preview frames and contextual alt text. |
| Low | Main copy does not clearly name the tool; support copy overstates photos/albums | Homepage | Preserved the brand H1 while adding a descriptive visible tool H2 and precise best-effort guidance. |
| Low | Theme setup waits for the full app JS; legal content is unnecessarily bundled on home | JS / rendering | Extracted policy content to one server-owned data source; tiny early theme code is CSP-hash authorized without an extra blocking request. |

**No verified Critical finding** was identified in this source audit. The existing unknown-URL behavior was a genuine 404, not a blanket SPA soft 404; that behavior was preserved. The homepage already had one H1, a description, a viewport, working responsive styles, system fonts and no visitor-facing third-party scripts. These were not falsely reported as missing.

No pagination, international language variants, editorial articles, local-business profile, product catalog or verified organization identity exists. Pagination/hreflang, Article/Product/LocalBusiness/Person markup and extra keyword landing pages were therefore not added.

# B. Changes implemented

## Technical SEO and routing

- `seo.py` centralizes public-page titles/descriptions, canonical URLs, schema, social metadata, rendering, fingerprints, robots and sitemap generation.
- Public HTML uses a **validated configured `PUBLIC_ORIGIN`**, never a caller-supplied Host or forwarding header, to create absolute URLs. The code rejects placeholder/local/malformed/non-HTTPS origins.
- `SEO_INDEXING_ENABLED=false` keeps staging noindex even when staging has a real hostname. Missing/invalid production origin also keeps preview noindex. Tests cover both production and preview branches.
- `/index.html` → `/`, `/ops.html` → `/ops`, and known policy/admin trailing-slash variants normalize with a single 308. Existing public paths remain stable. Host/scheme/path normalization is combined where requests reach the app; trusted TLS proxy handling avoids a redirect loop.
- Tracking and PWA share queries remain functional; canonicals omit those parameters. No unnecessary redirect removes a shared Reel URL before the app reads it.
- `/robots.txt` permits public crawling and essential assets. With production indexing enabled it advertises the correct absolute sitemap. Admin/API noindex responses remain crawlable so directives can be read.
- Production `/sitemap.xml` contains exactly `/`, `/privacy`, `/terms`. No tokens, admin pages, API routes, assets, fake timestamps or sample URLs are included. Without a valid origin it returns a documented 503 rather than an invalid or invented sitemap.
- GET/HEAD parity is repaired for documents and SEO resources. Unknown pages render a branded **404**, have no canonical, and carry noindex. Raw policy/error templates are not publicly served as duplicate HTML.
- API/download/admin responses have X-Robots-Tag and no-store. Metrics authentication is unchanged. The unused `/openapi.json` is now 404.

## On-page and content changes

- The brand H1 **“Good moments, kept.”** is preserved. A visible **“Instagram media downloader”** H2 and precise introductory copy establish purpose without hiding keywords or replacing the design.
- Privacy and Terms are normal documents with unique titles/descriptions/H1s, H2 policy sections, visible breadcrumbs and related-page links. Their substantive policy language is retained; retention wording now accurately mentions the existing periodic cleanup.
- Footer links are ordinary crawlable navigation, not JavaScript-only policy dialogs. Users without JS can read instructions, FAQs and all policy content; a noscript notice explains that resolving media still needs JS.
- Photos/albums/Stories are described as best-effort; no promise that every public link or quality is available. A useful quality/audio FAQ explains original formats, silent audio failures, permissions and terms.
- Generated image previews receive contextual alt text, known width/height attributes when provided, async decoding and a stable preview area. The sample has a specific mountain-lake illustration description, not a stuffed caption.

### Page-by-page intent map

These are **qualitative intent assignments**, inferred from the actual tool/content—not keyword-volume, competition or ranking research.

| Page | Primary intent / topic | Secondary topics | Implemented title |
|---|---|---|---|
| `/` | Use a free Instagram media downloader | Public Reels/video saving, available photos/carousels, no account, quality/audio, private/login limits | Free Instagram Downloader for Reels & Videos \| Pocket |
| `/privacy` | Understand Pocket's data handling | Pasted links, transient cache, tokens, optional local history, no tracking SDKs | Privacy Policy — Links, Cache & Local History \| Pocket |
| `/terms` | Understand permitted use and rights | Public media access, creator permission, fair use, independent service, technical limits | Terms of Use — Public Media & Creator Rights \| Pocket |
| `/ops` | Operator-only aggregate health | Authenticated metrics and method switches | Kept unique; noindex, not a search landing page |
| Unknown/404 | Recover from a missing URL | Return to downloader/policies | Page Not Found \| Pocket; noindex |

Each indexable-in-production page has its own useful description; none is generated by repeating the same keyword sentence. No fake reviews, testimonials, experience claims, business details, backlinks or search-volume estimates were added.

## Structured data and sharing

- Homepage: **WebSite + WebPage**, using the actual visible Pocket name and configured canonical URL.
- Policy pages: **WebPage + BreadcrumbList**, matching visible Home → current-policy breadcrumbs.
- JSON-LD is server-rendered and covered by the response's CSP hash. No generic search-action schema is invented for a downloader input.
- No unverified Organization, Product offers, aggregate ratings, reviews, Person credentials or creator VideoObject markup.
- Unique OG/Twitter titles and descriptions; production absolute page/image URLs; 1200×630 original brand artwork with image-alt metadata. The optimized PNG is about 32 KB and is not fetched as a homepage hero image.
- No FAQ rich-result promise or unnecessary FAQ schema. The visible FAQ is retained for users.

## Performance and architecture

- Selective gzip applies to public text only. API/media streams, byte-range responses and converted audio are excluded to preserve streaming behavior.
- CSS/JS/icon/social/sample assets use content-derived version URLs. Correct versions receive one-year immutable caching; unversioned/mismatched versions use shorter revalidation. HTML, robots, sitemap and service worker remain revalidatable; admin/API remain no-store.
- Service-worker cache names reflect current assets/content. Installation reloads versioned resources; network-first public HTML supports updates. Only explicit public shell/policy URLs are cached—no API responses or downloaded creator media.
- System fonts remain; no font CDN, font preload pile-up, framework or visitor analytics dependency was added. Required critical CSS remains render-blocking to avoid an unstyled flash; its small compressed size does not justify a brittle critical-CSS rewrite.
- The original JS lost its embedded legal-policy bundle. Theme initialization is tiny, early and CSP-hashed, avoiding an extra render-blocking request.
- Lighthouse is a **development-only** audit dependency, not website runtime code. The initial legacy audit toolchain had reported advisories; it was upgraded to Lighthouse 13.5.0. Final `npm audit` reports **0 advisories**. Its supported Node runtime is 22.19+; the site still runs on Python.

### Modified/new files

| Files | Purpose |
|---|---|
| `app.py` | Public routes, HEAD, aliases, host/scheme normalization, response policies, real 404s, static-template isolation, no OpenAPI |
| `seo.py` | Single source for rendering/metadata/canonicals/schema/sitemap/robots/versioning/compression |
| `static/index.html`, `static/app.js`, `static/style.css` | Visible intent, semantics, normal policy navigation, button name, media stability, preserved styling |
| `content/policies.json`, `static/policy.html` | Single-source substantive policies and server-rendered layout |
| `static/404.html`, `static/theme.js` | Error recovery and hash-authorized early theme initialization |
| `static/social-card.png`, `static/sw.js` | Brand sharing asset and versioned, privacy-preserving shell updates |
| `Dockerfile`, `compose.yaml`, `.env.example` | Include SEO module/content and configure indexing/verification variables |
| `package.json`, `package-lock.json` | Current optional Lighthouse/QA toolchain and repeatable audit commands |
| `tests/test_seo.py`, `tests/seo_browser_check.py`, `tests/browser_check.py` | SEO contracts, whole-site UX/no-JS/CSP/offline checks, updated policy-navigation regression |
| `scripts/seo_audit.py`, `SEO_GUIDE.md`, `README.md` | Repeatable crawl and explicit production/search-console handoff |

The resolver strategy, rights boundaries, authentication, limits and native download mechanism were not rewritten for SEO.

# C. Validation and test evidence

## Automated source/route validation

**95 passed, 0 failed** in pytest: the original 44 backend tests plus 51 additional SEO/configuration cases. One existing Starlette/httpx deprecation warning remains; it is not a failed test.

Validated in a clearly isolated **`pocket.test` production fixture**, not represented as the real domain:

- Unique title/description/H1, one canonical, correct OG/Twitter data per public page.
- Positive production indexing branch with no accidental noindex; separate default-preview/staging noindex cases.
- Sitemap XML parsing, namespace, exactly 3 canonical 200 URLs, no fabricated lastmod.
- Robots accessibility and Sitemap alignment without blocking CSS/JS or hiding noindex directives.
- Known one-hop aliases, HTTPS/host/path normalization, trusted/untrusted forwarding-header behavior, query-preserving share flow.
- True 404s, nonindexable API/admin utilities and disabled OpenAPI.
- JSON-LD syntax/type/property/breadcrumb consistency and exact CSP hashes.
- Crawlable internal links, fragments and resources.
- Public gzip/cache behavior and API-stream exclusion; versioned service-worker privacy rules.
- Optional verification-token rendering; no account verification asserted.

Actual current-preview HTTP crawl finds **0 broken internal links and 0 broken public-page resources**. Public GET/HEAD routes are 200, duplicate aliases 308, unknown/OpenAPI paths 404. The sitemap's 503 is the intentional unconfigured-production condition, not omitted from the findings.

## UX, accessibility and regression

- All `/`, `/privacy`, `/terms` layouts checked at **360, 390, 768, 1024, 1440 and 1920 px**: no horizontal overflow; one H1 per page.
- Axe WCAG 2 A/AA + 2.1 AA: **zero violations in all 6 tested page/theme combinations**. Existing sample-success checks also pass. This is not a WCAG certification or a complete manual screen-reader review.
- All three pages have visible useful content with JavaScript disabled. Policy text is no longer a hidden modal requiring script execution.
- Strict-CSP browser check: theme toggles, persists across policy navigation, and produces no console errors. The audit-only context uses CSP bypass solely to inject axe; normal browser checks do not.
- Offline service-worker test loads the cached Privacy page and confirms no API/media token URLs in the cache.
- Existing flows pass: invalid URL, clear input, sample SVG save, local history, policy navigation, 429 countdown and caption/author HTML escaping.
- Chromium/Firefox/WebKit each save and ffprobe-validate the live Reel MP4 after the SEO changes. Theme and keyboard skip/Escape checks pass; no page errors.
- Source compilation and JavaScript syntax checks pass, including the rendered service worker. There is no frontend production build/lint command in the original project; no nonexistent build result is claimed. Docker is unavailable here, so the updated image/Compose stack was not executed.

## Performance: measured locally, not field Core Web Vitals

### Current Lighthouse 13.5.0 results

Mobile default simulated throttling on `127.0.0.1`, installed Playwright Chromium, cold audit runs. Three homepage runs; single policy/desktop samples. Values are local synthetic observations, not real user traffic.

| Measurement | Homepage mobile median (3) | Privacy mobile (1) | Terms mobile (1) | Homepage desktop (1) |
|---|---:|---:|---:|---:|
| Performance score | 100 | 100 | 100 | 100 |
| Accessibility score | 100 | 100 | 100 | 100 |
| Best Practices score | 100 | 100 | 100 | 100 |
| LCP | **1,041 ms** | 756 ms | 775 ms | 268 ms |
| FCP | 757 ms | 756 ms | 775 ms | 204 ms |
| CLS | **0** | 0 | 0 | 0 |
| TBT | **4 ms** | 0 ms | 0 ms | 0 ms |
| SEO score in intentional noindex preview | **63** | 66 | 66 | 63 |

The only failed binary check in these final audits is `is-crawlable`, caused by the deliberate noindex directive. It does **not** mean robots blocks resources. Removing staging protection simply to improve this number would be an inappropriate change.

### Baseline and comparable observations

The original Lighthouse 12.8.2 baseline was Performance 100 / Accessibility 93 / SEO 100, LCP 1,253 ms, FCP 906 ms, CLS 0 and TBT 13 ms. That shallow SEO score did not discover the duplicate policy pages or missing canonical strategy.

A like-version post-change Lighthouse 12.8.2 run set measured median LCP **1,069 ms**, FCP **1,033 ms**, CLS **0**, TBT **9.5 ms**, with Performance **99/100/100**. FCP was slightly slower than the single baseline, and one TBT sample reached 138 ms while other QA was running; these variations are disclosed rather than cherry-picked. The later 13.5.0 results above were measured after refreshing the audit toolchain and must not be treated as a strictly controlled cross-version speed comparison.

Lighthouse reported total network transfer about **56.2 KB before**, versus **19.6–22.1 KB** across final runs (13.5 median 22.1 KB), with compression/cache findings resolved. Service-worker installation affects which optional shell assets are counted, so this is not an exact JS bundle-size comparison or a promised production speed-up.

**INP is not measured here.** Lighthouse navigation tests provide lab TBT, not field INP; no CrUX or 75th-percentile real-user dataset is available. Current Core Web Vitals targets are LCP ≤2.5 s, INP ≤200 ms, CLS ≤0.1 at the 75th percentile; a local lab pass does not establish production compliance. [1](https://web.dev/articles/defining-core-web-vitals-thresholds) [2](https://web.dev/articles/vitals)

### Evidence locations

`artifacts/seo/` contains:

- `AUDIT-PLAN.md`, `baseline-routes.json`, `before-source.zip`.
- `tests.txt`, `final-crawl.json`, `whole-site-browser.json` and mobile screenshots.
- `browser-regression.json`, `cross-browser-regression.json`.
- Raw before/after Lighthouse JSONs and `performance-summary.json`.
- Final development/runtime npm-audit outputs.

# D. Remaining issues / owner and hosting actions

| Remaining item | Why it cannot be completed here |
|---|---|
| Real preferred HTTPS domain and production indexing activation | No domain supplied; only an example in configuration. Canonicals/schema/social/sitemap are implemented but cannot safely publish actual absolute URLs yet. Preview stays noindex. |
| Production DNS, TLS, owned alternate-domain redirects and proxy headers | Requires your host/DNS and actual deployed URL. Application behavior is unit-tested; Caddy/Compose is not run here. |
| Google Search Console / Bing ownership and sitemap submission | Requires your accounts and verification tokens or DNS changes. Optional meta-token plumbing is implemented, not verified. |
| Actual Google-selected canonical, indexing state, rankings or organic traffic | Requires public deployment and search-engine crawl/report data. No claims made. |
| External schema/social inspection | JSON-LD/source consistency is tested, but no live production Schema Markup Validator, URL Inspection, social crawler or rich-result result was obtained. |
| Field LCP/INP/CLS and real mobile devices | No production CrUX/RUM dataset or physical phones. Playwright WebKit at mobile width is not physical iPhone Safari. |
| Operator identity/contact and rights-request workflow | Legal pages explicitly need customization for the actual operator. No contact/entity was fabricated. |
| Complete media coverage | Existing tool limits remain: public access can be blocked; Stories/login-required/private media and complete mixed-photo albums aren't guaranteed. SEO copy now discloses this instead of promising success. |

No rankings, search volumes, keyword difficulty, backlinks, competitors, ownership, index inclusion or rich results were invented.

# E. Final SEO scorecard — subjective engineering review

**These 0–100 ratings are my qualitative assessment, not official Google scores, ranking predictions or an SEO-tool certification.** They include verification limits. The separate measured Lighthouse results are above.

| Category | Review score | Evidence / remaining deductions |
|---|---:|---|
| Technical SEO | **90** | Rendering, statuses, duplicates, response policy, config tests and public resources fixed. Real-domain/edge/container validation remains. |
| On-page SEO | **93** | Unique useful metadata, one H1, descriptive visible tool H2, logical policy headings, ordinary navigation and accurate FAQ. No demand/ranking data was available. |
| Content quality | **80** | Clear concise utility/policies and transparent limits; no filler or fabricated proof. Real operator details and representative media-coverage validation still needed. |
| Performance | **94** | Current lab Performance 100, median mobile LCP 1.04 s, CLS 0, TBT 4 ms; compression/versioning implemented. No field INP/production-host evidence. |
| Mobile usability | **94** | 18 public-page viewport checks plus 3-engine download regression, visible labels and zero tested axe violations. Physical phone/save-sheet/screen-reader review remains. |
| Structured data | **88** | Accurate server-side WebSite/WebPage/BreadcrumbList, syntax/CSP/URL assertions pass. Absolute markup is intentionally withheld without a real origin; external deployed validation remains. |
| Crawlability and indexability | **60 — current preview** | Public HTML/links/robots are accessible and production contracts pass, but the current deployment intentionally cannot be indexed and has no production sitemap yet. Do not interpret this as launch-ready indexing. |

No averaged overall score is provided: a high average must not conceal the missing production origin/indexing activation.

# F. Priority action plan

| Priority | Next action | Expected benefit | Effort |
|---|---|---|---|
| P0 | Supply/configure the real preferred origin; keep staging noindex, enable production indexing only on the real host | Valid live canonicals, schema/social URLs, production sitemap and indexability | Low configuration + owner decision |
| P0 | Deploy updated container/module/content; verify real TLS, trusted proxy behavior, redirects and SEO responses | Prevent hosting-layer redirect loops, missing assets and incorrect response directives | Medium hosting/staging check |
| P1 | Verify Search Console via DNS or supplied HTML token; submit sitemap and inspect 3 public URLs | Search-engine discovery, crawl diagnostics, canonical/indexing evidence | Low owner action; external propagation/crawl time varies |
| P1 | Add real operator contact and rights-request details; retest representative permitted media | Trust and accurate product/legal expectations | Low–medium; requires actual operator facts |
| P1 | Run production PageSpeed/CrUX checks plus physical iPhone/Android downloads and installed share-target test | Real field/per-device evidence beyond local lab results | Medium |
| P2 | Validate deployed JSON-LD with Schema Markup Validator and inspect social cards | Confirm public crawler access and appearance metadata | Low |
| P2 | Verify/import Bing property and submit the same sitemap | Additional search-engine discovery/diagnostics | Low owner action |
| P2 | Monitor indexing/performance and extract real search queries before proposing new pages | Evidence-led content improvements without doorway-page sprawl | Ongoing, after crawl data exists |

Full activation instructions and repeatable commands are in **SEO_GUIDE.md**. Keep the noindex safeguard until the actual production configuration is ready.

## Documentation consulted / implementation rationale

- Canonicals are provided in raw HTML and share the sitemap's configured preferred URLs. [1](https://developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls)
- Noindex requires a crawler to access the response; robots.txt is not used as an indexing-removal mechanism. [2](https://developers.google.com/search/docs/crawling-indexing/block-indexing)
- Homepage WebSite name/url match the visible brand and canonical root; site names are not a promised rich result. [3](https://developers.google.com/search/docs/appearance/site-names)
- Also reviewed current Google sitemap-building and Search Console ownership documentation while preparing the owner handoff; no external verification was attempted without ownership access.
