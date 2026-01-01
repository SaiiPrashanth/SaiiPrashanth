#!/usr/bin/env python3
"""Generate top languages card SVG using GitHub GraphQL API."""

import os
import sys
import requests
from collections import defaultdict

def get_languages(username, token):
    """Fetch language data from GitHub GraphQL API."""
    headers = {"Authorization": f"Bearer {token}"}
    
    query = """
    query($username: String!, $cursor: String) {
      user(login: $username) {
        repositories(first: 100, after: $cursor, ownerAffiliations: OWNER, isFork: false, orderBy: {field: UPDATED_AT, direction: DESC}) {
          pageInfo {
            hasNextPage
            endCursor
          }
          nodes {
            name
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
            for edge in repo["languages"]["edges"]:
                lang_name = edge["node"]["name"]
                lang_color = edge["node"]["color"] or "#858585"
                size = edge["size"]
                
                all_languages[lang_name] += size
                if lang_name not in language_colors:
                    language_colors[lang_name] = lang_color
        
        if not repos["pageInfo"]["hasNextPage"]:
            break
        cursor = repos["pageInfo"]["endCursor"]
    
    return all_languages, language_colors

def generate_svg(languages, colors, max_languages=8):
    """Generate compact languages SVG."""
    # Sort by size and get top languages
    sorted_langs = sorted(languages.items(), key=lambda x: x[1], reverse=True)[:max_languages]
    total_bytes = sum(languages.values())
    
    if total_bytes == 0:
        total_bytes = 1  # Avoid division by zero
    
    # Calculate percentages
    lang_data = []
    for lang, bytes_count in sorted_langs:
        percentage = (bytes_count / total_bytes) * 100
        lang_data.append({
            "name": lang,
            "percentage": percentage,
            "color": colors.get(lang, "#858585")
        })
    
    # SVG dimensions
    width = 300
    height = 200
    padding = 20
    bar_height = 8
    item_height = 25
    
    # Start SVG
    svg_parts = [f"""<svg xmlns='http://www.w3.org/2000/svg' width='{width}' height='{height}' viewBox='0 0 {width} {height}'>
    <defs>
        <style>
            .header {{ fill: #00ffff; font-family: 'Segoe UI', Ubuntu, sans-serif; font-size: 16px; font-weight: 600; }}
            .lang-name {{ fill: #ffffff; font-family: 'Segoe UI', Ubuntu, sans-serif; font-size: 12px; }}
            .lang-percent {{ fill: #888888; font-family: 'Segoe UI', Ubuntu, monospace; font-size: 11px; }}
        </style>
    </defs>
    <rect width='{width}' height='{height}' rx='10' fill='#0a0a0a'/>
    
    <text x='{padding}' y='30' class='header'>Top Languages</text>
"""]
    
    y_offset = 55
    
    for lang in lang_data:
        # Language name and percentage
        svg_parts.append(f"""    <g>
        <circle cx='{padding + 5}' cy='{y_offset - 3}' r='4' fill='{lang["color"]}'/>
        <text x='{padding + 15}' y='{y_offset}' class='lang-name'>{lang["name"]}</text>
        <text x='{width - padding}' y='{y_offset}' class='lang-percent' text-anchor='end'>{lang["percentage"]:.1f}%</text>
    </g>
""")
        y_offset += item_height
    
    svg_parts.append("</svg>")
    
    return "".join(svg_parts)

def main():
    """Main function."""
    username = os.getenv("GITHUB_REPOSITORY", "").split("/")[0] or "SaiiPrashanth"
    token = os.getenv("GITHUB_TOKEN")
    
    if not token:
        print("Error: GITHUB_TOKEN environment variable not set", file=sys.stderr)
        sys.exit(1)
    
    try:
        print(f"Fetching language data for {username}...")
        languages, colors = get_languages(username, token)
        
        if not languages:
            print("No language data found")
            sys.exit(1)
        
        print(f"Found {len(languages)} languages across repositories")
        
        print("Generating SVG...")
        svg = generate_svg(languages, colors)
        
        output_path = "assets/top-languages.svg"
        os.makedirs("assets", exist_ok=True)
        
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(svg)
        
        print(f"✓ Top languages saved to {output_path}")
        
        # Print top 5 for verification
        top_5 = sorted(languages.items(), key=lambda x: x[1], reverse=True)[:5]
        total = sum(languages.values())
        print("\nTop 5 languages:")
        for lang, bytes_count in top_5:
            pct = (bytes_count / total) * 100
            print(f"  {lang}: {pct:.1f}%")
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
