"""Find a company's open positions in the candidate's target country via public job-board (ATS) APIs.

Many company career pages are JavaScript apps or block scrapers, but most of them
are fed by a standard ATS with a public JSON feed. This script tries those feeds
directly, keeps only jobs located in the target country, pre-filters titles to the
candidate's role family, and records how many of the candidate's skill keywords appear
in each description so Claude can make the final relevance call.

Usage:
    python probe_ats.py <targets.json> <out_dir> --profile <profile.json> [--workers 8] [--force]

profile.json (written by Claude from the CV in step 0; every key except country_code is optional):
    {"country": "Israel", "country_code": "IL",
     "location_terms": ["tel aviv", "haifa"],        # extra city/region names (regex fragments OK)
     "remote_terms": ["remote - israel"],            # optional: remote labels that count as local
     "title_include": ["engineer", "developer"],     # regexes; a title must match one ([] = keep all titles)
     "title_exclude": ["sales", "intern"],           # regexes; a title matching any is dropped
     "keywords": ["java", "spring", "kafka"]}        # skill keywords counted in descriptions (words or regexes)
Countries with a built-in city list: see LOCATION_PRESETS.

targets.json is a list of objects:
    {"company": "Cato Networks",            # required
     "slugs": ["catonetworks"],             # optional extra slugs to try (auto-generated ones are tried too)
     "workday": "https://nvidia.wd5.myworkdayjobs.com/NVIDIAExternalCareerSite",  # optional
     "comeet": "https://www.comeet.com/jobs/acme/12.345"}                        # optional

Writes one <out_dir>/<safe-company-name>.json per company (skipped on rerun unless
--force, so an interrupted scan can resume) and prints a one-line summary each.

Per-company result:
    {"company", "sources": ["greenhouse:catonetworks", ...], "local_jobs_total": int, "local_titles": [...],
     "candidates": [{"title","location","url","source","stack_hits":{kw:count},"description"}],
     "errors": [...]}
"sources" empty  ==> no ATS feed found; Claude must fall back to WebFetch/WebSearch.
"""
import argparse
import html
import json
import os
import re
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse

import time

import requests

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36"}
TIMEOUT = 10
# Workday rate-limits per client IP across all its tenants, so Workday calls run one at a time.
WD_LOCK = threading.Lock()


class Jobs(list):
    """Job list that can carry a warning (e.g. pagination cut short by rate limiting)."""
    warning = None

# Built-in city lists for countries where job locations often name only the city.
# For any other country, Claude passes the main cities in profile["location_terms"].
LOCATION_PRESETS = {
    "IL": [r"israel", r"\bisr\b", r"tel[\s-]?aviv", r"herzliya|herzelia", r"ramat[\s-]?gan", r"petah?[\s-]?tikv|petach",
           r"haifa", r"jerusalem", r"ra'?anana", r"netanya", r"yokneam|yoqneam", r"be'?er[\s-]?sheva|beersheba",
           r"rehovot", r"hod[\s-]?hasharon", r"kfar[\s-]?saba", r"or[\s-]?yehuda", r"airport[\s-]?city",
           r"rosh[\s-]?ha'?ayin", r"caesarea", r"modi'?in", r"holon", r"bnei[\s-]?brak", r"givatayim", r"rishon",
           r"\blod\b", r"ashdod", r"ashkelon", r"nazareth", r"kiryat", r"matam", r"yavne",
           r"ישראל", r"תל[\s-]?אביב", r"הרצליה", r"רמת[\s-]?גן", r"פתח[\s-]?תקווה", r"חיפה", r"ירושלים", r"רעננה",
           r"נתניה", r"יקנעם", r"באר[\s-]?שבע"],
    "GB": [r"united kingdom", r"\buk\b", r"england", r"scotland", r"wales", r"london", r"manchester", r"edinburgh",
           r"cambridge", r"oxford", r"bristol", r"belfast", r"glasgow", r"leeds", r"birmingham"],
    "US": [r"united states", r"\busa?\b", r"new york", r"san francisco", r"seattle", r"austin", r"boston", r"chicago",
           r"los angeles", r"denver", r"atlanta", r",\s*(ca|ny|wa|tx|ma|il|co|ga|nj|va|nc|fl|or|pa)\b"],
    "DE": [r"germany", r"deutschland", r"berlin", r"munich|münchen", r"hamburg", r"frankfurt", r"cologne|köln", r"stuttgart"],
}

# Defaults used when the profile doesn't define its own title filters: keep anything that
# looks like a tech/professional role and drop roles clearly in another field. Claude
# normally writes role-specific include/exclude lists into profile.json.
DEFAULT_TITLE_INCLUDE = [r"engineer", r"developer", r"programmer", r"software", r"architect", r"back[\s-]?end",
                         r"full[\s-]?stack", r"platform", r"data", r"scientist", r"analyst", r"product", r"design"]
DEFAULT_TITLE_EXCLUDE = [r"\bsales", r"account (executive|manager)", r"marketing", r"recruit", r"\bhr\b", r"legal",
                         r"finance", r"intern\b", r"internship", r"student"]
DEFAULT_KEYWORDS = ["java", "python", "go", "kotlin", "node", "typescript", "c#", "c++", "kafka", "aws", "kubernetes", "sql"]

# Keywords that need care to avoid false hits in free text.
_GO = r"\bgolang\b|\bgo\b(?=[\s,/)]*(?:lang|developer|engineer|services?|microservices|,|/|\)))"
KEYWORD_SPECIAL = {
    "java": r"\bjava\b(?!script)", "go": _GO, "golang": _GO,
    "c++": r"c\+\+", "c#": r"c#|\.net\b", ".net": r"\.net\b", "node": r"\bnode(\.js|js)?\b",
    "microservices": r"micro[\s-]?services?", "kubernetes": r"kubernetes|\bk8s\b",
}

# Filled in by configure() from the profile.
COUNTRY_CODE = ""
COUNTRY_NAME = ""
LOCAL_RE = TITLE_INCLUDE = TITLE_EXCLUDE = None
STACK_KWS = {}


def _alt(parts):
    return re.compile("|".join(f"(?:{p})" for p in parts), re.I) if parts else None


def _kw_regex(k):
    if k.lower() in KEYWORD_SPECIAL:
        return KEYWORD_SPECIAL[k.lower()]
    if re.search(r"[\\\[\](){}|?*^$]", k):  # already a regex
        return k
    return r"(?<![\w])" + re.escape(k) + r"(?![\w])"


def configure(profile):
    global COUNTRY_CODE, COUNTRY_NAME, LOCAL_RE, TITLE_INCLUDE, TITLE_EXCLUDE, STACK_KWS
    COUNTRY_CODE = (profile.get("country_code") or "").upper()
    COUNTRY_NAME = profile.get("country") or COUNTRY_CODE
    if not COUNTRY_CODE:
        sys.exit("profile.json needs a 2-letter country_code (e.g. IL, GB, US)")
    terms = list(LOCATION_PRESETS.get(COUNTRY_CODE, []))
    terms.append(re.escape(COUNTRY_NAME.lower()))
    terms.append(rf"\b{COUNTRY_CODE.lower()}\b")
    terms += profile.get("location_terms") or []
    terms += [re.escape(t) for t in profile.get("remote_terms") or []]
    LOCAL_RE = _alt(terms)
    inc = profile.get("title_include")
    TITLE_INCLUDE = _alt(DEFAULT_TITLE_INCLUDE if inc is None else inc)  # [] -> keep every title
    exc = profile.get("title_exclude")
    TITLE_EXCLUDE = _alt(DEFAULT_TITLE_EXCLUDE if exc is None else exc)
    STACK_KWS = {k: _kw_regex(k) for k in (profile.get("keywords") or DEFAULT_KEYWORDS)}


def is_local(loc):
    return bool(LOCAL_RE.search(loc or ""))


def title_ok(title):
    if TITLE_INCLUDE is not None and not TITLE_INCLUDE.search(title):
        return False
    return not (TITLE_EXCLUDE is not None and TITLE_EXCLUDE.search(title))


def clean(text, limit=2500):
    if not text:
        return ""
    t = html.unescape(html.unescape(text))
    t = re.sub(r"<[^>]+>", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t[:limit]


def stack_hits(text):
    hits = {}
    for k, pat in STACK_KWS.items():
        n = len(re.findall(pat, text or "", re.I))
        if n:
            hits[k] = n
    return hits


def slug_candidates(company, extra):
    base = company.lower()
    base = re.sub(r"\s*[|(\[].*$", "", base).strip()
    stripped = re.sub(
        r"[\s,]+(ltd\.?|inc\.?|llc|corp\.?|technologies|technology|gmbh|plc|group|r&d|labs?|software|systems|networks?|security|ai|io)$",
        "", base).strip()
    if COUNTRY_NAME:
        stripped = re.sub(rf"[\s,]+{re.escape(COUNTRY_NAME.lower())}$", "", stripped).strip()
    out = list(extra or [])
    for b in {base, stripped}:
        words = re.findall(r"[a-z0-9]+", b)
        if not words:
            continue
        out += ["".join(words), "-".join(words), words[0]]
        if "." in b:  # e.g. "monday.com", "mend.io"
            out.append(re.sub(r"[^a-z0-9.]", "", b))
            out.append(b.split(".")[0])
    seen, res = set(), []
    for s in out:
        if s and s not in seen and len(s) > 1:
            seen.add(s)
            res.append(s)
    return res


def http(method, url, **kw):
    """requests wrapper that backs off on 429 (Workday in particular rate-limits fast paging)."""
    kw.setdefault("headers", UA)
    kw.setdefault("timeout", TIMEOUT)
    for attempt in range(5):
        r = requests.request(method, url, **kw)
        if r.status_code != 429:
            return r
        try:
            wait = int(r.headers.get("Retry-After", 0) or 0)
        except ValueError:
            wait = 0
        time.sleep(min(wait or 10 * (attempt + 1), 60))  # cap: some servers ask for an hour
    return r


def get_json(url, **kw):
    r = http("GET", url, **kw)
    if r.status_code != 200:
        return None
    try:
        return r.json()
    except ValueError:
        return None


# --- ATS adapters: each returns a list of raw jobs {title, location, url, description} or None if not found.

def greenhouse(slug):
    d = get_json(f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs", params={"content": "true"})
    if not d or "jobs" not in d or (not d["jobs"] and d.get("meta", {}).get("total") is None):
        return None
    jobs = []
    for j in d["jobs"]:
        locs = [(j.get("location") or {}).get("name", "")]
        locs += [o.get("name", "") + " " + (o.get("location") or "") for o in j.get("offices", [])]
        jobs.append({"title": j.get("title", ""), "location": " | ".join(filter(None, locs)),
                     "url": j.get("absolute_url", ""), "description": j.get("content", "")})
    return jobs


def lever(slug):
    for host in ("api.lever.co", "api.eu.lever.co"):
        d = get_json(f"https://{host}/v0/postings/{slug}", params={"mode": "json"})
        if isinstance(d, list):
            jobs = []
            for j in d:
                c = j.get("categories") or {}
                locs = [c.get("location", "")] + (c.get("allLocations") or []) + [j.get("country", "") or ""]
                desc = (j.get("descriptionPlain") or "") + " " + " ".join(
                    clean(l.get("text", "")) + " " + clean(l.get("content", "")) for l in j.get("lists", []))
                jobs.append({"title": j.get("text", ""), "location": " | ".join(filter(None, locs)),
                             "url": j.get("hostedUrl", ""), "description": desc})
            return jobs
    return None


def ashby(slug):
    d = get_json(f"https://api.ashbyhq.com/posting-api/job-board/{slug}")
    if not d or "jobs" not in d:
        return None
    jobs = []
    for j in d["jobs"]:
        locs = [j.get("location", "")] + [s.get("location", "") for s in j.get("secondaryLocations") or []]
        addr = ((j.get("address") or {}).get("postalAddress") or {})
        locs.append(addr.get("addressCountry", "") or "")
        jobs.append({"title": j.get("title", ""), "location": " | ".join(filter(None, locs)),
                     "url": j.get("jobUrl", ""), "description": j.get("descriptionPlain") or j.get("descriptionHtml", "")})
    return jobs


def workable(slug):
    d = get_json(f"https://apply.workable.com/api/v1/widget/accounts/{slug}", params={"details": "true"})
    if not d or not d.get("jobs"):
        return None
    jobs = []
    for j in d["jobs"]:
        locs = [j.get("city", ""), j.get("state", ""), j.get("country", "")]
        locs += [" ".join(filter(None, [l.get("city"), l.get("country")])) for l in j.get("locations") or []]
        jobs.append({"title": j.get("title", ""), "location": " | ".join(filter(None, locs)),
                     "url": j.get("url") or j.get("shortlink", ""), "description": j.get("description", "")})
    return jobs


def smartrecruiters(slug):
    # The API answers 200 with zero results for any made-up slug, so only a non-empty
    # result counts as "found". Filtering by country keeps the payload small.
    d = get_json(f"https://api.smartrecruiters.com/v1/companies/{slug}/postings", params={"country": COUNTRY_CODE.lower(), "limit": 100})
    if not d or not d.get("content"):
        return None
    jobs = []
    for j in d["content"]:
        loc = j.get("location") or {}
        jobs.append({"title": j.get("name", ""),
                     "location": " ".join(filter(None, [loc.get("city"), loc.get("country"), COUNTRY_NAME if (loc.get("country") or "").upper() == COUNTRY_CODE else ""])),
                     "url": f"https://jobs.smartrecruiters.com/{slug}/{j.get('id')}",
                     "description": "", "_sr_ref": j.get("ref")})
    return jobs


def recruitee(slug):
    d = get_json(f"https://{slug}.recruitee.com/api/offers/")
    if not d or not d.get("offers"):
        return None
    return [{"title": j.get("title", ""),
             "location": " | ".join(filter(None, [j.get("location", ""), j.get("country", ""), j.get("city", "")])),
             "url": j.get("careers_url", ""), "description": j.get("description", "") + " " + (j.get("requirements") or "")}
            for j in d["offers"]]


def comeet(url):
    r = http("GET", url)
    if r.status_code != 200:
        return None
    m = re.search(r"COMPANY_POSITIONS_DATA\s*=\s*(\[.*?\])\s*;", r.text, re.S)
    if not m:
        return None
    jobs = []
    for j in json.loads(m.group(1)):
        loc = j.get("location") or {}
        jobs.append({"title": j.get("name", ""),
                     "location": " | ".join(filter(None, [loc.get("name"), loc.get("city"), loc.get("country"),
                                                          COUNTRY_NAME if (loc.get("country") or "").upper() == COUNTRY_CODE else ""])),
                     "url": j.get("url_active_page") or j.get("url_comeet_hosted_page") or url,
                     "description": "", "_comeet_page": j.get("url_comeet_hosted_page")})
    return jobs


def jobvite(slug):
    # Server-rendered list; descriptions are loaded by JavaScript, so candidates come back
    # without one and Claude reads the job page itself when needed.
    r = http("GET", f"https://jobs.jobvite.com/{slug}/jobs")
    if r.status_code != 200 or f"/{slug}/job/" not in r.text:
        return None
    jobs = []
    for m in re.finditer(rf'<a href="(/{re.escape(slug)}/job/[^"?]+)[^"]*"[^>]*>(.*?)</a>', r.text, re.S):
        name = re.search(r'jv-job-list-name[^>]*>(.*?)</', m.group(2), re.S)
        locm = re.search(r'jv-job-list-location[^>]*>(.*?)</div>', m.group(2), re.S)
        title = clean(name.group(1)) if name else clean(m.group(2))
        if title:
            jobs.append({"title": title, "location": clean(locm.group(1)) if locm else "",
                         "url": "https://jobs.jobvite.com" + m.group(1), "description": ""})
    return jobs


def workday(url):
    with WD_LOCK:
        return _workday(url)


def _workday(url):
    p = urlparse(url)
    tenant = p.netloc.split(".")[0]
    parts = [x for x in p.path.split("/") if x and not re.fullmatch(r"[a-z]{2}-[A-Z]{2}", x)]
    if not parts:
        return None
    site = parts[0]
    api = f"https://{p.netloc}/wday/cxs/{tenant}/{site}"
    hdr = {**UA, "Content-Type": "application/json", "Accept": "application/json"}

    def page(facets, search, offset):
        r = http("POST", f"{api}/jobs", headers=hdr,
                 json={"appliedFacets": facets, "limit": 20, "offset": offset, "searchText": search})
        return r.json() if r.status_code == 200 else None

    # Prefer the tenant's own location facet (country if offered, else the local offices):
    # a free-text country search misses jobs that only name the city.
    first = page({}, "", 0)
    if not first:
        raise RuntimeError("Workday did not answer (likely rate-limited, HTTP 429) - rerun this company later with --force")
    found = {}

    def walk(facets):
        for f in facets:
            for v in f.get("values") or []:
                if "values" in v:
                    walk([v])
                elif is_local(v.get("descriptor", "")) and f.get("facetParameter"):
                    found.setdefault(f["facetParameter"], []).append(v["id"])
    walk(first.get("facets") or [])
    country = [k for k in found if "country" in k.lower()]
    applied = {country[0]: found[country[0]]} if country else ({k: found[k]} if (k := next(iter(found), None)) else {})
    search = "" if applied else COUNTRY_NAME

    postings, offset, warning = [], 0, None
    while offset < 600:
        d = page(applied, search, offset)
        if not d:
            warning = f"partial: Workday stopped answering at offset {offset} (rate limit) - rerun later with --force"
            break
        batch = d.get("jobPostings") or []
        postings += batch
        if len(batch) < 20:
            break
        offset += 20
        time.sleep(2)
    if not postings and not warning:
        return None
    jobs = Jobs()
    jobs.warning = warning
    for j in postings:
        path = j.get("externalPath", "")
        jobs.append({"title": j.get("title", ""), "location": path.split("/")[2].replace("-", " ") if path.count("/") >= 2 else j.get("locationsText", ""),
                     "url": f"https://{p.netloc}/{site}{path}", "description": "", "_wd_api": f"{api}{path}"})
    return jobs


def fill_details(job):
    """Fetch full descriptions for sources whose list endpoint omits them."""
    try:
        if job.get("_wd_api"):
            with WD_LOCK:
                d = get_json(job["_wd_api"]) or {}
                time.sleep(1)
            info = d.get("jobPostingInfo") or {}
            job["description"] = info.get("jobDescription", "")
            locs = [info.get("location", "")] + (info.get("additionalLocations") or [])
            job["location"] = " | ".join(filter(None, locs)) or job["location"]
        elif job.get("_comeet_page"):
            r = http("GET", job["_comeet_page"])
            m = re.search(r"POSITION_DATA\s*=\s*(\{.*?\})\s*;\s*\n", r.text, re.S)
            if m:
                det = (json.loads(m.group(1)).get("custom_fields") or {}).get("details") or []
                job["description"] = " ".join(f'{d.get("name", "")}: {d.get("value", "")}' for d in det)
        elif job.get("_sr_ref"):
            d = get_json(job["_sr_ref"]) or {}
            sec = ((d.get("jobAd") or {}).get("sections") or {})
            job["description"] = " ".join((sec.get(k) or {}).get("text", "") for k in ("jobDescription", "qualifications"))
    except requests.RequestException:
        pass
    for k in ("_wd_api", "_sr_ref", "_comeet_page"):
        job.pop(k, None)
    return job


SLUG_ADAPTERS = [("greenhouse", greenhouse), ("lever", lever), ("ashby", ashby),
                 ("workable", workable), ("smartrecruiters", smartrecruiters), ("recruitee", recruitee), ("jobvite", jobvite)]


def probe(target):
    company = target["company"]
    res = {"company": company, "sources": [], "local_jobs_total": 0, "candidates": [], "errors": []}
    raw = []
    for kind, fn in (("workday", workday), ("comeet", comeet)):
        if target.get(kind):
            try:
                jobs = fn(target[kind])
                if jobs is not None:
                    res["sources"].append(f"{kind}:{target[kind]}")
                    raw += [dict(j, source=kind) for j in jobs]
                    if getattr(jobs, "warning", None):
                        res["errors"].append(f"{kind}: {jobs.warning}")
                        res["partial"] = True
                else:
                    res["errors"].append(f"{kind}: no jobs parsed from {target[kind]}")
            except Exception as e:  # noqa: BLE001 - report and continue
                res["errors"].append(f"{kind}: {e}")
                res["partial"] = True
    # An explicit Workday/Comeet URL means we already know the company's board; slug
    # guessing would only add slow requests and risk matching a different company.
    adapters = [] if (target.get("workday") or target.get("comeet")) else SLUG_ADAPTERS
    deadline = time.time() + 120  # slug guessing against slow/dead hosts can otherwise take many minutes
    for kind, fn in adapters:
        for slug in slug_candidates(company, target.get("slugs")):
            if time.time() > deadline:
                res["errors"].append("slug probing stopped after 120s (time budget)")
                break
            try:
                jobs = fn(slug)
            except Exception as e:  # noqa: BLE001
                res["errors"].append(f"{kind}/{slug}: {type(e).__name__}")
                continue
            if jobs is not None:
                res["sources"].append(f"{kind}:{slug}")
                raw += [dict(j, source=kind) for j in jobs]
                break  # first matching slug per ATS is enough

    seen = set()
    local = []
    for j in raw:
        key = (j["title"].strip().lower(), j["url"])
        if key in seen:
            continue
        seen.add(key)
        # SmartRecruiters is already filtered by country server-side.
        if is_local(j.get("location", "")) or j["source"] in ("smartrecruiters",):
            local.append(j)
    res["local_jobs_total"] = len(local)
    # All local titles, so Claude can sanity-check the slug matched the right company
    # and notice anything the title pre-filter wrongly dropped.
    res["local_titles"] = sorted({j["title"].strip() for j in local})

    cands = [j for j in local if title_ok(j["title"])]
    workers = 2 if any(j["source"] == "workday" for j in cands) else 6
    with ThreadPoolExecutor(max_workers=workers) as ex:
        cands = list(ex.map(fill_details, cands))
    for j in cands:
        # Workday's search is fuzzy; re-check location after details are known.
        if j["source"] == "workday" and not is_local(j.get("location", "")):
            continue
        desc = clean(j.get("description", ""), 6000)
        res["candidates"].append({"title": j["title"], "location": j.get("location", ""), "url": j["url"],
                                  "source": j["source"], "stack_hits": stack_hits(desc + " " + j["title"]),
                                  "description": desc[:4000]})
    return res


def safe_name(s):
    return re.sub(r"[^\w.-]+", "_", s, flags=re.U).strip("_")[:80] or "company"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("targets")
    ap.add_argument("out_dir")
    ap.add_argument("--profile", required=True, help="profile.json with country_code, title filters and keywords")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    with open(a.profile, encoding="utf-8") as f:
        configure(json.load(f))
    with open(a.targets, encoding="utf-8") as f:
        targets = json.load(f)
    os.makedirs(a.out_dir, exist_ok=True)
    todo = []
    for t in targets:
        path = os.path.join(a.out_dir, safe_name(t["company"]) + ".json")
        if os.path.exists(path) and not a.force:
            continue
        todo.append((t, path))
    print(f"{len(targets)} targets, {len(todo)} to probe", flush=True)
    with ThreadPoolExecutor(max_workers=a.workers) as ex:
        futs = {ex.submit(probe, t): (t, p) for t, p in todo}
        for fut in as_completed(futs):
            t, p = futs[fut]
            try:
                r = fut.result()
            except Exception as e:  # noqa: BLE001
                r = {"company": t["company"], "sources": [], "local_jobs_total": 0, "candidates": [], "errors": [str(e)]}
            with open(p, "w", encoding="utf-8") as f:
                json.dump(r, f, ensure_ascii=False, indent=1)
            src = ",".join(s.split(":")[0] for s in r["sources"]) or "NO FEED"
            print(f"{r['company']}: {src} | local={r['local_jobs_total']} candidates={len(r['candidates'])}" + (" PARTIAL" if r.get("partial") else ""), flush=True)


if __name__ == "__main__":
    main()
