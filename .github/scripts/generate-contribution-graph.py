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
    query($username: String!) {
      user(login: $username) {
        contributionsCollection {
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
    
    response = requests.post(
        "https://api.github.com/graphql",
        json={"query": query, "variables": {"username": username}},
        headers=headers,
        timeout=10
    )
    
    if response.status_code != 200:
        raise Exception(f"GitHub API error: {response.status_code}")
    
    data = response.json()
    if "errors" in data:
        raise Exception(f"GraphQL errors: {data['errors']}")
    
    return data["data"]["user"]["contributionsCollection"]["contributionCalendar"]

def generate_svg(calendar):
    """Generate contribution graph SVG."""
    # Flatten weeks into days
    days = []
    for week in calendar["weeks"]:
        days.extend(week["contributionDays"])
    
    # Get last 365 days
    days = days[-365:] if len(days) > 365 else days
    
    # Calculate max for color scaling
    max_contributions = max((day["contributionCount"] for day in days), default=1)
    if max_contributions == 0:
        max_contributions = 1
    
    # SVG dimensions
    width = 800
    height = 200
    padding = 40
    graph_width = width - (2 * padding)
    graph_height = height - (2 * padding)
    
    # Calculate point spacing
    point_spacing = graph_width / max(len(days) - 1, 1)
    
    # Generate points for line
    points = []
    max_height = graph_height - 40
    
    for i, day in enumerate(days):
        x = padding + (i * point_spacing)
        # Normalize contribution count to graph height
        normalized = (day["contributionCount"] / max_contributions) * max_height
        y = padding + max_height - normalized + 20
        points.append((x, y, day["contributionCount"]))
    
    # Create path for area fill
    area_path = f"M {padding} {padding + max_height + 20}"
    for x, y, _ in points:
        area_path += f" L {x} {y}"
    area_path += f" L {padding + graph_width} {padding + max_height + 20} Z"
    
    # Create path for line
    line_path = ""
    for i, (x, y, _) in enumerate(points):
        if i == 0:
            line_path = f"M {x} {y}"
        else:
            line_path += f" L {x} {y}"
    
    # Start SVG
    svg = f"""<svg xmlns='http://www.w3.org/2000/svg' width='{width}' height='{height}' viewBox='0 0 {width} {height}'>
    <defs>
        <linearGradient id='gradient' x1='0%' y1='0%' x2='0%' y2='100%'>
            <stop offset='0%' style='stop-color:#ff00ff;stop-opacity:0.3'/>
            <stop offset='100%' style='stop-color:#ff00ff;stop-opacity:0.05'/>
        </linearGradient>
        <style>
            .title {{ fill: #00ffff; font-family: 'Segoe UI', Ubuntu, sans-serif; font-size: 18px; font-weight: 600; }}
            .stat {{ fill: #ffffff; font-family: 'Segoe UI', Ubuntu, sans-serif; font-size: 14px; }}
        </style>
    </defs>
    
    <rect width='{width}' height='{height}' rx='10' fill='#0a0a0a'/>
    
    <text x='20' y='25' class='title'>Contribution Graph</text>
    <text x='{width - 20}' y='25' class='stat' text-anchor='end'>Total: {calendar["totalContributions"]}</text>
    
    <!-- Area fill -->
    <path d='{area_path}' fill='url(#gradient)'/>
    
    <!-- Line -->
    <path d='{line_path}' fill='none' stroke='#ff00ff' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'/>
    
    <!-- Points -->
"""
    
    # Add points
    for x, y, count in points[::7]:  # Show every 7th point to avoid clutter
        if count > 0:
            svg += f"    <circle cx='{x}' cy='{y}' r='3' fill='#ffff00'/>\n"
    
    # Add axis labels
    if len(days) > 0:
        first_date = datetime.strptime(days[0]["date"], "%Y-%m-%d").strftime("%b %d")
        last_date = datetime.strptime(days[-1]["date"], "%Y-%m-%d").strftime("%b %d")
        
        svg += f"""    <text x='{padding}' y='{height - 10}' fill='#888888' font-size='11px' font-family='monospace'>{first_date}</text>
    <text x='{width - padding}' y='{height - 10}' fill='#888888' font-size='11px' font-family='monospace' text-anchor='end'>{last_date}</text>
"""
    
    svg += "</svg>"
    
    return svg

def main():
    """Main function."""
    username = os.getenv("GITHUB_REPOSITORY", "").split("/")[0] or "SaiiPrashanth"
    token = os.getenv("GITHUB_TOKEN")
    
    if not token:
        print("Error: GITHUB_TOKEN environment variable not set", file=sys.stderr)
        sys.exit(1)
    
    try:
        print(f"Fetching contribution data for {username}...")
        calendar = get_contributions(username, token)
        
        print(f"Total contributions: {calendar['totalContributions']}")
        
        print("Generating graph SVG...")
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
