# Fallback job lookup: instructions for each batch agent

Template. Copy it to `<WORK>/fallback_instructions.md` and replace `<WORK>`, `<SKILL_DIR>`, `<COUNTRY>` and
`<ROLE>` (e.g. "backend developer"). Then give each subagent a short prompt: "Read and follow <file>. Your batch: [...]".

You're helping find open **<ROLE>** jobs **in <COUNTRY>** for one candidate, at companies where the
automatic job-board scan found nothing. Your batch is a list of companies. For each one, find the
company's current open positions in <COUNTRY>, decide which fit the candidate, and write one result file.

## Candidate profile and fit rules
Read `<WORK>/profile.json` first. `summary` describes the candidate (from their CV) and `fit_rules`
defines Strong / Good / Stretch / leave out. Judge every job against those, not against your own idea
of the candidate.

## Working rules
- Write each company's result file **as soon as you finish that company**, not at the end. Agents can
  stall or be cut off (e.g. a session login expiring), and anything unwritten is lost.
- Never run a command that can hang for minutes. Only run `probe_ats.py` with an explicit slug or URL,
  because slug guessing can take about 5 minutes per company.
- If Workday or Workable answer 429, they rate-limit the whole machine for hours. Switch to WebSearch/WebFetch.

## How to look (about 3–4 tool calls per company, then move on)
1. If the careers site is on a supported job board (Greenhouse, Lever, Ashby, Workable, SmartRecruiters,
   Recruitee, Jobvite, Comeet `comeet.com/jobs/<name>/<XX.XXX>`, Workday `*.myworkdayjobs.com/<site>`),
   run the scanner. It's faster and complete:
   `python "<SKILL_DIR>/scripts/probe_ats.py" <tmp_targets.json> "<WORK>/probe" --profile "<WORK>/profile.json" --force --workers 1`
   with tmp_targets like `[{"company":"<exact company name>","slugs":["<slug>"]}]` or `"comeet": "<url>"` / `"workday": "<url>"`.
   Write tmp files to your own temp folder. Then read the resulting probe JSON. Candidates include descriptions.
   - SmartRecruiters trick: if a job URL has a long posting ID (e.g. 744000160612109),
     `https://api.smartrecruiters.com/v1/companies/x/postings/<id>` returns an error naming the real company identifier.
   - WebSearch `site:comeet.com "<company>"` often finds Comeet boards (common for Israeli startups).
2. Otherwise WebFetch the company's careers page or job search page (filter to <COUNTRY> / <ROLE> if
   possible), or WebSearch `"<company>" careers <COUNTRY> <ROLE>`.
3. Big tech with its own portal (Google, Microsoft, Apple, Amazon, IBM, Intel, Salesforce, SAP, Dell, Red
   Hat...): WebFetch its search page with a <COUNTRY> location and a role query, e.g.
   Google `https://www.google.com/about/careers/applications/jobs/results/?location=<COUNTRY>&q=<ROLE>`,
   Amazon `https://www.amazon.jobs/en/search?base_query=<ROLE>&loc_query=<COUNTRY>`.
4. Aggregators (builtin, jobify360, glich, echojobs, VC portfolio boards) are often stale. Use them to find
   the real board. Only report a job seen only there if the company site is unreachable, and set `"verified": false`.
5. Respect blocks (403/429/captcha). Don't try to get around them. Record `"method": "blocked"` and move on.
   LinkedIn job pages need a login, so don't use them.

## Which jobs fit
Read requirements, not just titles, and apply `fit_rules` from profile.json. Jobs outside <COUNTRY> are
left out; remote roles open to <COUNTRY> residents count.

## Output: one file per company
Write `<WORK>/fallback/<safe>.json`, where `<safe>` is the company
name with every run of characters other than letters, digits, `.`, `_` and `-` replaced by `_`, and
leading/trailing `_` stripped. Use exactly this shape:
```json
{"company": "<exact name as given>",
 "method": "webfetch|websearch|<ats name>|blocked|not found",
 "how": "<the URL, slug or board that worked, for future runs>",
 "local_jobs": <number of open <COUNTRY> jobs seen, or null if unknown>,
 "notes": "<short: e.g. 'no matching roles open', 'site 403', 'list is JS-only'>",
 "matches": [{"title": "...", "location": "...", "url": "<direct job link>",
              "fit": "Strong|Good|Stretch", "why": "<one line naming the concrete overlap>",
              "verified": true}]}
```
Write a file for every company in your batch, including ones with no matches, so coverage is complete.
Finish with a short report: one line per company (method, local jobs, number of matches).
