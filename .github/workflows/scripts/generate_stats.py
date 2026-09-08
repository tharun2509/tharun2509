#!/usr/bin/env python3
import json, os, urllib.request
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOKEN = os.environ["GITHUB_TOKEN"]
USER = os.environ.get("GITHUB_USERNAME", "tharun2509")

QUERY = (
    "query($login:String!, $from:DateTime!, $to:DateTime!) {"
    " user(login:$login) {"
    " followers { totalCount }"
    " repositories(ownerAffiliations:OWNER, first:100, privacy:PUBLIC) {"
    " totalCount nodes { stargazerCount languages(first:10, orderBy:{field:SIZE, direction:DESC}) { edges { size node { name } } } }"
    " }"
    " contributionsCollection(from:$from, to:$to) { contributionCalendar { weeks { contributionDays { date contributionCount } } } }"
    " }"
    "}"
)

def gql(variables):
    body = json.dumps({"query": QUERY, "variables": variables}).encode()
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=body,
        headers={
            "Authorization": f"bearer {TOKEN}",
            "Content-Type": "application/json",
            "User-Agent": "tharun2509-profile",
        },
        method="POST",
    )
    with urllib.request.urlopen(req) as response:
        payload = json.load(response)
    if payload.get("errors"):
        raise RuntimeError(payload["errors"])
    return payload["data"]["user"]

def esc(value):
    return str(value).replace("&","&amp;").replace("<","&lt;").replace(">","&gt;").replace('"',"&quot;")

def write_svg(name, body, width=900, height=180):
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}">'
        '<rect width="100%" height="100%" fill="#ffffff"/>'
        '<style>.t{font-family:"JetBrains Mono","Courier New",monospace;fill:#111}'
        '.m{font-family:"JetBrains Mono","Courier New",monospace;fill:#777}</style>'
        + body +
        '</svg>'
    )
    (ROOT / name).write_text(svg, encoding="utf-8")

today = date.today()
start = date(today.year, 1, 1)
user = gql({
    "login": USER,
    "from": f"{start.isoformat()}T00:00:00Z",
    "to": f"{today.isoformat()}T23:59:59Z",
})

repos = user["repositories"]["nodes"]
repo_count = user["repositories"]["totalCount"]
followers = user["followers"]["totalCount"]
stars = sum(repo["stargazerCount"] for repo in repos)

languages = {}
for repo in repos:
    for edge in repo["languages"]["edges"]:
        name = edge["node"]["name"]
        languages[name] = languages.get(name, 0) + edge["size"]

days = []
for week in user["contributionsCollection"]["contributionCalendar"]["weeks"]:
    days.extend(week["contributionDays"])
days.sort(key=lambda item: item["date"])

current = 0
longest = 0
run = 0
for day in days:
    if day["contributionCount"] > 0:
        run += 1
        longest = max(longest, run)
    else:
        run = 0

for day in reversed(days):
    if day["contributionCount"] > 0:
        current += 1
    else:
        break

write_svg(
    "stats.svg",
    f'<g class="t">'
    f'<text x="30" y="34" font-size="13">PUBLIC REPOSITORIES</text>'
    f'<text x="30" y="76" font-size="32" font-weight="700">{repo_count}</text>'
    f'<text x="310" y="34" font-size="13">FOLLOWERS</text>'
    f'<text x="310" y="76" font-size="32" font-weight="700">{followers}</text>'
    f'<text x="560" y="34" font-size="13">STARS</text>'
    f'<text x="560" y="76" font-size="32" font-weight="700">{stars}</text>'
    f'<text x="30" y="125" class="m" font-size="11">Generated from GitHub GraphQL · {today.isoformat()}</text>'
    f'</g>',
    900, 150
)

top = sorted(languages.items(), key=lambda item: item[1], reverse=True)[:6]
total = sum(languages.values()) or 1
x = 30
bars = []
for name, size in top:
    bar = 840 * size / total
    bars.append(f'<rect x="{x:.1f}" y="78" width="{max(bar,2):.1f}" height="18" fill="#111"/>')
    x += bar
labels = " · ".join(f"{name} {size/total*100:.0f}%" for name, size in top)

write_svg(
    "langs.svg",
    f'<g class="t">'
    f'<text x="30" y="32" font-size="13">LANGUAGE MIX</text>'
    f'<text x="30" y="58" class="m" font-size="10">Public repositories · size-weighted totals</text>'
    + "".join(bars)
    + f'<text x="30" y="132" font-size="11">{esc(labels)}</text>'
    + '</g>',
    900, 160
)

write_svg(
    "streak.svg",
    f'<g class="t">'
    f'<text x="30" y="34" font-size="13">CONTRIBUTION STREAK</text>'
    f'<text x="30" y="82" font-size="28" font-weight="700">{current} days current · {longest} days longest</text>'
    f'<text x="30" y="112" class="m" font-size="10">Current year contribution calendar</text>'
    f'</g>',
    900, 135
)

weeks = user["contributionsCollection"]["contributionCalendar"]["weeks"]
palette = ["#f3f3f3", "#d8d8d8", "#a8a8a8", "#666666", "#111111"]
cells = []
for wi, week in enumerate(weeks):
    for di, day in enumerate(week["contributionDays"]):
        count = day["contributionCount"]
        level = 0 if count == 0 else 1 if count < 2 else 2 if count < 5 else 3 if count < 10 else 4
        x = 30 + wi * 13
        y = 72 + di * 13
        cells.append(
            f'<rect x="{x}" y="{y}" width="10" height="10" rx="1" fill="{palette[level]}">'
            f'<title>{esc(day["date"])}: {count}</title></rect>'
        )

write_svg(
    "year.svg",
    f'<g class="t"><text x="30" y="28" font-size="13">YEAR IN CODE · {today.year}</text>'
    + "".join(cells)
    + '</g>',
    900, 170
)
