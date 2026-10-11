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
    if n <= 0: return "#17171C"
    if n <= 2: return "#5C2115"
    if n <= 5: return "#99331D"
    if n <= 9: return "#E0592A"
    return "#FF9E45"


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
    loc = escape(CFG["location"].upper())
    logo = logo_data_uri()
    logo_img = (f'<image href="{logo}" x="46" y="92" width="96" height="96" '
                f'clip-path="url(#logoClip)" preserveAspectRatio="xMidYMid slice"/>'
                f'<circle cx="94" cy="140" r="52" fill="none" stroke="url(#ember)" stroke-width="1.6" opacity="0.85"/>'
                f'<path d="M 94 82 A 58 58 0 0 1 145 111" fill="none" stroke="{EMBER_B}" stroke-width="2.4" stroke-linecap="round">'
                f'<animateTransform attributeName="transform" type="rotate" from="0 94 140" to="360 94 140" dur="14s" repeatCount="indefinite"/></path>') if logo else ""
    pills, x = [], 46
    for sk in CFG["skills"]:
        w = 30 + len(sk) * 8.4
        pills.append(
            f'<g><rect x="{x:.0f}" y="330" width="{w:.0f}" height="36" rx="18" fill="#101014" stroke="{LINE}"/>'
            f'<text x="{x + w / 2:.0f}" y="353" font-size="14.5" fill="{SUB}" text-anchor="middle">{escape(sk)}</text></g>')
        x += w + 12
    stats = [("TOTAL STARS", stars), ("PUBLIC REPOS", profile.get("public_repos", 0)),
             ("CONTRIBUTIONS · LAST YEAR", total_contrib)]
    stat_svg, sx = [], 46
    for i, (label, val) in enumerate(stats):
        begin = i * 160
        stat_svg.append(
            f'<g><animateTransform attributeName="transform" type="translate" from="0 12" to="0 0" begin="{begin}ms" dur="450ms" fill="freeze"/>'
            f'<text x="{sx}" y="272" font-size="31" font-weight="700" fill="url(#ember)">{val}</text>'
            f'<text x="{sx}" y="296" font-size="10.5" letter-spacing="2.2" fill="{DIM}">{label}</text></g>')
        sx += 218
    eq = []
    for i, (h1, h2, dur) in enumerate([(10, 22, "1.1s"), (18, 30, "0.9s"), (8, 18, "1.3s"), (14, 26, "1.0s"), (6, 14, "1.2s")]):
        bx = 896 + i * 13
        eq.append(f'<rect x="{bx}" y="{352 - h1}" width="6" height="{h1}" rx="2" fill="{EMBER_A}" opacity="0.75">'
                  f'<animate attributeName="height" values="{h1};{h2};{h1}" dur="{dur}" repeatCount="indefinite"/>'
                  f'<animate attributeName="y" values="{352 - h1};{352 - h2};{352 - h1}" dur="{dur}" repeatCount="indefinite"/></rect>')
    # Typewriter for the focus line (monospace => uniform char width).
    focus_raw = CFG["focus"]
    cw = 8.75
    total_w = len(focus_raw) * cw
    steps = len(focus_raw)
    vals = ";".join(f"{(i * cw):.1f}" for i in range(steps + 1))
    keys = ";".join(f"{i / steps:.4f}" for i in range(steps + 1))
    caret_x = 168 + total_w + 5
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="400" viewBox="0 0 {W} 400" font-family="'Segoe UI','Helvetica Neue',Arial,sans-serif">
<defs>
<linearGradient id="ember" x1="0" y1="0" x2="1" y2="0">
<stop offset="0" stop-color="{EMBER_A}"/><stop offset="1" stop-color="{EMBER_B}"/>
</linearGradient>
<radialGradient id="glow" cx="0.5" cy="0.5" r="0.5">
<stop offset="0" stop-color="{EMBER_A}" stop-opacity="0.34"/><stop offset="1" stop-color="{EMBER_A}" stop-opacity="0"/>
</radialGradient>
<linearGradient id="trail" x1="0" y1="0" x2="1" y2="0">
<stop offset="0" stop-color="{EMBER_A}" stop-opacity="0"/><stop offset="1" stop-color="{EMBER_A}" stop-opacity="0.10"/>
</linearGradient>
<clipPath id="cardClip"><rect x="1" y="1" width="998" height="398" rx="23"/></clipPath>
<clipPath id="logoClip"><circle cx="94" cy="140" r="48"/></clipPath>
<clipPath id="typeClip"><rect x="166" y="182" width="0" height="30">
<animate attributeName="width" calcMode="discrete" values="{vals}" keyTimes="{keys}" dur="2300ms" begin="500ms" fill="freeze"/>
</rect></clipPath>
</defs>
<g clip-path="url(#cardClip)">
<rect width="{W}" height="400" fill="#08080A"/>
<ellipse cx="830" cy="46" rx="300" ry="190" fill="url(#glow)">
<animate attributeName="cx" values="805;858;805" dur="13s" repeatCount="indefinite"/>
<animate attributeName="opacity" values="0.75;1;0.75" dur="9s" repeatCount="indefinite"/>
</ellipse>
<g opacity="0.55">
<rect x="-130" y="0" width="130" height="400" fill="url(#trail)">
<animateTransform attributeName="transform" type="translate" from="0 0" to="1260 0" dur="12s" repeatCount="indefinite"/>
</rect>
<rect x="-1.5" y="0" width="1.6" height="400" fill="{EMBER_B}" opacity="0.30">
<animateTransform attributeName="transform" type="translate" from="0 0" to="1010 0" dur="12s" repeatCount="indefinite"/>
</rect>
</g>
<rect x="1" y="1" width="998" height="398" rx="23" fill="none" stroke="url(#ember)" stroke-opacity="0.38" stroke-width="1.4"/>
<circle cx="54" cy="46" r="5" fill="{EMBER_A}">
<animate attributeName="opacity" values="1;0.2;1" dur="1.7s" repeatCount="indefinite"/>
</circle>
<text x="70" y="51" font-size="12.5" letter-spacing="3.2" fill="{MUT}">IRDCODE · {loc}</text>
{logo_img}
<text x="168" y="138" font-size="46" font-weight="700" fill="{INK}">{name}</text>
<text x="168" y="174" font-size="19.5" fill="{SUB}">{role}</text>
<g clip-path="url(#typeClip)">
<text x="168" y="204" font-size="14.5" fill="{MUT}" font-family="ui-monospace,'SF Mono',Consolas,monospace">{focus}</text>
</g>
<rect x="{caret_x:.0f}" y="189" width="8" height="17" fill="{EMBER_B}" opacity="0">
<animate attributeName="opacity" values="0;0" begin="0ms" dur="2700ms" fill="freeze"/>
<animate attributeName="opacity" values="1;0;1" begin="2750ms" dur="1050ms" repeatCount="indefinite"/>
</rect>
<line x1="46" y1="232" x2="954" y2="232" stroke="{LINE}" stroke-width="1"/>
{''.join(stat_svg)}
<line x1="46" y1="316" x2="954" y2="316" stroke="{LINE}" stroke-width="1"/>
{''.join(pills)}
{''.join(eq)}
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
        cards.append(f'''<g>
<rect x="{cx}" y="{cy}" width="452" height="120" rx="14" fill="{CARD}" stroke="{LINE}"/>
<text x="{cx + 20}" y="{cy + 36}" font-size="17.5" font-weight="600" fill="{INK}">{escape(r['name'])}</text>
<text x="{cx + 20}" y="{cy + 63}" font-size="12.8" fill="{MUT}">{escape(desc)}</text>
{lang_svg}
<polygon points="0,-5.2 1.55,-2.1 5,-1.6 2.5,0.85 3.1,4.2 0,2.2 -3.1,4.2 -2.5,0.85 -5,-1.6 -1.55,-2.1" transform="translate({cx + 396},{cy + 94})" fill="{EMBER_B}"/>
<text x="{cx + 428}" y="{cy + 99}" font-size="13.5" fill="{EMBER_B}" text-anchor="end">{r.get('stargazers_count', 0)}</text>
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
            begin = int(c * 22 + row * 9)
            cells_svg.append(
                f'<rect x="{gx + c * pitch:.1f}" y="{gy + row * pitch:.1f}" width="{cell}" height="{cell}" rx="2.6" '
                f'fill="{level_color(n)}"><animate attributeName="fill" from="#17171C" to="{level_color(n)}" '
                f'begin="{begin}ms" dur="300ms" fill="freeze"/></rect>')
            if row == 0 and d.month not in seen_months and d.day <= 7:
                seen_months.add(d.month)
                month_labels.append(
                    f'<text x="{gx + c * pitch:.1f}" y="{gy - 10}" font-size="10" fill="{DIM}">{d.strftime("%b")}</text>')
    grid_h = 7 * pitch
    H = int(gy + grid_h + 58)
    legend = []
    for i, col in enumerate(["#17171C", "#5C2115", "#99331D", "#E0592A", "#FF9E45"]):
        legend.append(f'<rect x="{46 + i * 20}" y="{H - 34}" width="13" height="13" rx="3" fill="{col}"/>')
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="'Segoe UI','Helvetica Neue',Arial,sans-serif">
<defs>
<linearGradient id="ember2" x1="0" y1="0" x2="1" y2="0">
<stop offset="0" stop-color="{EMBER_A}"/><stop offset="1" stop-color="{EMBER_B}"/>
</linearGradient>
</defs>
<rect x="1" y="1" width="998" height="{H - 2}" rx="23" fill="#08080A" stroke="url(#ember2)" stroke-opacity="0.30" stroke-width="1.4"/>
<text x="46" y="44" font-size="14" letter-spacing="3.4" fill="{INK}">SELECTED WORK</text>
<rect x="46" y="56" width="0" height="2.4" fill="url(#ember2)">
<animate attributeName="width" from="0" to="172" dur="1100ms" fill="freeze"/>
</rect>
{''.join(cards)}
<text x="46" y="392" font-size="14" letter-spacing="3.4" fill="{INK}">LAST YEAR ON GITHUB</text>
<text x="954" y="392" font-size="13" fill="{MUT}" text-anchor="end">{total} contributions</text>
{''.join(month_labels)}
{''.join(cells_svg)}
<text x="46" y="{H - 40}" font-size="10.5" fill="{DIM}">LESS</text>
{''.join(legend)}
<text x="{46 + 5 * 20 + 8}" y="{H - 40}" font-size="10.5" fill="{DIM}">MORE</text>
<text x="954" y="{H - 24}" font-size="11" fill="#4B4B54" text-anchor="end">github.com/{USER} · art regenerates daily</text>
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
