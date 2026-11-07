#!/usr/bin/env python3
"""Generate the profile greeting using Typograssy's pixel-grid effect."""

from html import escape
from pathlib import Path


GLYPHS = {
    " ": "//", "!": "/012346/", ",": "6/5/", ".": "/6/",
    "H": "0123456/3/0123456", "N": "0123456/0/123456",
    "S": "125/036/145", "a": "25/246/3456", "e": "345/246/346",
    "h": "0123456/2/3456", "i": "/023456/", "l": "0/0123456/",
    "m": "23456/2345/3456", "n": "23456/2/3456", "o": "345/26/345",
    "r": "23456/3/2", "s": "36/246/25", "t": "2/123456/26",
    "u": "23456/6/23456", "y": "236/46/2345",
}

TEXT = "Hello! i am Sai, Nice to meet ya . "
COLORS = ("#00ffff", "#ff00ff", "#ffff00", "#8a2be2")
WEEKS = 53
DAYS = 7
CELL = 10
SPAN = 3
STEP = CELL + SPAN
WIDTH = STEP * (WEEKS + 2) - SPAN
HEIGHT = STEP * (DAYS + 3) - SPAN


def pixel_positions(text):
    positions = []
    for character in text:
        encoded = GLYPHS.get(character, "/3/")
        positions.extend(
            [int(row) for row in line]
            for line in encoded.split("/") if line
        )
        positions.append([])
    return positions


def rect(x, y, level):
    return (
        f"<rect class='pixel l{level}' x='{x * STEP}' y='{y * STEP}' "
        f"width='{CELL}' height='{CELL}' rx='2' ry='2'/>"
    )


def generate():
    positions = pixel_positions(TEXT)
    steps = len(positions)
    offset = 1 if steps > WEEKS else (WEEKS - steps + 1) // 2
    pixels = []
    for x, line in enumerate(positions):
        for y in line:
            level = x % len(COLORS) + 1
            pixels.append(rect(x + offset, y, level))
            if steps > WEEKS and x < WEEKS - offset:
                pixels.append(rect(x + offset + steps, y, level))

    base = "".join(rect(index // DAYS, index % DAYS, 0) for index in range(WEEKS * DAYS))
    scroll = ""
    if steps > WEEKS:
        scroll = (
            f"#typograssy #text-pixels{{animation:step {80 * steps}ms steps({steps}) infinite;}}"
            f"@keyframes step{{to{{transform:translateX(-{steps * STEP}px);}}}}"
        )

    style = (
        f"#typograssy .pixel{{stroke:rgba(27,31,35,.06);stroke-width:2px;}}"
        f"#typograssy .l0{{fill:none;}}"
        + "".join(f"#typograssy .l{index + 1}{{fill:{color};}}" for index, color in enumerate(COLORS))
        + scroll
    )
    return f"""<svg xmlns='http://www.w3.org/2000/svg' width='{WIDTH}' height='{HEIGHT}' id='typograssy'>
<style>{style}</style>
<rect width='{WIDTH}' height='{HEIGHT}' fill='none'/>
<svg x='{STEP}' y='{STEP}' width='{WIDTH - STEP * 2}' height='{HEIGHT - STEP * 2}'>
<g>{base}</g><g id='text-pixels'>{''.join(pixels)}</g>
</svg>
</svg>
"""


if __name__ == "__main__":
    Path("assets/typograssy-pixel.svg").write_text(generate(), encoding="utf-8")
