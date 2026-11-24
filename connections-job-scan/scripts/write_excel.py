"""Write the connections x open-positions report to an .xlsx file (sheets: "Matches", plus
"Check manually" listing companies that were blocked or had no job page found).

Usage:
    python write_excel.py <report.json> <out.xlsx>

report.json:
{
  "generated": "2026-11-19", "country": "Israel", "role_query": "backend developer",
  "matches": [   # one entry per relevant job
    {"company": "Cato Networks", "job_title": "...", "location": "Tel Aviv", "url": "https://...",
     "fit": "Strong" | "Good" | "Stretch", "why": "Java + Spring + Kafka microservices; 5+ yrs",
     "connections": [{"name": "...", "position": "...", "url": "https://linkedin..."}]}
  ],
  "coverage": [  # one entry per company that was considered
    {"company": "...", "method": "greenhouse" | "webfetch" | "websearch" | "blocked" | "not found",
     "local_jobs": 37, "matches": 6, "connections": 6, "notes": "..."}
  ]
}
"""
import json
import re
import sys
from urllib.parse import quote_plus

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

HEAD_FILL = PatternFill("solid", fgColor="1F4E78")
HEAD_FONT = Font(bold=True, color="FFFFFF")
FIT_FILL = {"Strong": "C6EFCE", "Good": "FFEB9C", "Stretch": "FCE4D6"}
FIT_ORDER = {"Strong": 0, "Good": 1, "Stretch": 2}
LINK = Font(color="0563C1", underline="single")


def sheet(wb, title, headers, widths):
    ws = wb.create_sheet(title)
    ws.append(headers)
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w
        c = ws.cell(row=1, column=i)
        c.fill, c.font = HEAD_FILL, HEAD_FONT
    ws.freeze_panes = "A2"
    ws.sheet_view.rightToLeft = False
    return ws


def link(cell, url, text=None):
    if url:
        cell.value = text or url
        cell.hyperlink = url
        cell.font = LINK


def main(src, out):
    with open(src, encoding="utf-8") as f:
        rep = json.load(f)
    matches = sorted(rep.get("matches", []),
                     key=lambda m: (FIT_ORDER.get(m.get("fit"), 9), m["company"].lower(), m["job_title"]))
    wb = Workbook()
    wb.remove(wb.active)
    wrap = Alignment(wrap_text=True, vertical="top")

    # 1. Matches: one row per job
    ws = sheet(wb, "Matches", ["Company", "Connections", "Job title", "Location", "Fit", "Why it matches", "Job link"],
               [22, 34, 40, 18, 9, 55, 14])
    for m in matches:
        conns = "\n".join(f'{c["name"]} ({c.get("position", "")})'.replace(" ()", "") for c in m.get("connections", []))
        ws.append([m["company"], conns, m["job_title"], m.get("location", ""), m.get("fit", ""), m.get("why", ""), ""])
        r = ws.max_row
        link(ws.cell(row=r, column=7), m.get("url"), "Open")
        if m.get("fit") in FIT_FILL:
            ws.cell(row=r, column=5).fill = PatternFill("solid", fgColor=FIT_FILL[m["fit"]])
        for col in range(1, 7):
            ws.cell(row=r, column=col).alignment = wrap
    ws.auto_filter.ref = ws.dimensions

    # 2. Check manually: companies that couldn't be scanned (site blocked / no job page found),
    #    so the user can look them up by hand.
    manual = [c for c in rep.get("coverage", []) if c.get("method") in ("blocked", "not found")]
    if manual:
        ws = sheet(wb, "Check manually", ["Company", "Connections", "Why not checked", "Careers link", "Search"],
                   [26, 38, 60, 14, 12])
        for c in sorted(manual, key=lambda c: (-(c.get("connections") or 0), c["company"].lower())):
            conns = "\n".join(f'{x["name"]} ({x.get("position", "")})'.replace(" ()", "")
                              for x in c.get("connection_list", []))
            notes = c.get("notes", "")
            m = re.search(r"https?://[^\s\]\)]+", notes)
            url = m.group(0).rstrip(".,;") if m else ""
            reason = re.sub(r"\s*\[[^\]]*\]\s*$", "", notes).strip() or c["method"]
            ws.append([c["company"], conns, f'{c["method"]}: {reason}', "", ""])
            r = ws.max_row
            link(ws.cell(row=r, column=4), url, "Open")
            q = quote_plus(" ".join(x for x in [c["company"], "careers", rep.get("country", ""), rep.get("role_query", "")] if x))
            link(ws.cell(row=r, column=5), f"https://www.google.com/search?q={q}", "Google")
            for col in range(1, 4):
                ws.cell(row=r, column=col).alignment = wrap
        ws.auto_filter.ref = ws.dimensions

    wb.save(out)
    print(f"wrote {out}: {len(matches)} jobs, {len(manual)} companies to check manually")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
