# Known career-site setups

A running list (seeded from scans of an Israeli tech network, so it's Israel-heavy) of how specific companies publish their jobs. Check it before probing a company, and
**add a line whenever you learn something new** (a slug that worked, a Comeet URL, a site that blocks
scripted access). The next run then needs fewer web lookups.

| Company | How to get jobs | Notes (date learned) |
|---|---|---|
| Cato Networks | greenhouse slug `catonetworks` | auto-slug works (2026-11) |
| monday.com | ashby slug `monday.com` | slug includes ".com" (2026-11) |
| JFrog | greenhouse slug `jfrog` | (2026-11) |
| Capitolis | greenhouse slug `capitolis` | board existed but had 0 jobs (2026-11) |
| Island | greenhouse slug `island` | Dallas HQ, Tel Aviv R&D. Slug verified as the right company (2026-11) |
| Mend.io | ashby slug `mend-io` | (2026-11) |
| Wix | smartrecruiters slug `Wix2` | careers.wix.com is a JavaScript app; plain `wix` slug is empty (2026-11) |
| Varonis | jobvite slug `varonis` | list only, no descriptions; aggregators show many stale Varonis roles (2026-11) |
| Silverfort | comeet `https://www.comeet.com/jobs/silverfort/54.007` | (2026-11) |
| Navina | comeet `https://www.comeet.com/jobs/navina/E6.00C` | (2026-11) |
| NVIDIA | workday `https://nvidia.wd5.myworkdayjobs.com/NVIDIAExternalCareerSite` | many Israel jobs; rate-limited if hit hard (2026-11) |
| Palo Alto Networks | workday `https://paloaltonetworks.wd5.myworkdayjobs.com/panwexternalcareers` | (2026-11) |
| CrowdStrike | workday `https://crowdstrike.wd5.myworkdayjobs.com/crowdstrikecareers` | (2026-11) |
| SciPlay | workday `https://lnw.wd5.myworkdayjobs.com/SciPlayExternalCareersSite` | parent company Light & Wonder (2026-11) |
| AT&T Israel R&D Center | workday `https://att.wd1.myworkdayjobs.com/ATTGeneral` | had 0 Israel jobs in the feed (2026-11) |
| Akamai Technologies | workday `https://akamai.wd1.myworkdayjobs.com/akamai_careers` (guess) | careers site 403s scripts; many "Israel remote" roles (2026-11) |
| CME Group | workday `https://cmegroup.wd1.myworkdayjobs.com/cme_careers` (guess) | (2026-11) |
| Sunbit | WebFetch `https://sunbit.com/careers-il/` | Comeet-backed but no public company URL; page lists titles fine (2026-11) |
| Personetics | WebFetch `https://personetics.com/careers-4/` | Comeet-backed; page lists all titles + links (2026-11) |
| Skai | WebFetch `https://skai.io/company/careers/` | (2026-11) |
| env zero | WebFetch `https://www.envzero.com/careers` | renamed from env0 (2026-11) |
| Komodor | none found | careers site 403s both scripts and WebFetch; job URLs look Comeet-style (komodor.com/job/66.A65) (2026-11) |

## General patterns

- **Greenhouse / Lever / Ashby / Workable / Recruitee / SmartRecruiters / Jobvite**: `probe_ats.py`
  guesses slugs from the company name. If it misses, the slug differs: open the careers page (or search
  `"<company>" greenhouse.io OR lever.co OR ashbyhq.com OR workable.com`) and pass the right slug in `slugs`.
- **SmartRecruiters identifier trick**: if you have any posting ID (the long number in a job URL, e.g.
  `REF6W-744000160612109` → `744000160612109`), request
  `https://api.smartrecruiters.com/v1/companies/x/postings/<id>`. The error message names the real company
  identifier (that's how Wix → `Wix2` was found).
- **Comeet** (very common in Israel): company URLs look like `https://www.comeet.com/jobs/<name>/<XX.XXX>`.
  Find one with WebSearch `site:comeet.com "<company>"` or in the careers page HTML (`company-uid`), then pass
  it as `"comeet"`. Job URLs on a company's own site with `XX.XXX` codes (`?job=98.74E`, `/co/.../72.554/...`)
  mean Comeet-backed. If you can't find the company URL, WebFetch the company's careers page, which usually
  lists everything.
- **Workday** (`*.myworkdayjobs.com`): pass the site URL as `"workday"`. The probe uses the tenant's
  location facet for the target country. Workday rate-limits per IP across all tenants. The script serializes Workday calls and
  backs off, and if a result has `"partial": true`, rerun that company later with `--force`. Never try to
  get around a block.
- **Big tech with their own portals** (Google, Microsoft, Apple, Amazon, Meta, Intel): WebFetch their
  search page with a location filter and a role query, or WebSearch `site:<careers domain> <country> <role>`.
  - Google: `https://www.google.com/about/careers/applications/jobs/results/?location=<Country>&q=<role>`
  - Amazon: `https://www.amazon.jobs/en/search?base_query=<role>&loc_query=<Country>`
- **Aggregators** (builtin, jobify360, hw.glich.co, VC job boards) are often stale. Use them only to
  discover which ATS a company uses or as a last resort, and mark such jobs "unverified" in notes.
- **Sites that 403 or need JavaScript**: don't fight them. Record the company as `blocked`/`not found` with a note.

## More boards found in earlier runs (Israel-heavy; verify before relying on them)

| Company | How |
|---|---|
| AI21 Labs | webfetch: https://www.ai21.com/careers/ (Comeet-backed IDs) |
| Aidoc | greenhouse: greenhouse slug 'aidocmedical' (EU board job-boards.eu.greenhouse.io/aidocmedical) |
| Akamai Technologies | websearch: Workday akamai.wd1.myworkdayjobs.com/akamaicareers (rate-limited); found via WebSearch aggregators (builtin, j |
| Akeyless Security | comeet: https://www.comeet.com/jobs/akeyless/27.006 (akeyless.io/careers 403s to curl but WebFetch works) |
| Align Technology | websearch: jobs.aligntech.com (JS-only search at /search-job); found via WebSearch aggregators |
| Amazon | webfetch: https://www.amazon.jobs/en/search.json?country=ISR&result_limit=100&category%5B%5D=software-development |
| Amdocs | webfetch: Eightfold API: https://jobs.amdocs.com/api/pcsx/search?domain=amdocs.com&query=&location=Israel&start=0&num=10 |
| AngelSense | not found: angelsense.com (/careers 404, no careers link); no Comeet board found |
| Apono | webfetch: https://www.apono.io/wp-admin/admin-ajax.php?action=fetch_jobs (JSON behind apono.io/careers; job pages apono. |
| Apple | webfetch: https://jobs.apple.com/en-il/search?location=israel-ISR&search=<query> |
| Appnext | greenhouse: greenhouse slug: appnext (boards-api.greenhouse.io/v1/boards/appnext/jobs) |
| Artlist | blocked: artlist.io/careers returns 403; jobs seem posted via Comeet (board not found) |
| Atera | websearch: https://www.atera.com/careers/ (embedded Comeet-style /careers/co/tel-aviv/<uid>/<slug>/ pages; site returns 4 |
| Autofleet | workable: workable:autofleet (https://apply.workable.com/api/v1/widget/accounts/autofleet via WebFetch; machine rate-lim |
| BMC Software | webfetch: https://jobs.bmc.com/Careers/SearchJobs/?jobRecordsPerPage=50&jobOffset=0 (own portal, 76 jobs worldwide; filt |
| Bank Hapoalim בנק הפועלים | webfetch: https://www.bankhapoalim.co.il/forms/he/jobs-site/lobby (job pages at /forms/he/node/<id>; tech roles found vi |
| Blockaid | comeet: https://www.comeet.com/jobs/blockaid/69.00B |
| BlueGrid.ai | not found: https://bluegrid.ai/ (no careers page) |
| Booking.com | webfetch: Jibe API https://jobs.booking.com/api/jobs?location=Israel&limit=100 (job pages https://jobs.booking.com/booki |
| Bridgewise | comeet: https://www.comeet.com/jobs/bridgewise/F9.009 |
| Bright Data | webfetch: https://brightdata.com/careers (Comeet-fed list rendered server-side; job pages at brightdata.com/careers/<slu |
| Broadcom Inc. | blocked: workday https://broadcom.wd1.myworkdayjobs.com/External_Career (rate-limited at offset 0) |
| Buildots | webfetch: https://buildots.com/careers/ (Comeet-backed, position pages buildots.com/careers/<uid>/) |
| CHEQ | webfetch: https://cheq.ai/careers/ (curl gets 403; WebFetch works; job pages cheq.ai/careers/<comeet-id>) |
| CTERA | webfetch: https://ctera.com/company/careers/ (Comeet-backed, positions at ctera.com/position/<XX.XXX>) |
| Capgemini | webfetch: https://careers.capgemini.com/search/?q=&locationsearch=Israel |
| Check Point Software | blocked: https://careers.checkpoint.com/ (403 to WebFetch); listings found only on aggregators (career.io, jobify360, e |
| Checkmarx | webfetch: https://checkmarx.com/job-openings/ (Comeet-backed, positions at /job-openings/position/<XX.XXX>/; curl gets 4 |
| Citi | webfetch: https://jobs.citi.com/location/israel-jobs/287/294640/2 |
| Claroty | comeet: Comeet API: https://www.comeet.co/careers-api/2.0/company/F2.004/positions?token=2F4EC42F42F45E814AC1A945E814A |
| CloudShare | webfetch: https://www.cloudshare.com/careers/ (links to Workable board cloudshare.workable.com / apply.workable.com/clou |
| CodiQ | not found: codiq.io (factory-automation no-code platform) has no careers page or job board link |
| Cognata | webfetch: https://www.cognata.com/hiring/ |
| Cognyte | comeet: https://www.comeet.com/jobs/cognyte/F2.009 |
| CommBox | webfetch: https://www.commbox.io/careers/ (Comeet-style codes; site blocks curl via Cloudflare, WebFetch works) |
| Converge Bio | not found: https://www.converge-bio.com/careers (JS-loaded, no ATS link); TLV Partners board shows no jobs |
| Coralogix | comeet: https://www.comeet.com/jobs/coralogix/06.004 |
| Covercy | websearch: covercy.com/careers has no listings/board; jobs found via jobify360 (LinkedIn mirror) |
| Cybellum | webfetch: https://cybellum.com/careers/ (Comeet-backed WP section) |
| Cynet Security | webfetch: https://www.cynet.com/careers/ (roles listed inline, no ATS links) |
| Cynomi | webfetch: https://cynomi.com/careers/ (Comeet-backed pages under /careers/co/israel-office/CB.E42/...; curl gets 403, We |
| Dcoya | not found: https://dcoya.com/ (no careers page; company acquired by NINJIO, ninjio.com) |
| Dell Technologies | webfetch: Oracle HCM API https://enterpriseplatform.dell.com/hcmRestApi/resources/latest/recruitingCEJobRequisitions?onl |
| Discount Bank בנק דיסקונט | not found: https://www.discountbank.co.il/jobs/#he-IL/sites/CX_3001 (Oracle Recruiting Cloud, JS-only; API host not found |
| DoubleVerify | greenhouse: greenhouse:doubleverify (job-boards.greenhouse.io/doubleverify) |
| DraftKings Inc. | workday: https://draftkings.wd1.myworkdayjobs.com/DraftKings |
| Dream | webfetch: https://dreamgroup.com/careers/ (Comeet-backed, links /comeet-positions/<slug>) |
| Dynamic Yield | workday: https://mastercard.wd1.myworkdayjobs.com/CorporateCareers (dynamicyield.com/careers redirects to careers.maste |
| Earnix | webfetch: https://earnix.com/career/ (Comeet-backed, job IDs like f5.571) |
| Elbit Systems | webfetch: https://elbitsystemscareer.com/cron/jobs.json (full JSON feed behind elbitsystemscareer.com; jobs UI at https: |
| Equitybee | not found: https://equitybee.com/careers/ (JS-only SPA, no ATS found); VC board careers.greenfield-growth.com/companies/e |
| EverC | websearch: Former Lever board 'everc' is gone (API 'Document not found'); EverC now part of G2 Risk Solutions. Jobs seen |
| Fetcherr | webfetch: https://www.fetcherr.io/career (Comeet-backed list in static HTML; positions at /careers/position-<xx_xxx>) |
| Finastra | websearch: workday: https://finastra.wd3.myworkdayjobs.com/FINC (Israel site = Kfar Saba, Payments BU); machine rate-limi |
| Firebolt | comeet: https://www.firebolt.io/careers-new -> comeet.com/jobs/firebolt/26.004 |
| Flashpoint | ashby: ashby slug flashpoint.io (https://jobs.ashbyhq.com/flashpoint.io), linked from flashpoint.io/about-us/careers |
| Flexera | websearch: Workday: https://flexerasoftware.wd1.myworkdayjobs.com/FlexeraSoftware (JS-only; direct API call not permitted |
| Flock Safety | ashby: https://api.ashbyhq.com/posting-api/job-board/Flock%20Safety (slug has a space; 'flock' is a different UK comp |
| Foretellix | webfetch: https://www.foretellix.com/career/#open-positions (Comeet-backed, links under foretellix.com/join-us/co/israel |
| Fullpath | webfetch: https://www.fullpath.com/careers/ (Comeet-style /careers/co/<loc>/<id>/ links) |
| Glassbox | greenhouse: glassboxltd (boards-api.greenhouse.io/v1/boards/glassboxltd/jobs) |
| Global-e | webfetch: https://www.global-e.com/careers/ |
| Gong | greenhouse: greenhouse:gongio (probe_ats slug gongio) |
| Google | websearch: https://www.google.com/about/careers/applications/jobs/results/?location=Israel&q=backend%20java (JS-only, not |
| GuardKnox Cyber Technologies | not found: guardknox.com/careers returned 403; no Comeet/ATS board found via search |
| Guardio | comeet: https://www.comeet.com/jobs/guardio/57.000 |
| HARMAN Automotive Israel | webfetch: Avature board https://jobsearch.harman.com/en_US/careers/SearchJobs/?listFilterMode=1&jobRecordsPerPage=20&job |
| Hailo | websearch: https://hailo.ai/company-overview/careers/ (Comeet-backed, positions at /company-overview/careers/<slug>/<XX.X |
| Healthee | websearch: https://healthee.com/who-we-are/healthee-career/ (JS widget, empty); builtin.com/company/healthee/jobs |
| Hexagon Asset Lifecycle Intelligence | websearch: careers.hexagon.com (SuccessFactors, list is JS-only; search ?locationsearch=Israel). Israel site is Nesher. |
| HiBob | webfetch: https://www.hibob.com/careers/ (static HTML lists all jobs; links to own ATS hibob-fa0ad69d0cb34a.careers.hibo |
| Hyro | webfetch: https://www.hyro.ai/careers/ (fetch with curl + browser UA; WebFetch gets 403). Positions are Comeet UIDs at / |
| IBM | webfetch: POST https://www-api.ibm.com/search/api/v2 (appId careers, scopes careers2, post_filter field_keyword_05=Israe |
| IG Group | not found: workday https://ig.wd103.myworkdayjobs.com/EXT_IG (from iggroup.com/careers) |
| IONIX | webfetch: https://www.ionix.io/careers/ (Comeet-powered, comeet.com/jobs/ionix/EE.742 timed out) |
| Imperva | workday: workday:https://thales.wd3.myworkdayjobs.com/Careers (Imperva is a Thales company; filter Israel) |
| Infinidat | comeet: https://www.comeet.com/jobs/infinidat/D6.003 |
| Innovid | not found: greenhouse 'innovid' board now 404 (merged into Mediaocean); mediaocean.com/careers TLS error |
| Innoviz Technologies | blocked: innoviz.tech/careers (Incapsula bot wall); positions at innoviz.tech/careers-3/co/<dept>/<uid>/... (Comeet ifr |
| Intango | comeet: Comeet uid 68.000 (comeet.com/jobs/intango/68.000), token in intango.com/career page |
| Intuit | webfetch: https://jobs.intuit.com/search-jobs/Israel |
| J.P. Morgan | webfetch: Oracle HCM API: https://jpmc.fa.oraclecloud.com/hcmRestApi/resources/latest/recruitingCEJobRequisitions?onlyDa |
| KLA | websearch: workday: https://kla.wd1.myworkdayjobs.com/Search (Israel sites Migdal HaEmek / Yavne); machine rate-limited o |
| Komodor | blocked: |
| LSEG (London Stock Exchange Group) | websearch: Workday: https://lseg.wd3.myworkdayjobs.com/Careers (JS-only, Workday rate-limited from this machine; not inde |
| Layline Tech | webfetch: https://www.laylinetech.com/jobs |
| Loris.ai | lever: Loris was acquired by Contentsquare (loris.ai/careers 301 -> contentsquare.com). Board: lever slug contentsqua |
| Lumen | comeet: https://www.comeet.com/jobs/lumen/1A.00E (also https://www.lumen.me/careers.json) |
| MDClone | comeet: https://www.comeet.com/jobs/mdclone/66.004 |
| MSD Animal Health Intelligence Technology Labs | websearch: MSD/Merck Workday (https://msd.wd5.myworkdayjobs.com/SearchJobs, location Netanya, Israel); machine rate-limit |
| Maccabi Health care Services | websearch: https://www.maccabi4u.co.il/careers/all-positions/ (list is JS-only; find posts with site:maccabi4u.co.il care |
| Maytronics | comeet: https://www.comeet.com/jobs/maytronics/E3.008 |
| Medulla | not found: |
| Melio | not found: greenhouse:melio (boards-api returns 0 jobs; lifeatmelio.com roles are JS/images; careers.xero.com post-acquis |
| Memcyco | webfetch: https://www.memcyco.com/careers-at-memcyco/ |
| Microsoft | webfetch: Eightfold API: https://apply.careers.microsoft.com/api/pcsx/search?domain=microsoft.com&query=&location=Israel |
| Migdal Group | webfetch: Drushim employer page https://www.drushim.co.il/דרושים-171896-מגדל-חברה-לביטוח/ (no own careers site found) |
| Millennium | websearch: eFinancialCareers listings for Millennium Management Tel Aviv (Ramat Gan Bursa office); Millennium's own porta |
| Mitiga | webfetch: https://www.mitiga.io/careers |
| NGsoft | webfetch: https://www.ngsoft.com/who-we-are/careers (all jobs in page HTML modals; apply via on-page form) |
| NVIDIA | websearch: WebSearch -> jobs.anitab.org/companies/nvidia (Getro mirror with Workday JR links); Workday nvidia.wd5.myworkd |
| Navan | greenhouse: greenhouse slug: tripactions (boards-api.greenhouse.io/v1/boards/tripactions/jobs) |
| NetApp | webfetch: https://careers.netapp.com/search-jobs/Israel (Radancy front-end over Workday; also /search-jobs/Tel%20Aviv) |
| NetNut.io | webfetch: Rippling board https://ats.rippling.com/netnut/jobs (company listed as 'NetNut Alarum'); netnut.io itself unre |
| NetOp.Cloud | webfetch: https://netop.ai/careers/ (netop.cloud redirects to netop.ai; static WordPress page, apply via 'Send CV') |
| Netskope | greenhouse: greenhouse:netskope (boards-api.greenhouse.io/v1/boards/netskope/jobs) |
| Neural Guard | not found: https://www.neuralguard.com/ (no careers page; LinkedIn only) |
| NextSilicon | comeet: https://www.comeet.com/jobs/nextsilicon/18.007 |
| Next Insurance | greenhouse: greenhouse slug nextinsurance66 (job-boards.greenhouse.io/nextinsurance66); now branded ERGO NEXT |
| Nexthink | smartrecruiters: smartrecruiters:Nexthink (api.smartrecruiters.com/v1/companies/Nexthink/postings) |
| Nimble Finance | not found: no careers page found (nimble-finance.com returns 526); recruitee 'nimble' is a different company |
| Noma Security | webfetch: https://noma.security/careers/ (positions at /positions/position-<id>, Webflow-hosted) |
| Nova Ltd. | webfetch: https://www.novami.com/location_filter/israel/ (Comeet-backed, items at novami.com/comeetitem/<uid>/) |
| ONE ZERO BANK | comeet: https://www.comeet.com/jobs/onezerobank/36.00A |
| ORION Security | greenhouse: greenhouse (EU) slug orioncscybersecurityltd (https://job-boards.eu.greenhouse.io/orioncscybersecurityltd); ca |
| OX Security | comeet: https://www.comeet.com/jobs/ox_security/F8.006 |
| OneLayer | webfetch: https://onelayer.com/career/ (Comeet-backed, positions at /careers/<xx-xxx>/) |
| Onebeat | comeet: https://www.comeet.com/jobs/onebeat/0A.000 |
| OpenPolicy | not found: openpolicygroup.com (no careers page; /careers 404); no Greenhouse/Lever/Ashby/Comeet board under openpolicy/o |
| Orca Security | webfetch: https://orca.security/about/careers/ (Greenhouse job IDs via gh_jid; board token is not 'orca') |
| OriginAI | webfetch: https://www.originai.co/careers/ (no ATS, apply via recruitment@originai.co) |
| Ovalix | webfetch: https://www.ovalix.ai/careers (Webflow page, jobs at /careers/<slug>) |
| PAPAYA | webfetch: https://www.papayaglobal.com/careers/ (server-rendered list; WebFetch 403, plain GET works) |
| Paragon | websearch: No public board found. paragon-solutions.com/careers returns an empty page. Listings appear only on jobify360 |
| PayZen | ashby: ashby:payzen-inc (old Lever board 'payzen' is 404) |
| Penlink | comeet: https://www.comeet.com/jobs/penlink/E5.002 |
| Pentera | webfetch: https://pentera.io/careers/ (Comeet-style codes, /careers/co/israel/<id>/<slug>/all; curl blocked by Cloudflar |
| Personetics | webfetch: https://personetics.com/careers-4/ |
| Pipl | comeet: https://www.comeet.com/jobs/pipl/22.008 (linked from pipl.com/careers) |
| Powtoon | blocked: apply.workable.com/powtoon (workable slug powtoon) |
| Priority Software | webfetch: https://www.priority-software.com/wp-json/wp/v2/careers?per_page=100 (WordPress careers CPT; page https://www. |
| Prismm (formerly AllSeated) | webfetch: https://www.prismm.com/jobs |
| Proofpoint | websearch: workday: https://proofpoint.wd5.myworkdayjobs.com/en-US/ProofpointCareers (location Tel Aviv); machine rate-li |
| Radware | blocked: radware.com/careers is behind a Radware bot-verification interstitial (curl + WebFetch blocked). Jobs found vi |
| Rafael Advanced Defense Systems | blocked: https://career.rafael.co.il/ (bot-challenge JS page, HTTP 247; not indexed by search). Found role via jobify36 |
| Rakuten Viber | webfetch: https://www.viber.com/en/careers-israel |
| Rapyd | webfetch: https://www.rapyd.net/company/careers-search/?location=tel-aviv-israel |
| Razor Labs | webfetch: https://www.razor-labs.com/careers (Comeet-style /careers/co/... links) |
| RedPanda | ashby: redpanda-data (api.ashbyhq.com/posting-api/job-board/redpanda-data) |
| Red Hat | websearch: workday: https://redhat.wd5.myworkdayjobs.com/Jobs (filter location Raanana); machine rate-limited on Workday, |
| Reindeer | ashby: ashby slug 'reindeer-ai' (reindeer.ai/careers redirects there) |
| Remedio (formerly GYTPOL) | webfetch: https://remedio.io/careers (Comeet-backed, positions at remedio.io/careers/<slug>/<uid>/) |
| Remitly Israel (formerly Rewire) | websearch: careers.remitly.com/job-search-results/?compliment=Israel&primary_city=Tel%20Aviv (JS-only; backed by Workday |
| Revolut | blocked: https://www.revolut.com/careers/ (403 for WebFetch); positions at revolut.com/careers/position/<slug-uuid>/ |
| Riverside.fm | comeet: https://www.comeet.com/jobs/riverside-fm/66.009 (token on riverside.fm/careers) |
| SAP | blocked: https://jobs.sap.com/search/?q=&locationsearch=Israel (also /go/SAP-Jobs-in-Ra'anana/852101/ and /go/Java-Jobs |
| SURF SECURITY | not found: https://www.surf.security/about?tab_id=Careers (no listings; asks to email Jobs@surf.security). Note: Greenhou |
| SafeBase | ashby: SafeBase acquired by Drata; safebase.io/careers redirects to drata.com; Ashby board 'drata' |
| Salesforce | not found: Workday: https://salesforce.wd12.myworkdayjobs.com/External_Career_Site (Israel facet locationCountry=08456288 |
| ScyllaDB | comeet: https://www.comeet.com/jobs/scylladb/E4.006 |
| Skai | webfetch: https://skai.io/company/careers/ |
| Smarsh | lever: lever:smarsh (api.lever.co/v0/postings/smarsh) |
| Sola Security | webfetch: https://sola.security/careers (Comeet-style position ids) |
| SolarEdge Technologies | comeet: https://www.comeet.com/jobs/SolarEdge/71.00A (corporate.solaredge.com/en/careers/open-positions) |
| Spectro Cloud | rippling: spectrocloud (api.rippling.com/platform/api/ats/v1/board/spectrocloud/jobs) |
| Stampli | webfetch: https://www.stampli.com/careers/ (Comeet-backed) |
| Start.io (formerly StartApp) | webfetch: https://www.start.io/career/ |
| Sunbit | webfetch: https://sunbit.com/careers-il/ |
| Tastewise | blocked: |
| Teads | greenhouse: greenhouse:teads1 (https://boards-api.greenhouse.io/v1/boards/teads1/jobs); old outbraininc board is empty |
| Team8 | comeet: https://www.comeet.com/jobs/team8/61.003 (team8.vc/career, lists jobs at portfolio companies) |
| Tenable | greenhouse: greenhouse slug tenableinc (boards-api.greenhouse.io/v1/boards/tenableinc/jobs) |
| Tikal | webfetch: https://www.tikalk.com/career/#jobs |
| Tipalti | blocked: tipalti.com/company/jobs/ (linked from tipalti.com/careers/): curl 403 and the page is JS-rendered, ATS not id |
| Trolley | greenhouse: greenhouse slug trolley (trolley.com/careers, Canadian payouts company; the connection is its VP Engineering) |
| Trustmi | blocked: https://apply.workable.com/trustmi/ (Workable 429, Retry-After ~23h) |
| Tufin | websearch: tufin.com/careers returns 403; Built In company page https://builtin.com/company/tufin/jobs |
| Upwind Security | webfetch: https://www.upwind.io/careers (Comeet-backed, links under upwind.io/careers/co/...) |
| Vayyar Imaging | blocked: vayyar.com/careers redirects to https://apply.workable.com/vayyar/ (workable slug 'vayyar') |
| Venn | greenhouse: venncity (Venn real-estate AI platform, Tel Aviv R&D). The other Venn (BYOD security, rippling venncareers) ha |
| Vesttoo | not found: vesttoo.com does not resolve (DNS ENOTFOUND) |
| Viewz | not found: no official careers page found (viewz.com unreachable/404); listings only on jobify360.co.il |
| WSC Sports | comeet: https://www.comeet.com/jobs/wsc-sports/93.007 (token on wsc-sports.com/careers) |
| WaveBL | websearch: No careers page/ATS found (wavebl.com/careers 404, no Comeet board); jobs seen on jobify360 (LinkedIn mirror) |
| Webz.io | webfetch: https://webz.io/careers/#open-positions (WordPress; jobs at webz.io/job/<slug>/) |
| ZIM Integrated Shipping Services | blocked: zim.com/careers returns 403 to WebFetch; ATS not identified (no greenhouse/lever/smartrecruiters board under ' |
| Zebra Technologies | websearch: Workday: https://zebra.wd501.myworkdayjobs.com/Zebra_careers (not probed - rate limited) |
| Zeekit (a Walmart Company) | not found: Workday walmart.wd5.myworkdayjobs.com/WalmartExternal returned HTTP 500/422; careers.walmart.com Israel filter |
| Zencity | comeet: Comeet API: https://www.comeet.co/careers-api/2.0/company/56.00B/positions?token=65B262265B1FC7131126220CB6262 |
| Zota | recruitee: zota.recruitee.com (careers.zota.com) |
| diwip | not found: www.diwip.com refuses connections and diwip.com doesn't resolve. diwip was acquired and now runs as Tangelo Ga |
| eToro | greenhouse: greenhouse slug etoroltd (job-boards.eu.greenhouse.io/etoroltd); careers page www.etoro.com/about/careers/ |
| env zero | webfetch: https://www.envzero.com/careers |
| qSpark | webfetch: https://qspark.co/careers (qspark.com is a parked domain) |
