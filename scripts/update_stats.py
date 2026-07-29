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

query = """
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    createdAt
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
      totalCommitContributions
      totalIssueContributions
      totalPullRequestContributions
      totalRepositoriesWithContributedCommits
    }
  }
}
"""

def graphql(document, variables):
    payload = json.dumps({"query": document, "variables": variables}).encode()
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
    return result["data"]


result = {
    "data": graphql(
        query,
        {
            "login": USERNAME,
            "from": datetime(now.year, 1, 1, tzinfo=timezone.utc).isoformat(),
            "to": now.isoformat(),
        },
    )
}

user = result["data"]["user"]
repos = user["repositories"]
stars = sum(
    repo["stargazerCount"]
    for repo in repos["nodes"]
    if not repo["isFork"]
)
lifetime_query = """
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) {
      totalCommitContributions
      totalIssueContributions
      totalPullRequestContributions
      commitContributionsByRepository(maxRepositories: 100) {
        repository { nameWithOwner }
      }
    }
  }
}
"""
created_at = datetime.fromisoformat(user["createdAt"].replace("Z", "+00:00"))
commits = 0
pull_requests = 0
issues = 0
contributed_repositories = set()
for year in range(created_at.year, now.year + 1):
    period_start = max(created_at, datetime(year, 1, 1, tzinfo=timezone.utc))
    period_end = min(
        now,
        datetime(year + 1, 1, 1, tzinfo=timezone.utc) - timedelta(seconds=1),
    )
    annual = graphql(
        lifetime_query,
        {
            "login": USERNAME,
            "from": period_start.isoformat(),
            "to": period_end.isoformat(),
        },
    )["user"]["contributionsCollection"]
    commits += annual["totalCommitContributions"]
    pull_requests += annual["totalPullRequestContributions"]
    issues += annual["totalIssueContributions"]
    contributed_repositories.update(
        contribution["repository"]["nameWithOwner"]
        for contribution in annual["commitContributionsByRepository"]
    )
contributed_to = len(contributed_repositories)
activity_score = commits + pull_requests * 8 + issues * 5 + stars * 4
if activity_score >= 1000:
    rank, rank_progress = "S", 0.96
elif activity_score >= 500:
    rank, rank_progress = "A+", 0.88
elif activity_score >= 250:
    rank, rank_progress = "A", 0.78
elif activity_score >= 100:
    rank, rank_progress = "B+", 0.68
elif activity_score >= 50:
    rank, rank_progress = "B", 0.58
elif activity_score >= 20:
    rank, rank_progress = "C+", 0.48
else:
    rank, rank_progress = "C", 0.36

rank_dash = 276.46 * rank_progress

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
  <rect x="5" y="5" width="490" height="210" rx="18" fill="#F7FBFE" stroke="#CFE6F1" filter="url(#shadow)"/>
  <path d="M23 5H156V215H23Q5 215 5 197V23Q5 5 23 5Z" fill="#E3F5FB"/>
  <circle cx="34" cy="187" r="18" fill="#FFE9F2" opacity=".8"/>
  <circle cx="139" cy="27" r="13" fill="#FFF0C6" opacity=".9"/>
  <g font-family="Segoe UI, Arial, sans-serif">
    <text x="28" y="41" fill="#328BAD" font-size="20" font-weight="700">GitHub</text>
    <text x="28" y="63" fill="#526071" font-size="13">at a glance</text>
    <circle cx="81" cy="126" r="43" fill="#FFFEFA" stroke="#BDE8F6" stroke-width="8"/>
    <circle cx="81" cy="126" r="43" fill="none" stroke="#65CFF0" stroke-width="8" stroke-linecap="round"
      stroke-dasharray="{rank_dash:.2f} 276.46" transform="rotate(-90 81 126)"/>
    <text x="81" y="134" text-anchor="middle" fill="#273142" font-size="25" font-weight="700">{rank}</text>
    <text x="81" y="181" text-anchor="middle" fill="#7B8796" font-size="9" letter-spacing="1">ACTIVITY</text>

    <g>
      <rect x="176" y="26" width="137" height="70" rx="12" fill="#FFFEFA" stroke="#E5EDF3"/>
      <text x="190" y="50" fill="#7B8796" font-size="11">Total Stars</text><text x="190" y="79" fill="#273142" font-size="23" font-weight="700">{stars:,}</text>
      <circle cx="294" cy="43" r="5" fill="#FFE171"/>

      <rect x="326" y="26" width="148" height="70" rx="12" fill="#FFFEFA" stroke="#E5EDF3"/>
      <text x="340" y="50" fill="#7B8796" font-size="11">Total Commits</text><text x="340" y="79" fill="#273142" font-size="23" font-weight="700">{commits:,}</text>
      <circle cx="455" cy="43" r="5" fill="#65CFF0"/>

      <rect x="176" y="108" width="88" height="70" rx="12" fill="#FFFEFA" stroke="#E5EDF3"/>
      <text x="188" y="132" fill="#7B8796" font-size="10">PRs</text><text x="188" y="161" fill="#273142" font-size="22" font-weight="700">{pull_requests:,}</text>

      <rect x="274" y="108" width="88" height="70" rx="12" fill="#FFFEFA" stroke="#E5EDF3"/>
      <text x="286" y="132" fill="#7B8796" font-size="10">Issues</text><text x="286" y="161" fill="#273142" font-size="22" font-weight="700">{issues:,}</text>

      <rect x="372" y="108" width="102" height="70" rx="12" fill="#FFFEFA" stroke="#E5EDF3"/>
      <text x="384" y="132" fill="#7B8796" font-size="10">Contributed</text><text x="384" y="161" fill="#273142" font-size="22" font-weight="700">{contributed_to:,}</text>
    </g>
    <text x="176" y="203" fill="#A0A9B5" font-size="9">Updated daily from GitHub API</text>
  </g>
</svg>
"""

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
OUTPUT.write_text(svg, encoding="utf-8")

if total_language_bytes:
    circumference = 339.29
    dash_offset = 0.0
    ring_parts = []
    legend_parts = []
    for index, (name, size) in enumerate(languages):
        ratio = size / total_language_bytes
        color = language_colors[name]
        dash = circumference * ratio
        ring_parts.append(
            f'<circle cx="125" cy="124" r="54" fill="none" stroke="{color}" '
            f'stroke-width="18" stroke-dasharray="{dash:.2f} {circumference - dash:.2f}" '
            f'stroke-dashoffset="{-dash_offset:.2f}" transform="rotate(-90 125 124)"/>'
        )
        dash_offset += dash
        x = 258
        y = 74 + index * 22
        percentage = ratio * 100
        legend_parts.append(
            f'<circle cx="{x + 6}" cy="{y - 4}" r="6" fill="{color}"/>'
            f'<text x="{x + 20}" y="{y}" fill="#526071" font-size="12">'
            f'{escape(name)} {percentage:.1f}%</text>'
        )
    ring_content = "".join(ring_parts)
    legend_content = "".join(legend_parts)
else:
    ring_content = (
        '<circle cx="125" cy="124" r="54" fill="none" '
        'stroke="#DCE5EE" stroke-width="18"/>'
    )
    legend_content = (
        '<text x="258" y="112" fill="#7B8796" font-size="14">'
        "No public repository languages to show yet.</text>"
    )

language_svg = f"""<svg width="500" height="220" viewBox="0 0 500 220" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <filter id="shadow"><feDropShadow dx="0" dy="3" stdDeviation="4" flood-color="#64748B" flood-opacity=".10"/></filter>
  </defs>
  <rect x="5" y="5" width="490" height="210" rx="28" fill="#FFF9F2" stroke="#F2DFC8" filter="url(#shadow)"/>
  <path d="M230 5V215" stroke="#F2DFC8" stroke-dasharray="4 6"/>
  <g font-family="Segoe UI, Arial, sans-serif">
    <text x="258" y="42" fill="#D27B47" font-size="21" font-weight="700">Language Mix</text>
    <text x="258" y="59" fill="#9A806F" font-size="10" letter-spacing="1">PUBLIC · NON-FORK REPOSITORIES</text>
    <circle cx="125" cy="124" r="54" fill="none" stroke="#F2E9DF" stroke-width="18"/>
    <g>{ring_content}</g>
    <circle cx="125" cy="124" r="35" fill="#FFFEFA"/>
    <text x="125" y="119" text-anchor="middle" fill="#273142" font-size="19" font-weight="700">{len(languages)}</text>
    <text x="125" y="137" text-anchor="middle" fill="#9A806F" font-size="9" letter-spacing="1">LANGUAGES</text>
    <g>{legend_content}</g>
    <path d="M75 42q18-18 36 0q18 18 36 0" fill="none" stroke="#FF9DC3" stroke-width="3" stroke-linecap="round"/>
    <circle cx="185" cy="48" r="7" fill="#FFE171"/>
    <text x="258" y="205" fill="#A08C7E" font-size="9">Calculated by repository language bytes</text>
  </g>
</svg>
"""

LANGUAGE_OUTPUT.write_text(language_svg, encoding="utf-8")
print(
    f"Updated {OUTPUT} and {LANGUAGE_OUTPUT}: stars={stars}, "
    f"commits={commits}, prs={pull_requests}, issues={issues}, "
    f"contributed_to={contributed_to}, rank={rank}, languages={len(languages)}"
)
