#!/usr/bin/env python3
"""Generate contribution graph SVG using GitHub GraphQL API."""

import os
import sys
from datetime import datetime, timedelta
import requests

def get_contributions(username, token):
    """Fetch contribution data from GitHub GraphQL API."""
    headers = {"Authorization": f"Bearer {token}"}
    
    query = """
    query($username: String!, $from: DateTime!, $to: DateTime!) {
      user(login: $username) {
        contributionsCollection(from: $from, to: $to) {
          contributionCalendar {
            totalContributions
            weeks {
              contributionDays {
                contributionCount
                date
              }
            }
          }
        }
      }
    }
    """
    
    # Get last year of data
    to_date = datetime.now()
    from_date = to_date - timedelta(days=365)
    
    response = requests.post(
        "https://api.github.com/graphql",
        json={
            "query": query,
            "variables": {
                "username": username,
                "from": from_date.isoformat(),
                "to": to_date.isoformat()
            }
        },
        headers=headers,
        timeout=10
    )
    
    if response.status_code != 200:
        raise Exception(f"GitHub API error: {response.status_code}")
    
    data = response.json()
    if "errors" in data:
        raise Exception(f"GraphQL errors: {data['errors']}")
    
    return data["data"]["user"]["contributionsCollection"]["contributionCalendar"]

def get_color_for_count(count, max_count):
    """Get color based on contribution count."""
    if count == 0:
        return "#2a2a2a"
    
    # Color scale from cyan to magenta based on intensity
    intensity = min(count / max(max_count, 1), 1.0)
    
    if intensity < 0.25:
        return "#1a4d4d"  # Dark cyan
    elif intensity < 0.5:
        return "#00ffff"  # Cyan
    elif intensity < 0.75:
        return "#8a2be2"  # Blue violet
    else:
        return "#ff00ff"  # Magenta

def generate_svg(calendar):
    """Generate SVG with contribution graph (line chart style)."""
    weeks = calendar["weeks"]
    total_contributions = calendar["totalContributions"]
    
    # Flatten all days
    all_days = []
    for week in weeks:
        all_days.extend(week["contributionDays"])
    
    # SVG dimensions (matching original)
    width = 800
    height = 200
    padding_left = 40
    padding_right = 40
    padding_top = 50
    padding_bottom = 50
    
    graph_width = width - padding_left - padding_right
    graph_height = height - padding_top - padding_bottom
    baseline_y = padding_top + graph_height
    
    # Find max contribution for scaling
    max_count = max((day["contributionCount"] for day in all_days), default=1)
    if max_count == 0:
        max_count = 1
    
    # Calculate points for line
    points = []
    for i, day in enumerate(all_days):
        x = padding_left + (i / len(all_days)) * graph_width
        # Scale y: 0 contributions = baseline, max = top
        y = baseline_y - (day["contributionCount"] / max_count) * graph_height
        points.append((x, y))
    
    # Build path for area fill
    area_path = f"M {padding_left} {baseline_y} "
    for x, y in points:
        area_path += f"L {x} {y} "
    area_path += f"L {padding_left + graph_width} {baseline_y} Z"
    
    # Build path for line
    line_path = " ".join(f"L {x} {y}" if i > 0 else f"M {x} {y}" 
                         for i, (x, y) in enumerate(points))
    
    # Find peak points for highlighting
    peak_threshold = max_count * 0.7
    peaks = [(x, y, all_days[i]) for i, (x, y) in enumerate(points) 
             if all_days[i]["contributionCount"] >= peak_threshold and all_days[i]["contributionCount"] > 0]
    
    # Get first and last dates
    first_date = datetime.strptime(all_days[0]["date"], "%Y-%m-%d").strftime("%b %d")
    last_date = datetime.strptime(all_days[-1]["date"], "%Y-%m-%d").strftime("%b %d")
    
    # Start building SVG (matching original structure)
    svg_parts = [
        f"<svg xmlns='http://www.w3.org/2000/svg' width='{width}' height='{height}' viewBox='0 0 {width} {height}'>",
        "    <defs>",
        "        <linearGradient id='gradient' x1='0%' y1='0%' x2='0%' y2='100%'>",
        "            <stop offset='0%' style='stop-color:#ff00ff;stop-opacity:0.3'/>",
        "            <stop offset='100%' style='stop-color:#ff00ff;stop-opacity:0.05'/>",
        "        </linearGradient>",
        "        <style>",
        "            .title { fill: #00ffff; font-family: 'Segoe UI', Ubuntu, sans-serif; font-size: 18px; font-weight: 600; }",
        "            .stat { fill: #ffffff; font-family: 'Segoe UI', Ubuntu, sans-serif; font-size: 14px; }",
        "        </style>",
        "    </defs>",
        "    ",
        f"    <rect width='{width}' height='{height}' rx='10' fill='#0a0a0a'/>",
        "    ",
        f"    <text x='20' y='25' class='title'>Contribution Graph</text>",
        f"    <text x='780' y='25' class='stat' text-anchor='end'>Total: {total_contributions}</text>",
        "    ",
        "    <!-- Area fill -->",
        f"    <path d='{area_path}' fill='url(#gradient)'/>",
        "    ",
        "    <!-- Line -->",
        f"    <path d='{line_path}' fill='none' stroke='#ff00ff' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'/>",
        "    "
    ]
    
    # Add peak points
    if peaks:
        svg_parts.append("    <!-- Points -->")
        for x, y, day in peaks[:4]:  # Show up to 4 peaks
            svg_parts.append(f"    <circle cx='{x}' cy='{y}' r='3' fill='#ffff00'/>")
    
    # Add date labels
    svg_parts.extend([
        f"    <text x='40' y='190' fill='#888888' font-size='11px' font-family='monospace'>{first_date}</text>",
        f"    <text x='760' y='190' fill='#888888' font-size='11px' font-family='monospace' text-anchor='end'>{last_date}</text>",
        "</svg>"
    ])
    
    return '\n'.join(svg_parts)

def main():
    """Main function."""
    username = os.getenv("GITHUB_REPOSITORY", "").split("/")[0] or "SaiiPrashanth"
    token = os.getenv("GITHUB_TOKEN")
    
    if not token:
        print("Error: GITHUB_TOKEN environment variable not set", file=sys.stderr)
        sys.exit(1)
    
    try:
        print(f"Fetching contributions for {username}...")
        calendar = get_contributions(username, token)
        
        print(f"Total contributions: {calendar['totalContributions']}")
        
        print("Generating SVG...")
        svg = generate_svg(calendar)
        
        output_path = "assets/contribution-graph.svg"
        os.makedirs("assets", exist_ok=True)
        
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(svg)
        
        print(f"✓ Contribution graph saved to {output_path}")
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
