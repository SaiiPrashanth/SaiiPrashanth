#!/usr/bin/env python3
"""Generate a self-contained top-languages SVG using the GitHub REST API."""

import os
import sys

import requests


COLORS = ["#00ffff", "#ff00ff", "#ffff00", "#8a2be2", "#39d353", "#58a6ff"]


def get_languages(username, token):
    """Return language byte counts across the user's original repositories."""
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    response = requests.get(
        f"https://api.github.com/users/{username}/repos",
        params={"per_page": 100, "type": "owner", "sort": "updated"},
        headers=headers,
        timeout=20,
    )
    response.raise_for_status()

    totals = {}
    for repository in response.json():
        if repository["fork"]:
            continue
        languages_response = requests.get(
            repository["languages_url"], headers=headers, timeout=20
        )
        languages_response.raise_for_status()
        for language, bytes_count in languages_response.json().items():
            totals[language] = totals.get(language, 0) + bytes_count
    return sorted(totals.items(), key=lambda item: item[1], reverse=True)[:6]


def generate_svg(languages):
    """Render language percentages as a compact dark card."""
    total = sum(value for _, value in languages) or 1
    rows = []
    bar_x = 24
    bar_width = 447
    bar_y = 54
    offset = 0

    for index, (language, value) in enumerate(languages):
        width = max(1, round(bar_width * value / total))
        color = COLORS[index % len(COLORS)]
        rows.append(
            f"<rect x='{bar_x + offset}' y='{bar_y}' width='{width}' height='8' "
            f"fill='{color}'/>"
        )
        offset += width

    labels = []
    for index, (language, value) in enumerate(languages):
        percent = value / total * 100
        x = 24 + (index % 3) * 150
        y = 86 + (index // 3) * 25
        color = COLORS[index % len(COLORS)]
        labels.append(
            f"<circle cx='{x}' cy='{y - 4}' r='4' fill='{color}'/>"
            f"<text x='{x + 10}' y='{y}' fill='#ffffff' font-family='Segoe UI, sans-serif' "
            f"font-size='12'>{language} {percent:.1f}%</text>"
        )

    return (
        "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 495 120' width='495' "
        "height='120'><rect width='100%' height='100%' rx='10' fill='#0a0a0a' "
        "stroke='#30363d'/><text x='24' y='30' fill='#00ffff' font-family='Segoe UI, "
        "sans-serif' font-size='16' font-weight='600'>Top Languages</text>"
        f"{''.join(rows)}{''.join(labels)}</svg>"
    )


def main():
    token = os.getenv("GITHUB_TOKEN")
    username = os.getenv("GITHUB_USERNAME", "SaiiPrashanth")
    if not token:
        print("Error: GITHUB_TOKEN environment variable not set", file=sys.stderr)
        return 1

    try:
        languages = get_languages(username, token)
        if not languages:
            raise ValueError("No language data returned from GitHub")
        with open("assets/top-languages.svg", "w", encoding="utf-8") as output:
            output.write(generate_svg(languages))
        print("Top languages saved to assets/top-languages.svg")
    except (requests.RequestException, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
