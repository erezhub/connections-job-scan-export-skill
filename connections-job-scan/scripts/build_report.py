"""Merge probe results, Claude's fit judgments and connections into report.json for write_excel.py.

Usage:
    python build_report.py <work_dir> [--judgments judgments.json] [--out report.json]

Reads from <work_dir>:
  companies.json   (from extract_companies.py) - to attach connections to each company
  targets.json     (the companies chosen in step 2) - defines the coverage list
  probe/*.json     (from probe_ats.py)
  fallback/*.json  (optional, step-4 results: {company, method, how, local_jobs, notes, matches:[{title, location, url, fit, why, verified}]})
  profile.json     (optional) - country and role_query are copied into the report for search links
  judgments.json   written by Claude:
    {
      "jobs": [
        {"company": "Cato Networks", "url": "<job url>", "fit": "Strong|Good|Stretch", "why": "..."},
        # title/location are taken from the probe candidate with the same url; give them
        # explicitly for jobs found by WebFetch/WebSearch that aren't in any probe file:
        {"company": "Personetics", "url": "...", "title": "Software Architect", "location": "Tel Aviv",
         "fit": "Good", "why": "..."}
      ],
      "coverage": {   # optional per-company overrides / notes
        "Komodor": {"method": "blocked", "notes": "careers site 403"},
        "Sunbit": {"method": "webfetch", "local_jobs": 8, "notes": "no Java/Go backend role open"}
      }
    }
Jobs judged unsuitable are simply left out of "jobs".
"""
import argparse
import glob
import json
import os
import re
from datetime import date


def norm(s):
    return re.sub(r"[^a-z0-9א-ת]+", "", (s or "").lower())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("work")
    ap.add_argument("--judgments", default=None)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    w = a.work
    load = lambda p: json.load(open(p, encoding="utf-8"))

    companies = load(os.path.join(w, "companies.json"))
    conn_by = {}
    for c in companies:
        for name in [c["company"], *c.get("aliases", [])]:
            if name:
                conn_by.setdefault(norm(name), c["connections"])

    targets = load(os.path.join(w, "targets.json")) if os.path.exists(os.path.join(w, "targets.json")) else []
    merges = {t["company"]: t.get("merge", []) for t in targets}

    def connections(company):
        # targets.json may list extra company-name variants under "merge" (e.g. "Wix" + "Wix.com")
        out, seen = [], set()
        for name in [company, *merges.get(company, [])]:
            for c in conn_by.get(norm(name), []):
                if c["url"] not in seen:
                    seen.add(c["url"])
                    out.append(c)
        return out

    probes = {}
    for p in glob.glob(os.path.join(w, "probe", "*.json")):
        r = load(p)
        probes[r["company"]] = r
    by_url = {}
    for r in probes.values():
        for cnd in r.get("candidates", []):
            by_url[cnd["url"]] = cnd

    j = load(a.judgments or os.path.join(w, "judgments.json"))
    j.setdefault("jobs", [])
    j.setdefault("coverage", {})
    # Fallback results (step 4, often written by batch subagents): one file per company with its own
    # matches and coverage info. They're merged in as if they were judgments.
    for p in glob.glob(os.path.join(w, "fallback", "*.json")):
        fb = load(p)
        for m in fb.get("matches", []):
            why = m.get("why", "")
            if m.get("verified") is False and "unverified" not in why.lower():
                why = (why + " (unverified - seen only on an aggregator)").strip()
            j["jobs"].append({**m, "company": fb["company"], "why": why})
        cov = j["coverage"].setdefault(fb["company"], {})
        cov.setdefault("method", fb.get("method"))
        if fb.get("local_jobs") is not None:
            cov.setdefault("local_jobs", fb["local_jobs"])
        cov.setdefault("notes", " ".join(x for x in [fb.get("notes", ""), f'[{fb["how"]}]' if fb.get("how") else ""] if x))
    matches, missing = [], []
    for job in j.get("jobs", []):
        cnd = by_url.get(job["url"], {})
        title = job.get("title") or cnd.get("title")
        if not title:
            missing.append(job["url"])
            continue
        conns = connections(job["company"])
        if not conns:
            print(f"warning: no connections found for company '{job['company']}' - check spelling vs companies.json")
        matches.append({"company": job["company"], "job_title": title.strip(),
                        "location": job.get("location") or cnd.get("location", ""),
                        "url": job["url"], "fit": job["fit"], "why": job.get("why", ""),
                        "connections": conns})
    if missing:
        print("warning: these judged jobs have no title (not in probe files, none given):", *missing, sep="\n  ")

    names = [t["company"] for t in targets] or list(probes)
    for extra in j.get("coverage", {}):
        if extra not in names:
            names.append(extra)
    cov = []
    for name in names:
        r = probes.get(name, {})
        o = j.get("coverage", {}).get(name, {})
        method = o.get("method") or (",".join(s.split(":")[0] for s in r.get("sources", [])) or "not found")
        notes = o.get("notes", "")
        if r.get("partial") and "partial" not in notes:
            notes = ("PARTIAL scan (rate-limited). " + notes).strip()
        cov.append({"company": name, "method": method,
                    "local_jobs": o.get("local_jobs", r.get("local_jobs_total") if r.get("sources") else None),
                    "matches": sum(1 for m in matches if m["company"] == name),
                    "connections": len(connections(name)), "notes": notes,
                    "connection_list": connections(name)})

    prof_path = os.path.join(w, "profile.json")
    prof = load(prof_path) if os.path.exists(prof_path) else {}
    out = a.out or os.path.join(w, "report.json")
    json.dump({"generated": date.today().isoformat(), "country": prof.get("country", ""),
               "role_query": prof.get("role_query", ""), "matches": matches, "coverage": cov},
              open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    fits = {}
    for m in matches:
        fits[m["fit"]] = fits.get(m["fit"], 0) + 1
    print(f"wrote {out}: {len(matches)} matches {fits}, {len(cov)} companies in coverage")


if __name__ == "__main__":
    main()
