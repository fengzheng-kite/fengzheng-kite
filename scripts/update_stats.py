import json
import os
import urllib.request
from datetime import datetime, timedelta, timezone
from html import escape
from pathlib import Path


USERNAME = "fengzheng-kite"
OUTPUT = Path("assets/github-stats.svg")
LANGUAGE_OUTPUT = Path("assets/github-languages.svg")
TOKEN = os.environ["GITHUB_TOKEN"]

now = datetime.now(timezone.utc)
start = now - timedelta(days=365)

query = """
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    followers { totalCount }
    repositories(
      first: 100
      ownerAffiliations: OWNER
      privacy: PUBLIC
      orderBy: {field: UPDATED_AT, direction: DESC}
    ) {
      totalCount
      nodes {
        isFork
        stargazerCount
        languages(first: 20, orderBy: {field: SIZE, direction: DESC}) {
          edges {
            size
            node { name color }
          }
        }
      }
    }
    contributionsCollection(from: $from, to: $to) {
      contributionCalendar { totalContributions }
    }
  }
}
"""

payload = json.dumps(
    {
        "query": query,
        "variables": {
            "login": USERNAME,
            "from": start.isoformat(),
            "to": now.isoformat(),
        },
    }
).encode()

request = urllib.request.Request(
    "https://api.github.com/graphql",
    data=payload,
    headers={
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json",
        "User-Agent": "profile-stats-generator",
    },
)

with urllib.request.urlopen(request) as response:
    result = json.load(response)

if "errors" in result:
    raise RuntimeError(result["errors"])

user = result["data"]["user"]
repos = user["repositories"]
stars = sum(
    repo["stargazerCount"]
    for repo in repos["nodes"]
    if not repo["isFork"]
)
contributions = user["contributionsCollection"]["contributionCalendar"][
    "totalContributions"
]
public_repos = repos["totalCount"]
followers = user["followers"]["totalCount"]

language_bytes = {}
language_colors = {}
for repo in repos["nodes"]:
    if repo["isFork"]:
        continue
    for edge in repo["languages"]["edges"]:
        name = edge["node"]["name"]
        language_bytes[name] = language_bytes.get(name, 0) + edge["size"]
        language_colors[name] = edge["node"]["color"] or "#65CFF0"

languages = sorted(language_bytes.items(), key=lambda item: item[1], reverse=True)[:6]
total_language_bytes = sum(language_bytes.values())

svg = f"""<svg width="500" height="220" viewBox="0 0 500 220" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <filter id="shadow"><feDropShadow dx="0" dy="3" stdDeviation="4" flood-color="#64748B" flood-opacity=".10"/></filter>
  </defs>
  <rect x="5" y="5" width="490" height="210" rx="14" fill="#FFFEFA" stroke="#DCE5EE" filter="url(#shadow)"/>
  <g font-family="Segoe UI, Arial, sans-serif">
    <text x="28" y="40" fill="#D45D8C" font-size="22" font-weight="700">Shenrui Liu's GitHub Stats</text>
    <path d="M28 52H472" stroke="#E7EDF2"/>

    <text x="28" y="82" fill="#7B8796" font-size="12">Total stars earned</text>
    <text x="28" y="111" fill="#344155" font-size="25" font-weight="700">{stars:,}</text>

    <text x="270" y="82" fill="#7B8796" font-size="12">Contributions (365 days)</text>
    <text x="270" y="111" fill="#344155" font-size="25" font-weight="700">{contributions:,}</text>

    <text x="28" y="143" fill="#7B8796" font-size="12">Public repositories</text>
    <text x="28" y="172" fill="#344155" font-size="25" font-weight="700">{public_repos:,}</text>

    <text x="270" y="143" fill="#7B8796" font-size="12">Followers</text>
    <text x="270" y="172" fill="#344155" font-size="25" font-weight="700">{followers:,}</text>

    <circle cx="455" cy="190" r="5" fill="#FFB84D"/>
    <path d="M28 194H440" stroke="#65CFF0" stroke-width="3" stroke-linecap="round"/>
    <text x="28" y="209" fill="#A0A9B5" font-size="9">Updated daily from GitHub API</text>
  </g>
</svg>
"""

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
OUTPUT.write_text(svg, encoding="utf-8")

if total_language_bytes:
    bar_x = 28.0
    bar_width = 444.0
    bar_parts = []
    legend_parts = []
    for index, (name, size) in enumerate(languages):
        ratio = size / total_language_bytes
        width = bar_width * ratio
        color = language_colors[name]
        bar_parts.append(
            f'<rect x="{bar_x:.2f}" y="91" width="{width:.2f}" height="14" '
            f'fill="{color}"/>'
        )
        bar_x += width

        column = index % 2
        row = index // 2
        x = 28 + column * 242
        y = 132 + row * 25
        percentage = ratio * 100
        legend_parts.append(
            f'<circle cx="{x + 6}" cy="{y - 4}" r="6" fill="{color}"/>'
            f'<text x="{x + 20}" y="{y}" fill="#526071" font-size="12">'
            f'{escape(name)} {percentage:.1f}%</text>'
        )
    bar_content = "".join(bar_parts)
    legend_content = "".join(legend_parts)
else:
    bar_content = ""
    legend_content = (
        '<text x="28" y="112" fill="#7B8796" font-size="14">'
        "No public repository languages to show yet.</text>"
    )

language_svg = f"""<svg width="500" height="220" viewBox="0 0 500 220" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <filter id="shadow"><feDropShadow dx="0" dy="3" stdDeviation="4" flood-color="#64748B" flood-opacity=".10"/></filter>
    <clipPath id="bar"><rect x="28" y="91" width="444" height="14" rx="7"/></clipPath>
  </defs>
  <rect x="5" y="5" width="490" height="210" rx="14" fill="#FFFEFA" stroke="#DCE5EE" filter="url(#shadow)"/>
  <g font-family="Segoe UI, Arial, sans-serif">
    <text x="28" y="40" fill="#328BAD" font-size="22" font-weight="700">Most Used Languages</text>
    <path d="M28 52H472" stroke="#E7EDF2"/>
    <g clip-path="url(#bar)">{bar_content}</g>
    <g>{legend_content}</g>
    <circle cx="455" cy="190" r="5" fill="#FFB84D"/>
    <path d="M28 194H440" stroke="#65CFF0" stroke-width="3" stroke-linecap="round"/>
    <text x="28" y="209" fill="#A0A9B5" font-size="9">Calculated by byte count across public, non-fork repositories</text>
  </g>
</svg>
"""

LANGUAGE_OUTPUT.write_text(language_svg, encoding="utf-8")
print(
    f"Updated {OUTPUT} and {LANGUAGE_OUTPUT}: stars={stars}, "
    f"contributions={contributions}, repos={public_repos}, "
    f"followers={followers}, languages={len(languages)}"
)
