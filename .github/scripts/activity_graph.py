"""Render a contribution area graph (last 31 days) as SVG, tokyo-night style."""

import json
import math
import os
import sys
import urllib.request
from datetime import date, timedelta

USER = os.environ["GH_USER"]
TOKEN = os.environ["GH_TOKEN"]
OUT = sys.argv[1]
DAYS = 31

QUERY = """
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) {
      contributionCalendar {
        weeks { contributionDays { date contributionCount } }
      }
    }
  }
}
"""

end = date.today()
start = end - timedelta(days=DAYS - 1)
payload = json.dumps({
    "query": QUERY,
    "variables": {
        "login": USER,
        "from": f"{start.isoformat()}T00:00:00Z",
        "to": f"{end.isoformat()}T23:59:59Z",
    },
}).encode()
req = urllib.request.Request(
    "https://api.github.com/graphql",
    data=payload,
    headers={"Authorization": f"bearer {TOKEN}", "Content-Type": "application/json"},
)
with urllib.request.urlopen(req) as resp:
    data = json.load(resp)
if "errors" in data:
    sys.exit(f"GraphQL error: {data['errors']}")

weeks = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
by_date = {d["date"]: d["contributionCount"] for w in weeks for d in w["contributionDays"]}
days = [start + timedelta(days=i) for i in range(DAYS)]
counts = [by_date.get(d.isoformat(), 0) for d in days]

# Layout
W, H = 1000, 340
LEFT, RIGHT, TOP, BOTTOM = 60, 30, 70, 50
PW, PH = W - LEFT - RIGHT, H - TOP - BOTTOM
BG, TITLE, LINE, POINT, GRID, TEXT = "#0D1117", "#70a5fd", "#bf91f3", "#38bdae", "#1f2335", "#a9b1d6"

step = max(1, math.ceil(max(counts) / 4))
y_max = step * 4


def x(i):
    return LEFT + i * PW / (DAYS - 1)


def y(v):
    return TOP + PH - v * PH / y_max


pts = [(x(i), y(c)) for i, c in enumerate(counts)]
line = "M " + " L ".join(f"{px:.1f} {py:.1f}" for px, py in pts)
area = f"{line} L {pts[-1][0]:.1f} {TOP + PH} L {pts[0][0]:.1f} {TOP + PH} Z"

parts = [
    f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
    f'font-family="-apple-system, BlinkMacSystemFont, Segoe UI, Helvetica, Arial, sans-serif">',
    "<defs>",
    '<linearGradient id="fill" x1="0" y1="0" x2="0" y2="1">',
    f'<stop offset="0%" stop-color="{LINE}" stop-opacity="0.45"/>',
    f'<stop offset="100%" stop-color="{LINE}" stop-opacity="0.02"/>',
    "</linearGradient>",
    "</defs>",
    f'<rect width="{W}" height="{H}" rx="6" fill="{BG}"/>',
    f'<text x="{W / 2}" y="38" text-anchor="middle" font-size="20" font-weight="600" fill="{TITLE}">'
    f"{USER}'s contribution graph</text>",
]

for k in range(5):
    v = k * step
    gy = y(v)
    parts.append(f'<line x1="{LEFT}" y1="{gy:.1f}" x2="{W - RIGHT}" y2="{gy:.1f}" stroke="{GRID}" stroke-width="1"/>')
    parts.append(f'<text x="{LEFT - 10}" y="{gy + 4:.1f}" text-anchor="end" font-size="12" fill="{TEXT}">{v}</text>')

for i, d in enumerate(days):
    parts.append(f'<text x="{x(i):.1f}" y="{TOP + PH + 22}" text-anchor="middle" font-size="11" fill="{TEXT}">{d.day}</text>')

parts.append(f'<text x="{W / 2}" y="{H - 6}" text-anchor="middle" font-size="12" fill="{TEXT}">Days</text>')
parts.append(f'<text x="18" y="{TOP + PH / 2}" text-anchor="middle" font-size="12" fill="{TEXT}" '
             f'transform="rotate(-90 18 {TOP + PH / 2})">Contributions</text>')
parts.append(f'<path d="{area}" fill="url(#fill)"/>')
parts.append(f'<path d="{line}" fill="none" stroke="{LINE}" stroke-width="2.5" stroke-linejoin="round"/>')
for (px, py), c, d in zip(pts, counts, days):
    parts.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="4" fill="{POINT}"><title>{d.isoformat()}: {c}</title></circle>')
parts.append("</svg>")

os.makedirs(os.path.dirname(OUT) or ".", exist_ok=True)
with open(OUT, "w") as f:
    f.write("\n".join(parts))
