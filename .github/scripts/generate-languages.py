#!/usr/bin/env python3
"""Generate top languages card SVG using GitHub GraphQL API."""

import os
import sys
import requests
from collections import defaultdict

def get_repository_languages(username, token):
    """Fetch language statistics from all user repositories."""
    headers = {"Authorization": f"Bearer {token}"}
    
    query = """
    query($username: String!, $cursor: String) {
      user(login: $username) {
        repositories(first: 100, after: $cursor, ownerAffiliations: OWNER, orderBy: {field: UPDATED_AT, direction: DESC}) {
          pageInfo {
            hasNextPage
            endCursor
          }
          nodes {
            name
            isFork
            isPrivate
            languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
              edges {
                size
                node {
                  name
                  color
                }
              }
            }
          }
        }
      }
    }
    """
    
    all_languages = defaultdict(int)
    language_colors = {}
    cursor = None
    
    while True:
        response = requests.post(
            "https://api.github.com/graphql",
            json={"query": query, "variables": {"username": username, "cursor": cursor}},
            headers=headers,
            timeout=10
        )
        
        if response.status_code != 200:
            raise Exception(f"GitHub API error: {response.status_code}")
        
        data = response.json()
        if "errors" in data:
            raise Exception(f"GraphQL errors: {data['errors']}")
        
        repos = data["data"]["user"]["repositories"]
        
        for repo in repos["nodes"]:
            # Skip forks
            if repo["isFork"]:
                continue
                
            for edge in repo["languages"]["edges"]:
                lang_name = edge["node"]["name"]
                lang_size = edge["size"]
                lang_color = edge["node"]["color"] or "#858585"
                
                all_languages[lang_name] += lang_size
                if lang_name not in language_colors:
                    language_colors[lang_name] = lang_color
        
        if not repos["pageInfo"]["hasNextPage"]:
            break
        cursor = repos["pageInfo"]["endCursor"]
    
    return all_languages, language_colors

def generate_svg(languages, colors, top_n=8):
    """Generate SVG with top languages statistics."""
    total_size = sum(languages.values())
    sorted_langs = sorted(languages.items(), key=lambda x: x[1], reverse=True)[:top_n]
    
    # Calculate percentages
    lang_stats = []
    for lang, size in sorted_langs:
        percentage = (size / total_size) * 100
        lang_stats.append({
            "name": lang,
            "percentage": percentage,
            "color": colors.get(lang, "#858585")
        })
    
    # SVG dimensions and layout (matching original)
    width = 300
    height = 200
    padding = 20
    spacing = 25
    
    # Start building SVG (matching original structure)
    svg_parts = [
        f"<svg xmlns='http://www.w3.org/2000/svg' width='{width}' height='{height}' viewBox='0 0 {width} {height}'>",
        "    <defs>",
        "        <style>",
        "            .header { fill: #00ffff; font-family: 'Segoe UI', Ubuntu, sans-serif; font-size: 16px; font-weight: 600; }",
        "            .lang-name { fill: #ffffff; font-family: 'Segoe UI', Ubuntu, sans-serif; font-size: 12px; }",
        "            .lang-percent { fill: #888888; font-family: 'Segoe UI', Ubuntu, monospace; font-size: 11px; }",
        "        </style>",
        "    </defs>",
        f"    <rect width='{width}' height='{height}' rx='10' fill='#0a0a0a'/>",
        "    ",
        f"    <text x='20' y='30' class='header'>Top Languages</text>"
    ]
    
    y_offset = 52  # Starting y position for first language
    
    for i, lang in enumerate(lang_stats):
        svg_parts.extend([
            "    <g>",
            f"        <circle cx='25' cy='{y_offset}' r='4' fill='{lang['color']}'/>",
            f"        <text x='35' y='{y_offset + 3}' class='lang-name'>{lang['name']}</text>",
            f"        <text x='280' y='{y_offset + 3}' class='lang-percent' text-anchor='end'>{lang['percentage']:.1f}%</text>",
            "    </g>"
        ])
        
        y_offset += spacing
    
    svg_parts.append("</svg>")
    
    return '\n'.join(svg_parts)

def main():
    """Main function."""
    username = os.getenv("GITHUB_REPOSITORY", "").split("/")[0] or "SaiiPrashanth"
    token = os.getenv("GITHUB_TOKEN")
    
    if not token:
        print("Error: GITHUB_TOKEN environment variable not set", file=sys.stderr)
        sys.exit(1)
    
    try:
        print(f"Fetching repository languages for {username}...")
        languages, colors = get_repository_languages(username, token)
        
        if not languages:
            print("Warning: No language data found", file=sys.stderr)
            sys.exit(1)
        
        print(f"Found {len(languages)} languages across repositories")
        
        print("Generating SVG...")
        svg = generate_svg(languages, colors)
        
        output_path = "assets/top-languages.svg"
        os.makedirs("assets", exist_ok=True)
        
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(svg)
        
        print(f"✓ Top languages card saved to {output_path}")
        
        # Print top 5 for debugging
        sorted_langs = sorted(languages.items(), key=lambda x: x[1], reverse=True)[:5]
        print("\nTop 5 languages:")
        total = sum(languages.values())
        for lang, size in sorted_langs:
            pct = (size / total) * 100
            print(f"  {lang}: {pct:.1f}%")
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
