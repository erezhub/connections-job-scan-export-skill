# connections-job-scan: a Claude Code skill

Finds open jobs at the companies where your LinkedIn connections work, matched against your own CV.
The result is an Excel file with the connection, the company and the matching job, so you know whom to
ask for a referral.

## What you need
- Claude Code with web search and web fetch enabled.
- Python 3 with `pip install requests openpyxl`.
- Your LinkedIn connections export: LinkedIn → Settings → Data privacy → *Get a copy of your data* →
  *Connections*. LinkedIn emails you a link to `Connections.csv`, usually within minutes.
- Your CV (.docx, .pdf, .md or .txt).

## Install
Unzip `connections-job-scan.skill` (it's a zip file) or copy the `connections-job-scan/` folder into
`~/.claude/skills/` (Windows: `%USERPROFILE%\.claude\skills\`). Restart Claude Code.

## Use
Put `Connections.csv` and your CV in your Downloads folder (or give their paths), then ask something like:

> scan my LinkedIn connections for jobs that match my CV

Claude reads your CV and shows you a short profile: role, level, country, main skills and which roles
count. Confirm or correct it, and Claude then runs the scan. This can take a while for a big network.
Interrupted runs resume from the `job-scan-<date>` folder.

The Excel file has two sheets:
- **Matches**: one row per job, rated Strong / Good / Stretch, with your connections there and a link to
  the job.
- **Check manually**: companies whose career site couldn't be read automatically, with a careers link
  and a Google search link.

It works for any role (engineering, product, data, design...) and any country. For countries other
than Israel, UK, US and Germany, Claude adds the main cities itself.

## Notes
- Your current and former employers (from the CV) are left out by default. Say so if you want them included.
- The skill respects sites that block automated access and lists those companies under "Check manually".
- `references/career-sites.md` remembers how each company publishes jobs, so later runs are faster. It
  starts with entries from Israeli tech companies.
