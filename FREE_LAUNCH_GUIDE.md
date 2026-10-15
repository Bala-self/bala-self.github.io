# Pocket: free public launch, from GitHub to Google

**Beginner guide · checked 15 October 2026**

## The honest answer first

You can attempt a **₹0 hosting setup for a small public hobby project**, without buying a domain, paying for an API, or paying Google. The code and configuration for that setup are now included.

**It is not an unlimited, always-working production service.** Render explicitly says its free instances are not for production applications. They sleep, have usage limits, and can be suspended. Instagram can block downloads. Google decides whether to index a page. No code change can honestly guarantee otherwise. [1](https://render.com/docs/free)

Free hosting does **not** resolve the legal issues in `LEGAL_RISK_REVIEW.md`. Before public release, resolve access permissions, add your real operator/contact and complaint information in `content/policies.json`, and review copyright/music/privacy obligations. Do not invent these details. Review the host rules too; GitHub Pages is not permitted as hosting for an online business/commercial SaaS. This preset is for a noncommercial hobby project, not permission to operate any particular service. [1](https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits)

## 1. Understand the three pieces

```text
Your files on GitHub
    ├── GitHub Actions → GitHub Pages → public website
    │                                  https://USERNAME.github.io
    └── Render Free → Python downloader backend
                     https://YOUR-SERVICE.onrender.com

Google reads the public GitHub Pages website.
When a person submits a link, the website contacts the Render backend.
```

- **GitHub repository:** stores your source files.
- **GitHub Pages:** serves the public website and its Google-readable pages. It cannot run the Python downloader. [1](https://docs.github.com/en/pages/getting-started-with-github-pages/creating-a-github-pages-site)
- **Render Free:** runs Python and FFmpeg. The lightweight image omits optional Chromium.
- **Google Search Console:** lets you verify the website and submit its sitemap; it does not promise indexing. [1](https://support.google.com/webmasters/answer/7451001?hl=en)

**Why two hosts?** Render sleeps after 15 minutes without inbound traffic. Waking takes about a minute. While asleep, its `/robots.txt` returns `Disallow: /` without waking the service. Keeping the public pages on GitHub Pages avoids making their crawlability depend on that sleeping backend. It does not keep downloads always available. [1](https://render.com/docs/free)

**No local coding tools are required for the steps below.** You need a browser, GitHub account, Render account and Google account. Menus may change; the exact configuration values below are the important part.

## 2. Download and upload the project to GitHub

1. Download **`pocket-free-launch.zip`** and extract it on your computer.
2. Sign in to GitHub. Note your actual **username**. `USERNAME` below always means that username, not the word “USERNAME”.
3. Create a **Public** repository named exactly:
   ```text
   USERNAME.github.io
   ```
   If your username were `yourname`, the repository would be `yourname.github.io` and your website would be `https://yourname.github.io`. Use your own username; these are illustrations, not assigned URLs.
4. Use **upload an existing file**, or **Add file → Upload files** if the repository already has a README. Upload the **contents of the extracted folder** to the repository root. Do not upload the ZIP itself, and do not put everything inside an extra `pocket/` folder.
5. Include the hidden `.github` directory. Enable hidden-file display on your computer if needed. Commit the upload to the **`main`** branch.
6. Check that GitHub shows these exact paths:
   ```text
   app.py
   seo.py
   Dockerfile.free
   requirements.lock
   render.yaml
   static/app.js
   static/client-config.js
   scripts/export_pages.py
   scripts/start_free.py
   .github/workflows/pages.yml
   ```

**Do not upload `.env`, credentials, browser cookies or passwords.** The supplied `.env.example` contains examples, not your secrets. Your source repository will be public.

**Already have a `USERNAME.github.io` repository/site? Stop before replacing it.** GitHub permits one user site per account. This simple preset requires the origin-root site and does not implement a `/repository/` project-site prefix. Preserve any existing website and URLs; ask for an adapted deployment instead. [1](https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits)

An initial failed “Publish free public website” workflow is expected if you have not set the backend URL yet. Complete the next steps, then run it again.

## 3. Create the free Render backend

1. Sign up/sign in at **https://dashboard.render.com/**. Choose the no-monthly-fee workspace option available to you. **Do not add a payment method or select paid resources for this ₹0 plan.** If account verification requires something you do not want to provide, stop; do not bypass it.
2. Select **New → Web Service** and connect the GitHub repository you just created. Grant Render access only to the repository it needs. This connection happens in your own browser.
3. Choose the following settings. The official first-deploy flow supports free services. [1](https://render.com/docs/your-first-deploy)

   | Setting | Choose |
   |---|---|
   | Branch | `main` |
   | Runtime / Language | **Docker**, not Python |
   | Root directory | Leave blank |
   | Dockerfile path | `./Dockerfile.free` — **not** the original `Dockerfile` |
   | Compute / Instance type | **Free** |
   | Health check path | `/api/health` |
   | Region | An available free region |

4. In **Environment**, add these values. Replace only the username in the first line. If an “Add from .env” bulk-entry option exists, paste this block there; otherwise add each row separately:

   ```dotenv
   PUBLIC_ORIGIN=https://USERNAME.github.io
   SEO_INDEXING_ENABLED=false
   ENABLE_CROSS_ORIGIN=true
   ENABLE_BROWSER=false
   DISABLE_BROWSER=true
   RESOLVER_CONCURRENCY=1
   MAX_ACTIVE_DOWNLOADS=2
   MAX_MEDIA_BYTES=104857600
   ```

   **Important:** `PUBLIC_ORIGIN` is the **GitHub Pages website**, not the Render address. Use HTTPS and a lowercase username/hostname, with no path or trailing slash. `SEO_INDEXING_ENABLED=false` is correct on the backend; the exported public website separately enables indexing.

5. Create/deploy the service. Docker installs FFmpeg and the required Python libraries automatically. You do not need Docker or FFmpeg installed on your own computer.
6. Once Render reports the deployment is live, copy its actual service address, such as `https://YOUR-SERVICE.onrender.com`.
7. Open **that address plus `/api/health`**. Wait for a wake-up if necessary. You should receive JSON containing:
   ```json
   {"status":"ok"}
   ```
   Additional fields are normal. Opening the backend root `/` redirects toward the public website; use `/api/health` for this check.

You do not need `METRICS_TOKEN` to let visitors download. Without it, administrative API actions are disabled. If you later enable administration, generate a strong random secret, save it only in Render environment settings, and keep it out of GitHub, screenshots and frontend configuration. The optional `render.yaml` Blueprint generates one automatically, but the manual steps above do not require using a Blueprint.

## 4. Publish the website on GitHub Pages

1. Open your GitHub repository.
2. Go to **Settings → Secrets and variables → Actions → Variables**.
3. Create a **repository variable**:
   - Name: **`BACKEND_URL`**
   - Value: the actual **`https://YOUR-SERVICE.onrender.com`** address from Render, with no extra path.
4. Go to **Settings → Pages**. Under **Build and deployment**, choose **GitHub Actions** as the source. Use HTTPS; keep **Enforce HTTPS** enabled if that option is shown. Do not set a custom domain for this free preset.
5. Go to **Actions → Publish free public website → Run workflow**, choose **main**, then run it. If Actions asks for permission to enable workflows, review and enable them.
6. Wait until the **build and deploy jobs both succeed**. Open the URL shown by the deployment:
   ```text
   https://USERNAME.github.io/
   ```

The workflow generates real public HTML, privacy/terms pages, canonical URLs, the sitemap, robots file, a configured API client and the offline shell. **Do not publish raw `static/index.html` directly**: it is a template, not the finished website.

You now have a public website **if those external deployments succeed**. This workspace alone has not published one on your account.

## 5. Check the website before sharing it

Open each URL, replacing the username:

- `https://USERNAME.github.io/` — the Pocket interface.
- `https://USERNAME.github.io/privacy/` — real policy text, not a blank page.
- `https://USERNAME.github.io/terms/` — real terms text.
- `https://USERNAME.github.io/robots.txt` — allows crawling and lists your sitemap.
- `https://USERNAME.github.io/sitemap.xml` — lists your actual website URLs.

Then:

1. Click **Try a sample** and save the sample file. This tests the interface, **not Instagram**.
2. Submit a public Instagram post **you own or are authorized to test**. The first request may display the free-server wake-up message.
3. Save a file and check its actual contents. An `ok` health response is not proof Instagram downloads work.
4. Test on your real phone and desktop. Check theme switching, policy navigation and download saving.

The free preset uses one resolver at a time, two concurrent media requests and a **100 MiB file ceiling**. These are resource safeguards, not a paid tier or daily quota. Its cross-origin download path temporarily buffers the file in the browser before saving, to avoid the Safari attachment-navigation issue; large files can strain phones. Same-origin deployments retain the native streaming download path.

## 6. Tell Google about the public website

1. Open **https://search.google.com/search-console/** and sign in.
2. Choose **Add property → URL prefix**. Enter:
   ```text
   https://USERNAME.github.io/
   ```
   Choose **URL prefix**, not Domain: you do not control the DNS for `github.io`. URL-prefix properties support HTML-tag verification. [1](https://support.google.com/webmasters/answer/34592?hl=en)
3. Choose **HTML tag** under the available verification methods. Google shows a tag resembling:
   ```html
   <meta name="google-site-verification" content="YOUR_TOKEN">
   ```
4. Copy **only the actual content value** Google gave you, without quotes or the surrounding tag. In GitHub, add another **repository variable** beside `BACKEND_URL`:
   - Name: **`GOOGLE_SITE_VERIFICATION`**
   - Value: your actual token.
5. Run **Publish free public website** again and wait for success. Then return to Google and click **Verify**. Keep the variable afterward: Google can recheck it. This token is a public verification value, not your Google password. [5](https://support.google.com/webmasters/answer/9008080?hl=en)
6. In Search Console, open **Sitemaps**, submit **`sitemap.xml`**, and check the result.
7. Use **URL inspection** on the homepage, run **Test live URL**, and use **Request indexing** if available.
8. Monitor the **Page indexing** and **Performance** reports later. Fix any reported problems; do not repeatedly submit the same URL or buy “instant indexing” promises.

**Public website ≠ Google-indexed website.** A sitemap is a discovery signal, not an indexing guarantee. Even a valid live inspection does not guarantee indexing, timing, ranking or traffic. [1](https://support.google.com/webmasters/answer/7451001?hl=en) [1](https://support.google.com/webmasters/answer/9012289?hl=en)

## 7. Keep the cost at ₹0 — and understand the limits

- Keep the source repository **Public**, Pages on the free offering, and the backend on **Free**. GitHub Pages has usage limits and host-policy restrictions. [1](https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits)
- The included workflow uses a standard Ubuntu runner. GitHub documents free standard-runner usage for public repositories/Pages; do not switch to paid larger runners or add paid storage/services. [1](https://docs.github.com/en/billing/concepts/product-billing/github-actions)
- **Do not add a Render payment method** for this zero-bill approach. Render documents that excess bandwidth can be billed when a payment method exists; without one, free services are suspended instead. Build usage can also stop new builds. Check your account billing/settings yourself. [1](https://render.com/docs/free)
- The 750 monthly free instance hours are **shared across the workspace**, not a separate allowance per service. Service-initiated traffic can also cause suspension; media fetching is relevant to that restriction. Do not create multiple backends expecting unlimited free capacity. [1](https://render.com/docs/free)
- No paid domain, paid proxy, paid scraping API, paid uptime bot, paid GitHub plan or paid SEO plugin is needed for these instructions.
- Do not use keep-awake bots or account rotation to evade host limits. The app's wake-up check runs only when a person requests a download.
- Watch actual usage in Render and GitHub. Free offerings can change. There is no promise that they remain available forever or meet your traffic needs.
- Review the existing weekly maintenance workflow. It is optional; you can disable **Weekly engine maintenance** under Actions if you do not want scheduled jobs. Do not add automated live probes merely to defeat sleeping.

## Quick fixes when something goes wrong

| What you see | What to check |
|---|---|
| Website 404 | Repository name is exactly `USERNAME.github.io`; root files are not inside an extra folder; Pages uses GitHub Actions; both workflow jobs succeeded. |
| “Backend URL” error in Actions | Add `BACKEND_URL` under **repository Variables**, using the actual HTTPS Render origin, then rerun. |
| Backend build fails | Runtime is Docker; file path is `./Dockerfile.free`; inspect the first actual error in Render build logs. A successful local Python test is not a Docker build. |
| Website loads, resolve does not | `/api/health` must work; Render `PUBLIC_ORIGIN` must exactly match the HTTPS Pages origin; `ENABLE_CROSS_ORIGIN=true`; wait for wake-up and inspect browser Network errors. |
| 429 / busy | Wait. Short-term safeguards or shared host/proxy traffic can limit the small backend. Do not bypass restrictions. |
| Some Instagram links fail | Public access can still be blocked, gated, deleted or incomplete. Do not supply login cookies or bypass private access. |
| Render suspended | Check free hours, bandwidth and service-initiated traffic notices. Wait for applicable resets; some suspensions are not fixed by a monthly reset. Do not upgrade if you must spend nothing. |
| Google cannot verify | Put only the actual token in GitHub's `GOOGLE_SITE_VERIFICATION` repository variable; redeploy; inspect the homepage source for the tag. |
| Google has not indexed it | Check Search Console's specific reason. Do not assume every non-indexed page is a code bug; indexing is Google's choice. |

## Updating the website later

Edit/commit source files on `main`. GitHub Actions rebuilds the public website. If Render auto-deploy is enabled, source changes rebuild the backend too. Review both deployment results. When you change repository variables such as the backend URL or verification token, **manually rerun the Pages workflow**; changing a variable alone does not deploy new files.

**Last checklist:** real permissions/contact/legal review → public GitHub repository → live Render health → configured GitHub Pages → authorized real download test → Search Console verification → sitemap submission → monitor actual results.
