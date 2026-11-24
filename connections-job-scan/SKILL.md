---
name: connections-job-scan
description: Finds open jobs at the companies where the user's LinkedIn connections work. Reads the user's LinkedIn Connections.csv export and their CV, picks out the real employers in the network, checks each company's career site / job board for open positions in the user's target country that match the CV, and produces an Excel report of connection name → company → relevant open position, so the user knows whom to ask for a referral. Use this whenever the user wants to find jobs through their network, asks which connections work at companies that are hiring, says things like "scan my connections for jobs", "who in my network can refer me", "check my LinkedIn connections' companies for open positions", "איפה יש משרות אצל אנשי הקשר שלי", or mentions Connections.csv together with job hunting, referrals or career pages, even if they don't spell out every step.
---

# Connections → open positions scan

Goal: for each real employer in the user's LinkedIn network, find open roles **in the user's target
country** that fit **the user's CV**, and say which connections work there (so the user knows whom to
ask for a referral). Output is an Excel file plus a short summary in chat.

This is a long job (often hundreds of companies). Work in a folder on disk so an interrupted run can
resume, and let the bundled scripts do the bulk of the fetching. Your judgment is needed for four
things the scripts can't do: understanding the candidate, deciding which companies count, finding job
boards the scripts miss, and deciding which jobs genuinely fit.

Scripts live in `scripts/` next to this file (`<skill_dir>` below). They need Python 3 with `requests`
and `openpyxl`. Check once with `python -c "import requests, openpyxl"` and, if that fails, ask the user
before running `pip install requests openpyxl`. On Windows, set `PYTHONUTF8=1` so non-English company
names don't break the console.

## 0. Inputs, profile and work folder

**Connections file.** Use the path the user gives. Otherwise look for `Connections.csv` in the
Downloads folder (or an unzipped LinkedIn data export there). If there isn't one, explain how to get it:
LinkedIn → Settings → Data privacy → *Get a copy of your data* → tick *Connections* → request archive;
LinkedIn emails a download link, usually within about 10 minutes. Then stop until they have it.

**CV.** Use the path the user gives. Otherwise look in Downloads and Documents for recent files whose
name contains CV, Resume or Résumé (.docx, .pdf, .md, .txt). If there are several, prefer the general one
over copies tailored to a single company, and ask if it's unclear. Read it on every run, because the CV
changes. A .docx is a zip: the text is in `word/document.xml`. If there's no CV, ask the user to describe
their role, main skills, seniority and location in a few lines and use that.

**Work folder.** `job-scan-<YYYY-MM-DD>/` next to the connections file. If a folder from today already
exists, reuse it (resume) instead of starting over. The final Excel goes next to the connections file.

**Profile.** From the CV, write `<work>/profile.json`. Every later step reads it, including the
subagents in step 4, so put everything they need to judge fit in it:

```json
{
  "summary": "Backend developer, 10+ yrs. Java + Spring Boot, some Go. Microservices, Kafka, AWS, Docker. Domains: fintech, security.",
  "role_query": "backend developer",
  "country": "Israel",
  "country_code": "IL",
  "location_terms": [],
  "remote_terms": ["remote - israel", "remote, israel"],
  "title_include": ["engineer", "developer", "programmer", "back[\\s-]?end", "server", "software", "architect", "platform"],
  "title_exclude": ["front[\\s-]?end(?!.*back)", "\\bqa\\b", "\\btest", "hardware", "embedded", "devops", "\\bsre\\b",
                    "data scien", "machine learning", "\\bsales", "marketing", "manager", "director", "head of",
                    "team lead", "intern\\b", "student", "junior"],
  "keywords": ["java", "spring", "go", "kotlin", "kafka", "microservices", "aws", "docker", "kubernetes", "sql"],
  "exclude_companies": ["<current and former employers from the CV>"],
  "fit_rules": {
    "strong": "backend role whose main stack is Java/JVM or Go, mid to senior/staff level",
    "good": "backend role with no named language or Java/Go among options; backend-heavy full-stack on a JVM stack",
    "stretch": "solid backend role in another language (Node, Python, C#) where the experience carries over",
    "leave_out": "frontend-heavy, DevOps/SRE, data science, embedded, managers/team leads, junior roles, jobs outside the country"
  }
}
```

That example is for a backend developer. Write each field for the actual candidate:
- **Role family and level.** A product manager, data scientist or designer needs completely different
  `title_include` / `title_exclude` lists, keywords and fit rules. Seniority matters. A senior person
  usually doesn't want junior roles, and someone with 2 years doesn't want staff roles. Whether
  people-manager roles count depends on the CV, so ask when it's unclear.
- **Country.** Use the CV's location unless the user says otherwise. `country_code` is the ISO 2-letter
  code. `probe_ats.py` has built-in city lists for IL, GB, US and DE. For any other country, add its
  main tech cities to `location_terms` (lower case; regex fragments are fine), because many job feeds
  name only the city.
- **Title filters.** These are a cheap pre-filter, so keep them loose. A wrongly excluded title is a
  missed job, while a wrongly included one costs only a quick look. `title_include: []` keeps every title.
- **Keywords.** Use the candidate's main skills plus a few common alternatives. Seeing "python: 6" on a
  Java candidate's job is a useful signal too.
- **exclude_companies.** List the current and former employers from the CV. People rarely want their own
  or past employers scanned. Mention this in the confirmation, since some users do want them included.

Before the long scan starts, show the user the profile in a few plain lines: role and level, country,
main skills, which kinds of jobs count and which are left out, and which employers are excluded. Ask them
to confirm or correct it. This is the one place to stop and ask. A wrong country or role family would
waste the whole run, while everything later can carry on without asking.

## 1. Extract companies

```
python <skill_dir>/scripts/extract_companies.py "<Connections.csv>" "<work>/companies.json"
```

This handles LinkedIn's "Notes:" lines at the top of the file, groups connections by company, marks noise
(blank, freelance, self-employed, stealth, students) and flags likely recruiters. Each entry keeps its
connections (name, position, LinkedIn URL). To merge known renames up front (e.g. a company and its old
name), pass `--merge merge.json` with `{"old name": "New Name"}`. Leftover duplicates can also be merged
later in targets.json.

## 2. Decide which companies to scan

Go through the non-noise entries and keep **companies that plausibly hire the candidate's kind of role
in the target country**:
- Keep: product and tech companies with an office or R&D center in the country, including global
  companies, and big non-tech employers with real in-house teams for this role (banks, insurers,
  retailers, media groups). For non-engineering roles (product, design, data, marketing), the set of
  relevant employers is wider. Use common sense about who hires that role.
- Drop: recruiting and staffing agencies, outsourcing body-shops (unless the user wants them), training
  schools and bootcamps, government and military units, small local businesses unrelated to the role,
  foreign companies with no presence in the country, and everything in `exclude_companies`.
- Names you don't recognise (including non-English ones): work out what the company is from the name and
  the connections' positions. A single quick WebSearch is fine. If it's still unclear, drop it and note
  that in the decisions file.
- Merge leftover duplicates ("Acme" vs "Acme Ltd") by listing the extra names under `"merge"`.

Write `<work>/targets.json`: a list of `{"company": ..., "slugs": [...], "workday": url, "comeet": url,
"merge": [other names]}`. Only `company` is required. Before writing it, read
`references/career-sites.md` and add any known slugs or URLs from there. Save the kept/dropped decision
with a reason per company to `<work>/company_decisions.json`. Then tell the user in one line how many
companies you kept, with a few examples of what you dropped, and carry on.

## 3. Probe job boards (scripted)

```
python <skill_dir>/scripts/probe_ats.py "<work>/targets.json" "<work>/probe" --profile "<work>/profile.json" --workers 8
```

For each company, this tries the public feeds of Greenhouse, Lever, Ashby, Workable, SmartRecruiters,
Recruitee and Jobvite (plus Workday and Comeet when given a URL). It keeps jobs located in the target
country and applies the profile's title filters. It writes one JSON per company with the candidates'
full descriptions and a `stack_hits` count of the profile keywords. Already-probed companies are skipped
on rerun, so it's safe to run again after adding slugs (use `--force` to redo one).

How to read the results:
- `"sources": []` means no feed was found, so the company goes to step 4.
- `"partial": true` means Workday rate-limited the scan. Rerun just those companies at the end with
  `--force --workers 1`. Workday calls are already serialized and paced.
- Check `local_titles` for companies found through a guessed slug, especially generic one-word slugs.
  If the titles don't look like this company, the slug hit a different company's board: drop that source
  and treat the company as no-feed. This happens more often than you'd think.
- `local_titles` also shows what the title filter dropped. Skim it for jobs the filter got wrong.
- Candidates with an empty `description` (Jobvite always, sometimes others) need a WebFetch of the job
  URL before you can judge fit. Only do this for titles that look plausible.

## 4. Fallback for companies with no feed

Many companies use their own portals, regional job boards, or pages that need JavaScript. For each one:
1. Check `references/career-sites.md`.
2. WebSearch for the job board: `"<company>" careers <country>`, or
   `"<company>" greenhouse OR lever OR ashbyhq OR workable OR myworkdayjobs`. In Israel, also try
   `site:comeet.com "<company>"`. If you find a supported board, add the slug or URL to targets.json and
   rerun the probe for that company with an explicit slug. That's cheaper and more complete than reading
   pages by hand.
3. Otherwise, WebFetch the careers page or job search page with a country/role filter and pull out the
   matching jobs yourself.
4. Spend about 3–4 tool calls per company at most. If you're still stuck, record it as `not found` or
   `blocked` with a note. A visible gap in the "Check manually" sheet is better than a long dig on one
   company, and the user can follow up by hand.

Be careful with aggregator sites (builtin, VC portfolio boards, job-search engines). They're full of
closed postings. In earlier runs they listed many roles that the companies' own boards no longer had. Use
them to discover which ATS a company uses. Only report a job found only on an aggregator if you can't
reach the company's own site, and then set `"verified": false`.

Respect sites that block automated access (403, 429, captcha). Use search results instead and don't
try to get around the block. LinkedIn job pages need a login, so don't rely on them.

With many fallback companies (more than about 20), split them into batches of about 15 and give each
batch to a general-purpose subagent. Copy `references/fallback-agent-instructions.md` to
`<work>/fallback_instructions.md`, fill in its placeholders, and give each agent a short prompt: "Read and
follow <file>. Your batch: [...]". Each agent writes one `<work>/fallback/<company>.json` per company,
which `build_report.py` merges automatically. Run at most about 6 agents at once; more has exhausted
memory. When an agent stalls, check which companies have no result file and relaunch only those. Start
with the companies that have the most connections.

Whenever you learn how a company publishes jobs, add a line to `references/career-sites.md`, so the
next run needs fewer lookups.

## 5. Decide which jobs fit

Read each candidate's description; don't judge by the title alone. The pre-filter is deliberately loose.
Rate each job with the profile's `fit_rules`:
- **Strong**: the candidate could apply today with a good chance. The role family, main skills and
  level match.
- **Good**: a clear fit with a gap, e.g. the stack isn't named, the candidate's skill is one of several
  options, or the role is adjacent.
- **Stretch**: same role family, but the main tool or stack differs and the experience carries over.
  Include these but keep them labelled.
- **Leave out**: everything in `leave_out`, plus jobs located only outside the country. Remote roles
  open to residents of the country count as local.

For each kept job, write a one-line `why` that names the concrete overlap (and the gap, if any), e.g.
"Java/Spring + Kafka microservices, 5+ yrs backend" or "Go data platform; Go is secondary in CV".

## 6. Build the report

Write your decisions to `<work>/judgments.json`, using the format in the docstring of
`scripts/build_report.py`. Each kept job needs `company`, `url`, `fit` and `why`. Add `title` and
`location` for jobs found by WebFetch or WebSearch. Also give per-company `coverage` notes for blocked,
not-found and partial companies. Then merge everything (this attaches each company's connections
automatically):

```
python <skill_dir>/scripts/build_report.py "<work>"
python <skill_dir>/scripts/write_excel.py "<work>/report.json" "<folder of Connections.csv>/Connections_Job_Matches_<YYYY-MM-DD>.xlsx"
```

The workbook has two sheets:
- **Matches**: one row per job (company, connections, title, location, fit, why, link), Strong first.
- **Check manually**: every company whose coverage method is `blocked` or `not found`, with its
  connections, the reason, a careers link when one is known, and a Google search link. The user checks
  these by hand, so make each coverage `notes` field say why the company couldn't be checked, and put
  the careers URL in `how`.

## 7. Tell the user

Give a short chat summary:
- The file path.
- The headline numbers: companies scanned, companies with matches, Strong/Good/Stretch counts.
- The top ~10 Strong matches as a compact table: connection(s) | company | job title.
- The coverage gaps: how many companies are on the "Check manually" sheet, with the notable names.

End the summary with this signature, exactly as written, after a separator line:

```
---
created by eRez Huberman (c)
https://www.linkedin.com/in/erezhuberman/
```
