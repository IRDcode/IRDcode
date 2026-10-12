#!/usr/bin/env python3
"""IRDcode profile art generator (custom build, stdlib only).

Fetches public GitHub data (profile, repos, contribution calendar) and
renders two animated SVGs:
  assets/hero.svg   - identity header: logo, name, role, stats, skills
  assets/works.svg  - featured repositories + last-year contribution heatmap

Animations are SMIL (works when GitHub serves the SVG as an image):
pulsing record dot, drifting glow, a slow timeline "playhead" sweep,
an equalizer motif, and a staggered heatmap fade-in.
No tokens, no third-party services, no external assets (logo is embedded).
"""

import base64
import json
import math
import re
import sys
import urllib.request
from datetime import date, timedelta
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parent.parent
CFG = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
USER = CFG["username"]

W = 1000
INK = "#F5F4F2"
SUB = "#C7C7CD"
MUT = "#8B8B94"
DIM = "#62626B"
CARD = "#0D0D10"
LINE = "#202027"
EMBER_A = "#FF4A2D"
EMBER_B = "#FFB03A"

LANG_COLORS = {
    "Python": "#3572A5", "PowerShell": "#5391FE", "TypeScript": "#3178C6",
    "JavaScript": "#F1E05A", "HTML": "#E34C26", "CSS": "#663399",
}


def fetch(url, accept="application/json"):
    req = urllib.request.Request(url, headers={
        "User-Agent": f"{USER}-profile-art",
        "Accept": accept,
    })
    with urllib.request.urlopen(req, timeout=30) as r:
        body = r.read().decode("utf-8", "replace")
    return json.loads(body) if accept == "application/json" else body


def demo_data():
    repos = [
        {"name": n, "description": d, "stargazers_count": s, "language": l}
        for n, d, s, l in [
            ("claude-code-session-handoff", "Session handoff tooling for Claude Code CLI", 2, "Python"),
            ("hyperos-keyboard-gap-fix", "Fix the HyperOS keyboard gap on Xiaomi devices", 3, "PowerShell"),
            ("hermes-agent-session-handoff", "Session handoff for Hermes agent workflows", 2, "Python"),
            ("event-timer-distribution", "Event countdown timer - distribution build", 0, None),
        ]
    ]
    today = date.today()
    days = {}
    for i in range(364, -1, -1):
        d = today - timedelta(days=i)
        days[d] = (i * 7) % 9 if (i % 3) else 0
    return {"public_repos": 4, "followers": 3}, repos, 7, days


def live_data():
    profile = fetch(f"https://api.github.com/users/{USER}")
    repos = fetch(f"https://api.github.com/users/{USER}/repos?per_page=100&type=owner")
    stars = sum(r.get("stargazers_count", 0) for r in repos if not r.get("fork"))
    html = fetch(f"https://github.com/users/{USER}/contributions", accept="text/html")
    cells = dict(re.findall(r'data-date="(\d{4}-\d{2}-\d{2})" id="(contribution-day-component-[\d-]+)"', html))
    tips = dict(re.findall(r'for="(contribution-day-component-[\d-]+)"[^>]*>([^<]+)<', html))
    days = {}
    for ds, cid in cells.items():
        txt = tips.get(cid, "")
        m = re.match(r"(\d+) contribution", txt)
        days[date.fromisoformat(ds)] = int(m.group(1)) if m else 0
    return profile, repos, stars, days


def level_color(n):
    if n <= 0: return "#141414"
    if n <= 2: return "#2C2C2C"
    if n <= 5: return "#565656"
    if n <= 9: return "#969696"
    return "#F2F2F2"


def logo_data_uri():
    p = ROOT / "assets" / "logo.jpg"
    raw = None
    if p.exists():
        raw = p.read_bytes()
    else:
        try:
            req = urllib.request.Request(f"https://github.com/{USER}.png?size=460",
                                         headers={"User-Agent": f"{USER}-profile-art"})
            with urllib.request.urlopen(req, timeout=20) as r:
                raw = r.read()
        except Exception:
            raw = None
    if not raw:
        return ""
    return "data:image/jpeg;base64," + base64.b64encode(raw).decode()


def hero_svg(profile, stars, total_contrib):
    name = escape(CFG["name"])
    role = escape(CFG["role"])
    focus = escape(CFG["focus"])
    logo = logo_data_uri()
    logo_img = (f'<image href="{logo}" x="46" y="92" width="96" height="96" '
                f'clip-path="url(#logoClip)" preserveAspectRatio="xMidYMid slice"/>'
                f'<circle cx="94" cy="140" r="52" fill="none" stroke="#D8D8D8" stroke-width="1.2"/>'
                f'<circle cx="94" cy="140" r="59" fill="none" stroke="#5C5C5C" stroke-width="5" stroke-dasharray="1.4 6.34" opacity="0.8">'
                f'<animateTransform attributeName="transform" type="rotate" from="0 94 140" to="360 94 140" dur="46s" repeatCount="indefinite"/></circle>') if logo else ""
    stats = [("TOTAL STARS", stars), ("PUBLIC REPOS", profile.get("public_repos", 0)),
             ("CONTRIBUTIONS · LAST YEAR", total_contrib)]
    stat_svg, sx = [], 46
    for label, val in stats:
        stat_svg.append(
            f'<text class="statnum" x="{sx}" y="272" font-size="30" font-weight="700" fill="#F5F5F5">{val}</text>'
            f'<text class="statlab" x="{sx}" y="296" font-size="10.5" letter-spacing="2.2" fill="#666666">{label}</text>')
        sx += 218
    skills_line = " / ".join(sk.upper() for sk in CFG["skills"])
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="400" viewBox="0 0 {W} 400" font-family="'Segoe UI','Helvetica Neue',Arial,sans-serif">
<defs>
<linearGradient id="sweep" x1="0" y1="0" x2="1" y2="0">
<stop offset="0" stop-color="#FFFFFF" stop-opacity="0"/>
<stop offset="0.5" stop-color="#FFFFFF" stop-opacity="0.055"/>
<stop offset="1" stop-color="#FFFFFF" stop-opacity="0"/>
</linearGradient>
<clipPath id="cardClip"><rect x="1" y="1" width="998" height="398" rx="23"/></clipPath>
<clipPath id="logoClip"><circle cx="94" cy="140" r="48"/></clipPath>
<style>
@media (max-width: 640px) {{
  .coords {{ display: none; }}
  .pname {{ font-size: 64px; }}
  .prole {{ font-size: 27px; }}
  .pfocus {{ font-size: 20px; }}
  .statnum {{ font-size: 42px; }}
  .statlab {{ font-size: 15px; }}
  .skills {{ font-size: 16.5px; letter-spacing: 1.4px; }}
}}
</style>
<pattern id="grain" width="3" height="3" patternUnits="userSpaceOnUse">
<circle cx="0.7" cy="0.7" r="0.55" fill="#FFFFFF" opacity="0.05"/>
<circle cx="2.2" cy="2.4" r="0.45" fill="#FFFFFF" opacity="0.035"/>
</pattern>
</defs>
<g clip-path="url(#cardClip)">
<rect width="{W}" height="400" fill="#050505"/>
<rect x="46" y="1.5" width="908" height="1" fill="#FFFFFF" opacity="0.10"/>
<g>
<rect x="-320" y="-60" width="300" height="520" fill="url(#sweep)" transform="rotate(8)">
</rect>
<animateTransform attributeName="transform" type="translate" values="0 0;1420 0;1420 0" keyTimes="0;0.16;1" dur="17s" repeatCount="indefinite"/>
</g>
<rect x="1" y="1" width="998" height="398" rx="23" fill="none" stroke="#1B1B1B" stroke-width="1.2"/>
<path d="M 26 44 V 30 Q 26 26 30 26 H 44" fill="none" stroke="#5A5A5A" stroke-width="1.6"/>
<path d="M 956 26 H 970 Q 974 26 974 30 V 44" fill="none" stroke="#5A5A5A" stroke-width="1.6"/>
<path d="M 974 356 V 370 Q 974 374 970 374 H 956" fill="none" stroke="#5A5A5A" stroke-width="1.6"/>
<path d="M 44 374 H 30 Q 26 374 26 370 V 356" fill="none" stroke="#5A5A5A" stroke-width="1.6"/>
<text x="46" y="51" font-size="12.5" letter-spacing="3.4" fill="#8A8A8A">IRDCODE</text>
<text class="coords" x="954" y="51" font-size="12" letter-spacing="2.6" fill="#555555" text-anchor="end">TEHRAN · 35.69°N 51.39°E</text>
{logo_img}
<text class="pname" x="170" y="144" font-size="55" font-weight="700" letter-spacing="-0.5" fill="#F5F5F5" font-family="Georgia,'Times New Roman',serif">{name}</text>
<text class="prole" x="170" y="180" font-size="18.5" letter-spacing="0.4" fill="#B4B4B4">{role}</text>
<text class="pfocus" x="170" y="208" font-size="13.5" fill="#7E7E7E">{focus}</text>
<line x1="46" y1="232" x2="954" y2="232" stroke="#1E1E1E" stroke-width="1"/>
{''.join(stat_svg)}
<line x1="46" y1="316" x2="954" y2="316" stroke="#1E1E1E" stroke-width="1"/>
<text class="skills" x="46" y="354" font-size="12.5" letter-spacing="2.2" fill="#9A9A9A">{escape(skills_line)}</text>
<rect width="{W}" height="400" fill="url(#grain)"/>
</g>
</svg>'''


def works_svg(repos_by_name, days):
    featured = []
    for name in CFG["featured_repos"]:
        r = repos_by_name.get(name)
        if r:
            featured.append(r)
    featured = featured[:4]
    cards = []
    for i, r in enumerate(featured):
        cx = 46 + (i % 2) * 470
        cy = 74 + (i // 2) * 136
        desc = (r.get("description") or "").strip()
        if any(ord(ch) > 127 for ch in desc):
            tail = desc.split("—")[-1].strip()
            if sum(ch.isascii() and ch.isalpha() for ch in tail) >= 10:
                desc = tail
        if len(desc) > 58:
            desc = desc[:57].rstrip() + "…"
        lang = r.get("language") or ""
        dot = LANG_COLORS.get(lang, "#8B8B94")
        lang_svg = (f'<circle cx="{cx + 24}" cy="{cy + 94}" r="5" fill="{dot}"/>'
                    f'<text x="{cx + 38}" y="{cy + 99}" font-size="12.5" fill="{MUT}">{escape(lang)}</text>') if lang else ""
        dly = 0.12 + i * 0.12
        tot = dly + 0.5
        kt = f"{dly / tot:.3f}"
        cards.append(f'''<g>
<animate attributeName="opacity" values="0;0;1" keyTimes="0;{kt};1" dur="{tot:.2f}s" fill="freeze"/>
<animateTransform attributeName="transform" type="translate" values="0 12;0 12;0 0" keyTimes="0;{kt};1" dur="{tot:.2f}s" fill="freeze"/>
<rect x="{cx}" y="{cy}" width="452" height="120" rx="14" fill="url(#cardGrad)" stroke="{LINE}"/>
<text class="cardname" x="{cx + 20}" y="{cy + 36}" font-size="17.5" font-weight="600" fill="{INK}">{escape(r['name'])}</text>
<text class="desc" x="{cx + 20}" y="{cy + 63}" font-size="12.8" fill="{MUT}">{escape(desc)}</text>
<g class="meta">{lang_svg}</g>
<g class="meta"><polygon points="0,-5.2 1.55,-2.1 5,-1.6 2.5,0.85 3.1,4.2 0,2.2 -3.1,4.2 -2.5,0.85 -5,-1.6 -1.55,-2.1" transform="translate({cx + 396},{cy + 94})" fill="#E8E8E8"/>
<text x="{cx + 428}" y="{cy + 99}" font-size="13.5" fill="#B4B4B4" text-anchor="end">{r.get('stargazers_count', 0)}</text></g>
</g>''')
    # heatmap: columns = weeks (Sun..Sat rows), from the earliest date in data
    total = sum(days.values())
    if days:
        first = min(days)
        first -= timedelta(days=(first.weekday() + 1) % 7)  # back to Sunday
        last = max(days)
        cols = ((last - first).days // 7) + 1
    else:
        first, cols = date.today(), 0
    gx, gy, cell, gap = 46, 428, 12.6, 3.6
    pitch = cell + gap
    cells_svg, month_labels = [], []
    seen_months = set()
    for c in range(cols):
        for row in range(7):
            d = first + timedelta(days=c * 7 + row)
            if d > date.today():
                continue
            n = days.get(d, 0)
            begin = int(620 + c * 26 + row * 10)
            cells_svg.append(
                f'<rect x="{gx + c * pitch:.1f}" y="{gy + row * pitch:.1f}" width="{cell}" height="{cell}" rx="2.6" '
                f'fill="{level_color(n)}"><animate attributeName="fill" from="#141414" to="{level_color(n)}" '
                f'begin="{begin}ms" dur="300ms" fill="freeze"/></rect>')
            if row == 0 and d.month not in seen_months and d.day <= 7:
                seen_months.add(d.month)
                month_labels.append(
                    f'<text class="mon" x="{gx + c * pitch:.1f}" y="{gy - 10}" font-size="10" fill="{DIM}">{d.strftime("%b")}</text>')
    grid_h = 7 * pitch
    H = int(gy + grid_h + 58)
    legend = []
    for i, col in enumerate(["#141414", "#2C2C2C", "#565656", "#969696", "#F2F2F2"]):
        legend.append(f'<rect x="{46 + i * 20}" y="{H - 34}" width="13" height="13" rx="3" fill="{col}"/>')
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="'Segoe UI','Helvetica Neue',Arial,sans-serif">
<defs>
<linearGradient id="ember2" x1="0" y1="0" x2="1" y2="0">
<stop offset="0" stop-color="#3A3A3A"/><stop offset="1" stop-color="#E8E8E8"/>
</linearGradient>
<linearGradient id="cardGrad" x1="0" y1="0" x2="0" y2="1">
<stop offset="0" stop-color="#0C0C0C"/><stop offset="1" stop-color="#060606"/>
</linearGradient>
<style>
@media (max-width: 640px) {{
  .desc {{ display: none; }}
  .meta {{ transform: translateY(-25px); }}
  .cardname {{ font-size: 21px; }}
  .whead {{ font-size: 17px; }}
  .mon {{ font-size: 13px; }}
}}
</style>
</defs>
<rect x="1" y="1" width="998" height="{H - 2}" rx="23" fill="#050505" stroke="#262626" stroke-width="1.2"/>
<path d="M 42 24 H 25 V 41" fill="none" stroke="#3D3D3D" stroke-width="2"/>
<path d="M 958 24 H 975 V 41" fill="none" stroke="#3D3D3D" stroke-width="2"/>
<g>
<animate attributeName="opacity" values="0;1" dur="0.45s" fill="freeze"/>
<animateTransform attributeName="transform" type="translate" values="-8 0;0 0" dur="0.45s" fill="freeze"/>
<text class="whead" x="46" y="44" font-size="14" letter-spacing="3.4" fill="{INK}">SELECTED WORK</text>
<rect x="46" y="56" width="0" height="2.4" fill="url(#ember2)">
<animate attributeName="width" from="0" to="172" dur="1100ms" fill="freeze"/>
</rect>
</g>
{''.join(cards)}
<g>
<animate attributeName="opacity" values="0;0;1" keyTimes="0;0.45;1" dur="1.2s" fill="freeze"/>
<text class="whead" x="46" y="392" font-size="14" letter-spacing="3.4" fill="{INK}">LAST YEAR ON GITHUB</text>
<text x="954" y="392" font-size="13" fill="{MUT}" text-anchor="end">{total} contributions</text>
</g>
<g><animate attributeName="opacity" values="0;0;1" keyTimes="0;0.3;1" dur="1.5s" fill="freeze"/>{''.join(month_labels)}</g>
{''.join(cells_svg)}
<g>
<animate attributeName="opacity" values="0;0;1" keyTimes="0;0.78;1" dur="2.7s" fill="freeze"/>
<text x="46" y="{H - 40}" font-size="10.5" fill="{DIM}">LESS</text>
{''.join(legend)}
<text x="{46 + 5 * 20 + 8}" y="{H - 40}" font-size="10.5" fill="{DIM}">MORE</text>
<text x="954" y="{H - 24}" font-size="11" fill="#4B4B54" text-anchor="end">github.com/{USER} · art regenerates daily</text>
</g>
</svg>'''


def main():
    if "--demo" in sys.argv:
        profile, repos, stars, days = demo_data()
    else:
        profile, repos, stars, days = live_data()
    by_name = {r["name"]: r for r in repos}
    total = sum(days.values())
    (ROOT / "assets" / "hero.svg").write_text(hero_svg(profile, stars, total), encoding="utf-8")
    (ROOT / "assets" / "works.svg").write_text(works_svg(by_name, days), encoding="utf-8")
    print(f"Generated profile art for @{USER}: stars={stars} contributions={total}")


if __name__ == "__main__":
    main()
