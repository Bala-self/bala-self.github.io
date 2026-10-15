# Pocket — legal, honesty and future-risk review

**Review date:** October 15, 2026. **Conclusion: not cleared for a risk-free public launch.**

This is a code/claims review and issue-spotting exercise, **not a legal opinion, compliance certification or prediction of enforcement**. India is considered because of the user's approximate location; the operator's actual jurisdiction, business entity, intended audience and hosting arrangements have not been confirmed. Other applicable jurisdictions need separate review.

## 1. The main unresolved issue: platform authorization

The code uses automated Instagram access through yt-dlp, an HTML parser and an optional browser. There is no evidence in this project of express permission from Meta to perform that access. Instagram's published terms prohibit automated access/collection without express permission, including logged-out collection, and prohibit circumventing access-control measures. Public visibility and not requesting a password do not establish platform authorization. Whether particular terms are enforceable against this operator and what other laws apply require counsel. A terms dispute is not automatically a criminal offense. [1](https://help.instagram.com/581066165581870/)

Possible outcomes include upstream blocks and a requirement to stop or change the service. A legal demand or claim is possible; its likelihood, merits and outcome cannot be predicted from the repository. Permission from a creator does not necessarily satisfy Meta's access terms.

**Safest product change:** avoid public scraping and instead process user-supplied files or use a genuinely authorized interface within its actual permitted scope. There is no basis to promise an official API that downloads every public Instagram URL without authorization.

## 2. Copyright and music rights

The server copies/transmits media to users, and optional MP3 conversion creates temporary copies and extracts audio. Not maintaining a permanent library is a technical retention choice, not a copyright exemption.

Public posts, attribution, no charge and personal use do not automatically establish permission for every download. A creator may not control the music, footage, likeness or other third-party rights in a Reel. Permission to upload or play music inside Instagram does not by itself prove permission for an outside downloader to distribute audio files.

For India, Sections 51 and 52 concern infringement and exceptions; Section 52 contains specific fair-dealing exceptions, and Section 55 provides civil remedies. Section 63 concerns knowing infringement/abetment and can involve criminal consequences when its conditions are met. This does **not** mean that every use, every download, or this code by itself is a criminal offense. A lawyer must assess the particular acts, permissions, knowledge, exceptions and operator role. [2](https://www.indiacode.nic.in/handle/123456789/1367?view_type=browse)

Potential consequences, depending on facts and law: takedown requests, injunctions, damages/costs, and in qualifying cases criminal proceedings. No probability or penalty estimate is justified here.

## 3. Hosting and repository exposure

Vercel prohibits infringement of others' rights, responds to copyright notices and provides for restriction/suspension/termination under its acceptable-use policy. A successful deployment is not legal approval. [3](https://vercel.com/legal/acceptable-use-policy)

GitHub has a DMCA notice/counter-notice procedure that can result in affected content or repositories being disabled. That does not mean a downloader source repository will automatically be removed, or that a complaint is necessarily correct. [4](https://docs.github.com/en/site-policy/content-removal-policies/dmca-takedown-policy)

Hosting, bandwidth and compute bills are also operational risks. Current in-memory limits do not constitute a complete DDoS, fraud or cost-control program. No permanent public deployment or hosting-provider approval was completed in this conversation.

## 4. Privacy, misuse, branding and licenses

- The service processes links, creator metadata, media, observed client/proxy network addresses and expiring access tokens. It must not claim to process no data.
- Short retention/no login reduces some exposure but does not establish privacy-law compliance. Review lawful processing, complaints, security, vendor logs, cross-border hosting and any children's-data obligations that actually apply.
- India's DPDP framework has phased commencement; assess the particular provisions and dates instead of assuming every obligation is already operative or that the framework can be ignored. The official Rules provide immediate, one-year and eighteen-month phases. [Official Rules](https://www.meity.gov.in/static/uploads/2025/11/53450e6e5dc0bfa85ebd78686cadad39.pdf).
- Public images can still be misused for harassment, stalking, impersonation or non-consensual sharing. The current code does not verify rights ownership, consent or every request's purpose.
- The Instagram/Meta non-affiliation notice is helpful disclosure, not blanket trademark permission. The name “Pocket” and the intended domain also require actual clearance; none was performed here.
- Dependency/binary redistribution obligations, including FFmpeg and its enabled components, require a proper license review before distributing images/binaries. No complete dependency-license clearance was performed.
- Actual host security, egress restrictions, backup/log retention, secrets, breach response and production proxy behavior remain deployment responsibilities. Passing local tests is not a penetration test or legal audit.

## 5. Misleading or overbroad claims corrected in this review

Changed `static/index.html`, `static/manifest.webmanifest`, `content/policies.json` and `seo.py`:

1. Removed “does not ... redistribute posts” / “no public redistribution service” as an implied legal assurance. The site now discloses that the server fetches and transmits files, while keeping no permanent media library.
2. Replaced broad “fair use” shorthand in the footer with rights/permission/legal-entitlement language. Terms distinguish jurisdiction-specific fair dealing/fair use and do not declare a download automatically lawful.
3. Clarified **no added watermark**, not removal of source watermarks. The implementation does not remove marks embedded in the original media.
4. Replaced “Your links stay private” with a factual temporary-processing statement; the operator/upstream necessarily handle a link to resolve it.
5. Replaced the indefinite “Always free” badge with “Free to use,” describing current functionality rather than guaranteeing a future operating model.
6. Added explicit platform-authorization and third-party/music-rights cautions. Clarified transient network-address rate-limit retention.

These are accuracy improvements, **not a cure for missing permissions or statutory obligations**. Substantive behavior, user access and resolver strategies were not changed. No unrequested consent gate was added.

## 6. Required before advertising a public service as compliant

- Establish the operator, jurisdiction and intended markets with an internet/copyright/privacy lawyer.
- Establish an authorized access model; do not treat creator permission as automatic Meta authorization.
- Obtain relevant content/music permissions or a sound, specifically reviewed basis for any exception relied on.
- Add real operator/contact details and a working, reviewed rights/privacy-complaint process. Do not claim one exists while the terms still contain a launch placeholder.
- Determine any intermediary/safe-harbour/notice-handling rules that actually apply. Merely writing “users are responsible” or adding a disclaimer does not automatically establish an exemption.
- Review host/repository rules, licenses and name/domain clearance; configure spending limits and abuse response.
- Keep private/login-required access, challenge bypass, credential collection and evasion out of scope. Continuing after a legal notice needs advice, not automatic proxy rotation.
- Recheck law, platform terms and dependencies periodically and when changing markets, features, vendors or monetization.

**Bottom line:** the code has sensible safeguards, but an unrestricted public downloader cannot honestly be advertised as “100% legal,” “Meta approved,” “no data processing” or “no future consequences” on the evidence available. Do not present this review as lawyer approval.

## Validation

96 automated tests pass, including a new check for the corrected disclosures. These checks verify application behavior and wording only; they do not establish legality or immunity from claims.
