#!/usr/bin/env python3
"""Actualiza las estadísticas y los lenguajes del README de perfil."""
import json
import os
import re
import urllib.request
from pathlib import Path

LOGIN = "lucioooofacc"
README = Path(__file__).resolve().parents[2] / "README.md"
BAR_WIDTH = 40
MAX_LANGUAGES = 5

QUERY = """
query($login: String!) {
  user(login: $login) {
    followers { totalCount }
    repositories(first: 100, ownerAffiliations: OWNER, privacy: PUBLIC) {
      totalCount
      nodes {
        name
        isFork
        languages(first: 20) { edges { size node { name } } }
      }
    }
    contributionsCollection {
      totalCommitContributions
      totalPullRequestContributions
      contributionCalendar { totalContributions }
    }
  }
}
"""


def fetch():
    request = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": LOGIN}}).encode(),
        headers={
            "Authorization": f"bearer {os.environ['GH_TOKEN']}",
            "Content-Type": "application/json",
            "User-Agent": "profile-readme-updater",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = json.load(response)
    if payload.get("errors"):
        raise RuntimeError(payload["errors"])
    return payload["data"]["user"]


def language_lines(user):
    totals = {}
    for repo in user["repositories"]["nodes"]:
        # El repo del perfil se excluye para no contar este script.
        if repo["isFork"] or repo["name"] == LOGIN:
            continue
        for edge in repo["languages"]["edges"]:
            name = edge["node"]["name"]
            totals[name] = totals.get(name, 0) + edge["size"]
    if not totals:
        raise RuntimeError("GitHub no devolvió lenguajes")
    total = sum(totals.values())
    ranked = sorted(totals.items(), key=lambda item: -item[1])[:MAX_LANGUAGES]
    lines = []
    for name, size in ranked:
        bar = ("#" * round(size / total * BAR_WIDTH)).ljust(BAR_WIDTH, ".")
        lines.append(f'  {name + ":":<12}"{bar}"  # {size / total * 100:.1f}%')
    return lines


def replace_once(pattern, replacement, text):
    text, count = re.subn(pattern, replacement, text, flags=re.M)
    if count != 1:
        raise RuntimeError(f"Se esperaba una coincidencia para: {pattern}")
    return text


def render(text, user):
    work = user["contributionsCollection"]
    repos = user["repositories"]["totalCount"]
    followers = user["followers"]["totalCount"]
    commits = work["totalCommitContributions"]
    prs = work["totalPullRequestContributions"]
    total = work["contributionCalendar"]["totalContributions"]

    for pattern, value in (
        (r"^Repos:\s+\d+", f"Repos:     {repos}"),
        (r"^Followers:\s+\d+", f"Followers: {followers}"),
        (r"^Commits:\s+\d+", f"Commits:   {commits}"),
        (r"^PRs:\s+\d+", f"PRs:       {prs}"),
        (r"^Contribuciones último año:\s+\d+", f"Contribuciones último año: {total}"),
    ):
        text = replace_once(pattern, value, text)
    bars = "\n".join(language_lines(user))
    return replace_once(r"(^# --\[ lenguajes .*\n)(?:  .*\n)+",
                        lambda match: match.group(1) + bars + "\n", text)


def main():
    current = README.read_text(encoding="utf-8")
    updated = render(current, fetch())
    if updated == current:
        print("Sin cambios")
        return
    README.write_text(updated, encoding="utf-8")
    print("README actualizado")


if __name__ == "__main__":
    main()
