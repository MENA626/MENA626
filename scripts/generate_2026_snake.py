#!/usr/bin/env python3
"""Generate animated 2026 GitHub contribution calendars in light and dark themes."""
import datetime as dt
import html
import json
import os
from pathlib import Path
import urllib.request

YEAR = 2026
USER = "MENA626"
OUT = Path("dist")
DAYS = [dt.date(YEAR, 1, 1) + dt.timedelta(days=i) for i in range(365)]
START = DAYS[0] - dt.timedelta(days=(DAYS[0].weekday() + 1) % 7)
WEEKS = 53
CELL = 15
STEP = 19
LEFT, TOP = 80, 100
SVG_WIDTH = 1190
SVG_HEIGHT = 330
COLORS = {
    "light": {"bg": "#FFFFFF", "text": "#0F172A", "sub": "#475569", "empty": "#E7EDF5", "future": "#F8FAFC", "levels": ["#C6D8FF", "#8FB5FF", "#5086F3", "#1D4ED8"], "accent": "#EAB308", "snake": "#F59E0B"},
    "dark": {"bg": "#0B1220", "text": "#E6EDF7", "sub": "#9CAFC8", "empty": "#202D42", "future": "#111D2D", "levels": ["#173C74", "#2155AE", "#3B82F6", "#93C5FD"], "accent": "#FACC15", "snake": "#FACC15"},
}

def fetch_contributions():
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if not token:
        raise RuntimeError("GitHub token is required; refusing to publish invented data")
    query = """query($login: String!, $from: DateTime!, $to: DateTime!) {
      user(login: $login) {
        contributionsCollection(from: $from, to: $to) {
          contributionCalendar {
            totalContributions
            weeks { contributionDays { date contributionCount } }
          }
        }
      }
    }"""
    payload = json.dumps({"query": query, "variables": {
        "login": USER, "from": f"{YEAR}-01-01T00:00:00Z", "to": f"{YEAR}-12-31T23:59:59Z"
    }}).encode("utf-8")
    request = urllib.request.Request("https://api.github.com/graphql", data=payload, headers={
        "Authorization": f"Bearer {token}", "Content-Type": "application/json",
        "Accept": "application/vnd.github+json", "User-Agent": "menat-2026-snake"
    })
    with urllib.request.urlopen(request, timeout=40) as response:
        result = json.loads(response.read())
    if result.get("errors") or not result.get("data", {}).get("user"):
        raise RuntimeError("Could not fetch 2026 contributions: " + json.dumps(result.get("errors", result))[:700])
    weeks = result["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
    observed = {
        item["date"]: int(item["contributionCount"])
        for week in weeks for item in week["contributionDays"]
    }
    today = dt.datetime.now(dt.timezone.utc).date()
    return {day: max(0, observed.get(day.isoformat(), 0)) if day <= today else None for day in DAYS}

def level(count):
    if count <= 2: return 1
    if count <= 5: return 2
    if count <= 9: return 3
    return 4

def svg_for_theme(data, theme):
    c = COLORS[theme]
    weekly = [0] * WEEKS
    monthly = [0] * 12
    for day, count in data.items():
        if count is None:
            continue
        weekly[(day - START).days // 7] += count
        monthly[day.month - 1] += count
    peak_weeks = sorted(
        (index for index in range(WEEKS) if weekly[index] > 0),
        key=lambda index: (-weekly[index], index)
    )[:3]
    peak_month = max(range(12), key=lambda i: monthly[i]) if any(monthly) else None
    total = sum(count for count in data.values() if count is not None)

    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {SVG_WIDTH} {SVG_HEIGHT}" role="img" aria-label="2026 GitHub contribution snake for {USER}">',
        '<title>2026 Contribution Snake — MENA626</title>',
        f'<desc>Complete 2026 calendar. Gold outlines mark the three busiest contribution weeks. Total: {total}.</desc>',
        '<style>',
        f'.label{{font:600 15px ui-monospace,Consolas,monospace;fill:{c["sub"]}}}',
        f'.title{{font:800 24px ui-monospace,Consolas,monospace;fill:{c["text"]}}}',
        f'.info{{font:600 16px ui-monospace,Consolas,monospace;fill:{c["text"]}}}',
        '.head,.tail{animation:crawl 38s linear infinite}',
        '.head{filter:drop-shadow(0 0 3px #FBBF24)}',
        '@keyframes crawl{',
    ]
    track = [
        (column, row)
        for row in range(7)
        for column in (range(WEEKS) if row % 2 == 0 else range(WEEKS - 1, -1, -1))
    ]
    for index, (column, row) in enumerate(track):
        percent = 100 * index / len(track)
        x, y = LEFT + column * STEP + CELL / 2, TOP + row * STEP + CELL / 2
        out.append(f'{percent:.4f}%{{transform:translate({x:.1f}px,{y:.1f}px)}}')
    out.append(f'100%{{transform:translate({LEFT+CELL/2:.1f}px,{TOP+CELL/2:.1f}px)}}')
    out.extend([
        '}</style>',
        f'<rect width="{SVG_WIDTH}" height="{SVG_HEIGHT}" rx="22" fill="{c["bg"]}"/>',
        f'<text class="title" x="{LEFT}" y="45">2026 // CONTRIBUTION SNAKE</text>',
        f'<text class="label" x="{LEFT}" y="70">REAL ACTIVITY · JAN 01 — DEC 31 · {USER}</text>',
    ])
    for month in range(1, 13):
        first = dt.date(YEAR, month, 1)
        column = (first - START).days // 7
        month_color = (
            c["accent"] if peak_month == month-1 and monthly[month-1] else c["sub"]
        )
        out.append(
            f'<text x="{LEFT+column*STEP}" y="90" font-family="monospace" '
            f'font-size="12" font-weight="700" fill="{month_color}">{first:%b}</text>'
        )
    for row, label in ((0, "SUN"), (2, "TUE"), (4, "THU"), (6, "SAT")):
        out.append(f'<text class="label" x="16" y="{TOP+row*STEP+12}">{label}</text>')
    for index in peak_weeks:
        x = LEFT + index * STEP - 3
        out.append(
            f'<rect x="{x}" y="{TOP-4}" width="{STEP+2}" height="{7*STEP+3}" '
            f'rx="6" fill="none" stroke="{c["accent"]}" stroke-width="2.1" opacity=".9"/>'
        )
    for day in DAYS:
        column = (day - START).days // 7
        row = (day.weekday() + 1) % 7
        x, y = LEFT + column * STEP, TOP + row * STEP
        count = data[day]
        fill = (
            c["future"] if count is None else
            c["empty"] if count == 0 else
            c["levels"][level(count)-1]
        )
        label = "future day" if count is None else f"{count} contributions"
        out.append(
            f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="3" fill="{fill}">'
            f'<title>{day.isoformat()}: {html.escape(label)}</title></rect>'
        )
    for i in reversed(range(6)):
        out.append(
            f'<circle class="tail" cx="0" cy="0" r="{5.3-i*.48:.2f}" '
            f'fill="{c["snake"]}" opacity="{1-i*.115:.2f}" '
            f'style="animation-delay:{i*.10:.2f}s"/>'
        )
    out.append(
        f'<circle class="head" cx="0" cy="0" r="6.7" fill="{c["snake"]}" '
        f'stroke="{c["bg"]}" stroke-width="1.3"/>'
    )
    out.append(f'<text class="info" x="{LEFT}" y="275">TOTAL 2026: {total:,}</text>')
    if peak_month is not None:
        out.append(
            f'<text class="info" x="360" y="275">'
            f'TOP MONTH: {dt.date(2026, peak_month+1, 1):%b} '
            f'({monthly[peak_month]:,})</text>'
        )
    out.extend([
        f'<rect x="{LEFT}" y="297" width="16" height="4" rx="2" fill="{c["accent"]}"/>',
        '<text class="label" x="105" y="306">Gold outline = your busiest activity weeks</text>',
        '<text class="label" x="690" y="306">Future days remain blank</text>',
        '</svg>'
    ])
    return "".join(out)

def main():
    data = fetch_contributions()
    OUT.mkdir(parents=True, exist_ok=True)
    for theme in ("light", "dark"):
        (OUT / f"github-snake-2026-{theme}.svg").write_text(
            svg_for_theme(data, theme), encoding="utf-8"
        )
    print(f"Generated real {YEAR} contributions: {sum(c for c in data.values() if c is not None)}")

if __name__ == "__main__":
    main()
