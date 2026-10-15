# Pocket SEO deployment & search integration

## Current state: intentional preview mode

No real preferred domain was supplied during the audit. The live preview therefore returns `noindex, follow` on public HTML, omits canonical/absolute social/schema URLs, and returns a clear **503** for `/sitemap.xml` instead of publishing guessed or relative sitemap URLs. `/robots.txt` is **200** and allows crawling so a crawler can see the noindex rules. This is deliberate staging protection, **not** a claim that the site is ready to be indexed now.

## Turn on production SEO

1. Choose the exact HTTPS origin you control, including whether `www` is preferred. The app supports an origin, not a subdirectory deployment. Do not use an Arena preview URL as a permanent canonical.
2. Configure DNS and HTTPS on your actual host. In Compose, set the real `DOMAIN` in `.env`; `PUBLIC_ORIGIN` is derived as `https://${DOMAIN}`. On another host set `PUBLIC_ORIGIN` directly to your exact preferred HTTPS origin.
3. Set `SEO_INDEXING_ENABLED=true` on the production service, **false on staging**. Missing, HTTP, placeholder, local and malformed origins keep the site in preview mode. This validation intentionally rejects `.test`, `.invalid`, `.example`, loopback/IP hosts and the example domains in documentation.
4. Rebuild/restart after editing environment variables, templates, policies or frontend assets. Document templates, fingerprints and public origin are loaded at startup. Docker needs the new `seo.py` module and `content/` directory; the Dockerfile already copies them.
5. On the real domain verify:
   - `/`, `/privacy`, `/terms`: 200, exactly one title/description/H1/canonical, no noindex in meta or headers.
   - Self-canonicals exactly match your preferred origin and paths, without tracking/share query strings.
   - `/robots.txt`: 200, public assets allowed, correct absolute Sitemap line.
   - `/sitemap.xml`: 200, XML, exactly these 3 public canonical URLs and no admin/API/download/example URLs.
   - `/index.html` → `/`, `/ops.html` → `/ops`, known policy trailing slash → slashless path, single 308 hop.
   - Unknown paths remain 404; admin/API/download responses remain noindex.
   - CSS/JS/PNG/SVG versioned assets load, CSP has no violations, and a real file download works.
6. Redirect any old public domains or owned www/apex aliases at your edge in one hop to the same preferred HTTPS URLs. Only configure domains you own. The app normalizes known-resource host/scheme/path requests that reach it, but **Caddy/DNS must accept an alternate hostname first**. No unverified www/apex DNS alias was added.
7. Keep `TRUST_PROXY_IPS` correct. A trusted TLS-terminating proxy supplies `X-Forwarded-Proto`; trusting no proxy behind a real HTTPS reverse proxy can cause HTTPS redirect loops. The Compose network configuration already trusts only Caddy's exact IP. Do not trust arbitrary forwarding headers.

The sitemap deliberately has no `lastmod` field rather than falsely updating every URL on every request. Generated metadata uses the same source as the document routes, so sitemap, canonicals and social URLs stay aligned.

## Google Search Console — owner action required

No verification, sitemap submission, indexing or ranking has been performed or claimed.

1. Open Google Search Console under your own account and add a **Domain property** for the real domain.
2. Add the exact DNS TXT record supplied by Google at your DNS provider. Wait for DNS propagation and use **Verify**. Preserve the record after verification.
3. Alternatively, add a **URL-prefix property** for the preferred HTTPS origin and select HTML-tag verification. Copy only the token from Google's meta `content` value into `GOOGLE_SITE_VERIFICATION`, restart the app and confirm the homepage's raw source contains it. This project supports the HTML-tag method, not automatic verification or arbitrary verification-file upload.
4. In **Sitemaps**, submit `sitemap.xml` only after the production response is 200 with correct absolute URLs.
5. Use URL Inspection → Live Test on the homepage and the two policy pages. Confirm crawling is allowed, rendered content matches visible pages, and no staging noindex remains. Request indexing if appropriate.
6. Monitor Page Indexing, sitemap processing, Core Web Vitals and Performance reports. A submission/request is not a guarantee of indexing or rankings. Review Google-selected canonicals after crawl data is available.

## Bing Webmaster Tools — optional owner action

Add/verify your real property using Bing's available DNS method or import the verified Search Console property if your account offers it. For HTML meta verification, put Bing's token into `BING_SITE_VERIFICATION`, restart and check `msvalidate.01` in the homepage source. Submit the same production sitemap. No Bing account was accessed in this audit.

## Structured-data checks

With a valid PUBLIC_ORIGIN configured, the homepage emits WebSite + WebPage JSON-LD; policy pages emit WebPage + BreadcrumbList matching the visible breadcrumb navigation. No business identity, ratings, product offers, personal biography or third-party creator VideoObject is invented.

JSON syntax, required site-name properties, breadcrumb order, canonical consistency and CSP hash compatibility are covered by local tests. Paste the production source into Schema Markup Validator for a full vocabulary review and use URL Inspection after deployment. Google's Rich Results Test does not test every schema type or guarantee a search feature. No rich-result eligibility or appearance is promised.

## Analytics & privacy

No analytics tracker was added. This preserves Pocket's existing no-tracking posture and privacy policy. Start with Search Console/Bing search-performance reports plus aggregate host metrics. If you later choose visitor analytics, assess legal/consent and retention requirements, do not send pasted Instagram URLs, captions or download tokens as events, and update Privacy before enabling the integration. There is no reason to add GA/Tag Manager solely for a superficial SEO score.

## Performance measurements & rechecks

Python serves the application; **Node is only for optional local browser/audit tooling**. The updated Lighthouse toolchain needs Node **22.19+**. No Node dependency is sent to visitors or included in the Python runtime image.

```sh
pip install -r requirements.lock
npm ci  # Node 22.19+ recommended
python -m playwright install --with-deps chromium firefox webkit
pytest -q
python scripts/seo_audit.py http://127.0.0.1:8000
python tests/seo_browser_check.py
python tests/browser_check.py
python tests/cross_browser.py  # also reaches historical live Instagram fixtures
# Set CHROME_PATH to the installed Chromium binary, then:
npm run audit:mobile -- http://127.0.0.1:8000/
```

The test scripts expect the application running on port 8000. The strict production CSP is preserved; only the axe audit context enables test injection. No physical phone, field INP, CrUX dataset, production TLS or live Google/Bing index state is represented by these local tests.

After deployment, run PageSpeed Insights on the real public URL and inspect any available CrUX field data. Collect real-user measurements only if needed and consistent with Privacy. Lighthouse measures lab LCP/CLS and TBT, **not field INP**. Local synthetic metrics are not proof that the production site's 75th-percentile Core Web Vitals pass.
