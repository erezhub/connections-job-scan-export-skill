"""Parse a LinkedIn Connections.csv export and group connections by company.

Usage:
    python extract_companies.py <Connections.csv> <out.json> [--merge merge.json]

merge.json (optional) maps a company-name variant to the canonical name, e.g.
    {"whitesource": "Mend.io", "mend": "Mend.io"}
Keys are compared after normalization (lower case, legal suffixes like Ltd/Inc removed).

LinkedIn exports start with a few "Notes:" lines before the real header, so we
scan for the header row instead of assuming it's line 1.

Output JSON: list of
  {"company": canonical name, "aliases": [raw names], "connections": [{name, position, url}],
   "noise": reason-or-null, "maybe_recruiter": bool}
sorted by number of connections (desc). Entries with a non-null "noise" are
not real employers (blank, freelance, ...) and should be skipped. "maybe_recruiter"
is only a hint -- Claude makes the final call on which companies to scan.
"""
import csv
import json
import re
import sys
from collections import OrderedDict

NOISE_PATTERNS = [
    (r"^[\s.\-]*$", "blank"),
    (r"free\s*-?lanc", "freelance"),
    (r"self[\s-]*employ", "self-employed"),
    (r"stealth", "stealth startup"),
    (r"^(unemployed|looking for|open to work|seeking|retired|n/?a|none|-+)\b", "not employed"),
    (r"^(student|university|college|the open university)\b", "student/academia"),
    (r"פרילנס|עצמאי", "freelance"),
]

# Staffing / recruiting / outsourcing hints (international plus some common Israeli firms). Not exhaustive.
RECRUITER_HINTS = [
    "robert half", "randstad", "hays", "kforce", "teksystems", "michael page", "page group", "kelly services",
    "insight global", "aerotek", "harvey nash", "cpl ", "spencer ogden", "modis", "akkodis",
    "techjob", "gotfriends", "jobinfo", "linkmeout", "picaro", "matrix", "ness technologies",
    "sela", "jump start", "jumpstart", "manpower", "adecco", "hunter", "recruit", "staffing",
    "talent", "headhunt", "placement", "hr ", "השמה", "גיוס", "ethosia", "nisha", "sqlink",
    "experis", "allstars", "elad systems", "malam", "one technologies", "john bryce",
    "aman group", "infinity labs", "naya", "hackeru", "academy", "bootcamp", "college",
]

# Known renames / variants that should be merged into one company. Extended at runtime
# with --merge; leftover duplicates can also be merged later via targets.json "merge".
MERGE = {}

SUFFIXES = re.compile(
    r"[\s,]+(ltd\.?|inc\.?|llc|corp\.?|corporation|limited|technologies|technology|"
    r"group|israel|il|r&d|r & d|center|centre|bv|gmbh|plc|co\.?|labs?)$",
    re.I,
)


def normalize(name: str) -> str:
    n = name.strip().lower()
    n = re.sub(r"\s*[|(\[].*$", "", n)  # drop "| tagline" or "(formerly X)"
    n = n.rstrip(" .,-")
    prev = None
    while prev != n:
        prev = n
        n = SUFFIXES.sub("", n).strip()
    return n


def main(csv_path: str, out_path: str) -> None:
    hdr_needed = "First Name"
    with open(csv_path, encoding="utf-8-sig", errors="replace") as f:
        rows = list(csv.reader(f))
    try:
        hdr_idx = next(i for i, r in enumerate(rows) if r and r[0].strip() == hdr_needed)
    except StopIteration:
        sys.exit("No 'First Name' header row found - is this LinkedIn's Connections.csv export?")
    header = [h.strip() for h in rows[hdr_idx]]
    col = {h: i for i, h in enumerate(header)}

    groups: "OrderedDict[str, dict]" = OrderedDict()
    for r in rows[hdr_idx + 1:]:
        if len(r) < len(header):
            continue
        raw = r[col["Company"]].strip()
        key = normalize(raw)
        canonical = MERGE.get(key)
        if canonical:
            key = normalize(canonical)
        g = groups.setdefault(key, {"company": canonical or raw, "aliases": set(), "connections": []})
        g["aliases"].add(raw)
        g["connections"].append({
            "name": f'{r[col["First Name"]].strip()} {r[col["Last Name"]].strip()}'.strip(),
            "position": r[col["Position"]].strip(),
            "url": r[col["URL"]].strip(),
        })

    out = []
    for key, g in groups.items():
        noise = next((why for pat, why in NOISE_PATTERNS if re.search(pat, key, re.I)), None)
        low = " " + " ".join([key] + [a.lower() for a in g["aliases"]]) + " "
        maybe_rec = any(h in low for h in RECRUITER_HINTS)
        # Pick the most common alias as display name unless a canonical merge name exists.
        if g["company"] not in MERGE.values():
            names = [c for c in g["aliases"] if c]
            # shortest variant is usually the cleanest ("Wix" vs "Wix.com Ltd | We're hiring")
            g["company"] = min(names, key=len) if names else ""
        out.append({
            "company": g["company"],
            "aliases": sorted(g["aliases"]),
            "connections": g["connections"],
            "noise": noise,
            "maybe_recruiter": maybe_rec,
        })
    out.sort(key=lambda x: -len(x["connections"]))

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)

    real = [o for o in out if not o["noise"]]
    print(f"{sum(len(o['connections']) for o in out)} connections, {len(out)} company groups, "
          f"{len(real)} after dropping noise, {sum(o['maybe_recruiter'] for o in real)} flagged as possible recruiters")


if __name__ == "__main__":
    args = sys.argv[1:]
    if "--merge" in args:
        i = args.index("--merge")
        with open(args[i + 1], encoding="utf-8") as f:
            MERGE.update({normalize(k): v for k, v in json.load(f).items()})
        del args[i:i + 2]
    main(args[0], args[1])
