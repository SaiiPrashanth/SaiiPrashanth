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
    """Generate SVG with contribution graph - line chart with grid."""
    weeks = calendar["weeks"]
    total_contributions = calendar["totalContributions"]
    
    # Flatten all days
    all_days = []
    for week in weeks:
        all_days.extend(week["contributionDays"])
    
    # SVG dimensions
    width = 800
    height = 400
    padding_left = 50
    padding_right = 40
    padding_top = 60
    padding_bottom = 40
    
    graph_width = width - padding_left - padding_right
    graph_height = height - padding_top - padding_bottom
    baseline_y = padding_top + graph_height
    
    # Find max contribution for scaling
    max_count = max((day["contributionCount"] for day in all_days), default=1)
    if max_count == 0:
        max_count = 10
    # Round up to next multiple of 5 for nice grid
    y_max = ((max_count // 5) + 1) * 5
    
    # Calculate points for line
    points = []
    for i, day in enumerate(all_days):
        x = padding_left + (i / max(len(all_days) - 1, 1)) * graph_width
        y = baseline_y - (day["contributionCount"] / y_max) * graph_height
        points.append((x, y, day["contributionCount"]))
    
    # Build path for area fill
    area_path = f"M {padding_left} {baseline_y} "
    for x, y, _ in points:
        area_path += f"L {x} {y} "
    area_path += f"L {padding_left + graph_width} {baseline_y} Z"
    
    # Build path for line
    line_path = " ".join(f"L {x} {y}" if i > 0 else f"M {x} {y}" 
                         for i, (x, y, _) in enumerate(points))
    
    # Start building SVG with grid
    svg_parts = [
        f"<svg xmlns='http://www.w3.org/2000/svg' width='{width}' height='{height}' viewBox='0 0 {width} {height}'>",
        "    <defs>",
        "        <linearGradient id='gradient' x1='0%' y1='0%' x2='0%' y2='100%'>",
        "            <stop offset='0%' style='stop-color:#ff00ff;stop-opacity:0.4'/>",
        "            <stop offset='100%' style='stop-color:#ff00ff;stop-opacity:0.05'/>",
        "        </linearGradient>",
        "        <style>",
        "            .title { fill: #00ffff; font-family: 'Segoe UI', Ubuntu, sans-serif; font-size: 18px; font-weight: 600; }",
        "            .axis-label { fill: #00ffff; font-family: 'Segoe UI', Ubuntu, sans-serif; font-size: 12px; }",
        "            .tick-label { fill: #888888; font-family: 'Segoe UI', Ubuntu, monospace; font-size: 10px; }",
        "            .grid-line { stroke: #2a2a2a; stroke-width: 1; }",
        "        </style>",
        "    </defs>",
        f"    <rect width='{width}' height='{height}' rx='10' fill='#0a0a0a'/>",
        "    ",
        f"    <text x='{width/2}' y='30' class='title' text-anchor='middle'>Contribution Graph</text>",
        "    ",
        "    <!-- Grid lines -->"
    ]
    
    # Draw horizontal grid lines and Y-axis labels
    num_y_lines = 8
    for i in range(num_y_lines):
        y = baseline_y - (i / (num_y_lines - 1)) * graph_height
        value = int((i / (num_y_lines - 1)) * y_max)
        svg_parts.append(f"    <line x1='{padding_left}' y1='{y}' x2='{padding_left + graph_width}' y2='{y}' class='grid-line'/>")
        svg_parts.append(f"    <text x='{padding_left - 10}' y='{y + 4}' class='tick-label' text-anchor='end'>{value}</text>")
    
    # Draw vertical grid lines (every ~30 days)
    num_x_lines = 13
    svg_parts.append("    ")
    for i in range(num_x_lines):
        x = padding_left + (i / (num_x_lines - 1)) * graph_width
        svg_parts.append(f"    <line x1='{x}' y1='{padding_top}' x2='{x}' y2='{baseline_y}' class='grid-line'/>")
        # Add day number below
        if i < len(all_days):
            day_index = int((i / (num_x_lines - 1)) * (len(all_days) - 1))
            if day_index < len(all_days):
                date = datetime.strptime(all_days[day_index]["date"], "%Y-%m-%d")
                day_label = date.day
                svg_parts.append(f"    <text x='{x}' y='{baseline_y + 20}' class='tick-label' text-anchor='middle'>{day_label}</text>")
    
    # Y-axis label
    svg_parts.extend([
        "    ",
        f"    <text x='15' y='{(padding_top + baseline_y) / 2}' class='axis-label' text-anchor='middle' transform='rotate(-90, 15, {(padding_top + baseline_y) / 2})'>Contributions</text>",
        "    ",
        "    <!-- X-axis label (Days) -->",
        f"    <text x='{padding_left + graph_width/2}' y='{height - 10}' class='tick-label' text-anchor='middle'>Days</text>",
        "    ",
        "    <!-- Area fill -->",
        f"    <path d='{area_path}' fill='url(#gradient)'/>",
        "    ",
        "    <!-- Line -->",
        f"    <path d='{line_path}' fill='none' stroke='#ff00ff' stroke-width='2.5' stroke-linecap='round' stroke-linejoin='round'/>",
        "    ",
        "    <!-- Data points -->"
    ])
    
    # Add yellow dots at all points with contributions
    for x, y, count in points:
        if count > 0:
            svg_parts.append(f"    <circle cx='{x}' cy='{y}' r='2.5' fill='#ffff00'/>")
    
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
