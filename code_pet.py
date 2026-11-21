"""Render assets/code-pet.svg (profile + pet) and assets/code-stats.svg (stats + languages).

Usage: GH_TOKEN=... python code_pet.py <login>
       python code_pet.py --fixture data.json   (offline render for testing)
"""
import base64, datetime as dt, html, json, os, sys, urllib.request

QUERY = """query($login:String!){user(login:$login){
  name login bio avatarUrl(size:160) createdAt followers{totalCount}
  repositories(ownerAffiliations:OWNER, privacy:PUBLIC, isFork:false, first:100){
    totalCount nodes{stargazerCount languages(first:10){edges{size node{name color}}}}}
  contributionsCollection{contributionCalendar{totalContributions
    weeks{contributionDays{contributionCount date}}}}}}"""

BG, CARD, LINE = "#0d0605", "#140806", "#4a1a0e"
INK, MUTED, TEAL, AMBER = "#fff4e6", "#e0b49a", "#ff7a1a", "#ffd23f"
LEVELS = ["#2a120c", "#7a1d0a", "#d62a1e", "#ff7a1a", "#ffd23f"]
# background gradient stops: black -> red -> orange -> yellow
GRADIENT = [("0", "#0d0605"), (".45", "#5a0e08"), (".75", "#d9480f"), ("1", "#ffb020")]

# Original pixel fire fox with swag specs.
# b=fur d=outline c=cream r=red g=yellow flame s=specs w=lens shine n=nose
ADULT = ["..d......d......", ".dbd....dbd...g.", ".drbd..dbrd..gg.", ".drbbddbbrd.grg.",
         "dbbbbbbbbbbd.grg", "sssssssssssss.gr", "dswsssbswsssd.rb", "dsssssbsssssd.rb",
         "dbbbbbbbbbbbd.bb", "dccbbbnnbbbccdbb", ".dccccccccccd.db", "..dccccccccd.dbd",
         "...ddbbbbdd.dbd.", "...dbccccbddbd..", "...dbccccbbbd...", "...ddddddddd...."]
BABY = ["............", "..d....d....", ".dbd..dbd...", ".drbddbrd.g.",
        "dbbbbbbbbdgg", "ssssssssss.r", "dswsbbswsd.b", "dbbbbbbbbd.b",
        "dccbnnbccddb", ".dccccccd.d.", "..dbbbbd....", "..dddddd...."]
EGG = ["............", "............", ".....dd.....", "....dbbd....",
       "...dbgbbd...", "...dbbbbd...", "..dbbbbgbd..", "..dgbbbbbd..",
       "..dbbbbbbd..", "...dbbbbd...", "....dddd....", "............"]


def fetch(login):
    req = urllib.request.Request("https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": login}}).encode(),
        headers={"Authorization": f"bearer {os.environ['GH_TOKEN']}"})
    data = json.load(urllib.request.urlopen(req))
    if "errors" in data:
        sys.exit(f"GitHub API error: {data['errors']}")
    user = data["data"]["user"]
    with urllib.request.urlopen(user["avatarUrl"]) as r:
        user["avatar_b64"] = base64.b64encode(r.read()).decode()
    return user


def stats(user, today):
    weeks = user["contributionsCollection"]["contributionCalendar"]["weeks"]
    days = [d for w in weeks for d in w["contributionDays"] if d["date"] <= today.isoformat()]
    counts = [d["contributionCount"] for d in days]
    streak, i = 0, len(counts) - 1
    if counts and counts[-1] == 0:
        i -= 1  # today not done yet doesn't break the streak
    while i >= 0 and counts[i] > 0:
        streak, i = streak + 1, i - 1
    recent = weeks[-13:]
    active_13 = sum(any(d["contributionCount"] for d in w["contributionDays"]) for w in recent)
    active_52 = sum(any(d["contributionCount"] for d in w["contributionDays"]) for w in weeks[-52:])
    total_13 = sum(d["contributionCount"] for w in recent for d in w["contributionDays"])
    langs = {}
    for repo in user["repositories"]["nodes"]:
        for e in repo["languages"]["edges"]:
            n = e["node"]["name"]
            langs.setdefault(n, [0, e["node"]["color"] or MUTED])[0] += e["size"]
    top = sorted(langs.items(), key=lambda kv: -kv[1][0])[:5]
    lang_total = sum(v[0] for _, v in top) or 1
    return {
        "grid": recent, "streak": streak, "active_13": active_13,
        "year_total": user["contributionsCollection"]["contributionCalendar"]["totalContributions"],
        "asleep": sum(counts[-14:]) == 0,
        "glow": active_52 >= 40,
        "stage": "egg" if total_13 < 10 else "baby" if total_13 < 60 else "adult",
        "stars": sum(r["stargazerCount"] for r in user["repositories"]["nodes"]),
        "langs": [(n, v[1], v[0] / lang_total) for n, v in top],
    }


def sprite(stage, asleep, x, y):
    rows = {"egg": EGG, "baby": BABY, "adult": ADULT}[stage]
    if asleep:  # lenses go dark while it naps
        rows = [r.replace("w", "s") for r in rows]
    px = 128 // len(rows[0])
    pal = {"b": "#ff7a1a", "d": "#3a0a05", "c": "#fff4e6", "r": "#d62a1e", "g": AMBER,
           "s": "#111111", "w": "#ffffff", "n": "#1a0a05"}
    return "".join(f'<rect x="{x + c * px}" y="{y + r * px}" width="{px}" height="{px}" fill="{pal[ch]}"/>'
                   for r, row in enumerate(rows) for c, ch in enumerate(row) if ch != ".")


def card(x, y, w, h, body, label=None):
    lbl = f'<text x="{x + 24}" y="{y + 32}" class="lbl">{label}</text>' if label else ""
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="16" fill="{CARD}" fill-opacity=".86" stroke="{LINE}"/>{lbl}{body}'


def wrap(user, parts, h, footer=False):
    """Wrap card markup in one SVG with the fire gradient background."""
    esc = lambda t: html.escape(t or "", quote=True)
    W = 800
    H = h + (76 if footer else 40)  # 20px padding each side (+ footer line)
    stamp = dt.date.today().strftime("%d %b %Y")
    foot = (f'<text x="20" y="{H - 16}" class="small" style="fill:{INK}">updated {stamp} · fed by real contributions</text>'
            if footer else "")
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W + 40}" height="{H}" viewBox="0 0 {W + 40} {H}" role="img" aria-label="GitHub stats for {esc(user["login"])}">
<style>
text{{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;fill:{INK}}}
.lbl{{font-size:11px;letter-spacing:2px;fill:{MUTED}}} .small{{font-size:13px;fill:{MUTED}}}
.big{{font-size:28px;font-weight:700}} .zzz{{font-size:18px;animation:z 3s infinite}} .d2{{animation-delay:1.5s}}
.bob{{animation:bob 1.6s ease-in-out infinite}} .pulse{{animation:pulse 3s ease-in-out infinite}}
@keyframes bob{{50%{{transform:translateY(-6px)}}}} @keyframes pulse{{50%{{opacity:.4}}}}
@keyframes z{{0%{{opacity:0}}50%{{opacity:1}}100%{{opacity:0;transform:translateY(-10px)}}}}
</style>
<defs><linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">{"".join(f'<stop offset="{o}" stop-color="{c}"/>' for o, c in GRADIENT)}</linearGradient></defs>
<rect width="{W + 40}" height="{H}" rx="20" fill="url(#bg)"/>
<g transform="translate(20 20)">{"".join(parts)}</g>
{foot}
</svg>'''


def render(user, s):
    """Return (top SVG: profile + pet, bottom SVG: stats + languages)."""
    esc = lambda t: html.escape(t or "", quote=True)
    W = 800

    # profile card
    y = 0
    avatar = (f'<clipPath id="av"><circle cx="{W - 76}" cy="{y + 70}" r="44"/></clipPath>'
              f'<image href="data:image/png;base64,{user.get("avatar_b64", "")}" x="{W - 120}" y="{y + 26}" '
              f'width="88" height="88" clip-path="url(#av)"/>') if user.get("avatar_b64") else ""
    bio = esc((user.get("bio") or "")[:70])
    top = [card(0, y, W, 140,
        f'<text x="24" y="{y + 32}" class="lbl">PROFILE</text>'
        f'<text x="24" y="{y + 76}" class="big">{esc(user.get("name") or user["login"])}</text>'
        f'<text x="24" y="{y + 102}" class="small">@{esc(user["login"])}</text>'
        f'<text x="24" y="{y + 124}" class="small">{bio}</text>{avatar}')]

    # pet card
    y = 160
    level = s["active_13"]
    mood = "asleep · a commit wakes it" if s["asleep"] else f'{s["stage"]} · {s["streak"]}-day streak'
    glow = f'<circle cx="150" cy="{y + 140}" r="78" fill="{TEAL}" opacity=".18" class="pulse"/>' if s["glow"] else ""
    zzz = (f'<text x="230" y="{y + 80}" class="zzz" fill="{MUTED}">z</text>'
           f'<text x="246" y="{y + 62}" class="zzz d2" fill="{MUTED}">Z</text>') if s["asleep"] else ""
    grid = []
    for wi, w in enumerate(s["grid"]):
        for di, d in enumerate(w["contributionDays"]):
            c = d["contributionCount"]
            lv = 0 if c == 0 else 1 if c < 3 else 2 if c < 6 else 3 if c < 10 else 4
            grid.append(f'<rect x="{340 + wi * 30}" y="{y + 56 + di * 22}" width="24" height="18" rx="4" fill="{LEVELS[lv]}"/>')
    meter_w = 390 * level / 13
    top.append(card(0, y, W, 280,
        f'<text x="24" y="{y + 32}" class="lbl">CODE PET · LEVEL {level}</text>{glow}'
        f'<g class="{"" if s["asleep"] else "bob"}">{sprite(s["stage"], s["asleep"], 90, y + 80)}</g>{zzz}'
        f'<text x="150" y="{y + 232}" class="small" text-anchor="middle">{esc(mood)}</text>'
        + "".join(grid) +
        f'<text x="340" y="{y + 232}" class="small">{level} / 13 active weeks</text>'
        f'<rect x="340" y="{y + 244}" width="390" height="8" rx="4" fill="{LEVELS[0]}"/>'
        f'<rect x="340" y="{y + 244}" width="{meter_w:.0f}" height="8" rx="4" fill="{AMBER}"/>'))

    # two stat cards
    y = 0
    bottom = []
    for i, (lbl, val, sub) in enumerate([
        ("CONTRIBUTIONS", f'{s["year_total"]:,}', "in the last year"),
        ("REPOS · STARS", f'{user["repositories"]["totalCount"]} · {s["stars"]}', f'{user["followers"]["totalCount"]} followers'),
    ]):
        x = i * 410
        bottom.append(card(x, y, 390, 120,
            f'<text x="{x + 24}" y="{y + 32}" class="lbl">{lbl}</text>'
            f'<text x="{x + 24}" y="{y + 80}" class="big">{val}</text>'
            f'<text x="{x + 24}" y="{y + 104}" class="small">{sub}</text>'))

    # languages
    y = 140
    bars = []
    for i, (name, color, share) in enumerate(s["langs"]):
        by = y + 56 + i * 30
        bars.append(f'<text x="24" y="{by + 12}" class="small">{esc(name)}</text>'
                    f'<rect x="160" y="{by}" width="560" height="14" rx="7" fill="{LEVELS[0]}"/>'
                    f'<rect x="160" y="{by}" width="{max(560 * share, 8):.0f}" height="14" rx="7" fill="{color}"/>'
                    f'<text x="{W - 24}" y="{by + 12}" class="small" text-anchor="end">{share:.0%}</text>')
    lang_h = 76 + 30 * len(s["langs"])
    bottom.append(card(0, y, W, lang_h, f'<text x="24" y="{y + 32}" class="lbl">TOP LANGUAGES</text>' + "".join(bars)))

    return wrap(user, top, 440), wrap(user, bottom, y + lang_h, footer=True)


if __name__ == "__main__":
    if sys.argv[1] == "--fixture":
        user = json.load(open(sys.argv[2]))
    else:
        user = fetch(sys.argv[1])
    os.makedirs("assets", exist_ok=True)
    s = stats(user, dt.date.today())
    top, bottom = render(user, s)
    with open("assets/code-pet.svg", "w", encoding="utf-8") as f:
        f.write(top)
    with open("assets/code-stats.svg", "w", encoding="utf-8") as f:
        f.write(bottom)
    print(f'stage={s["stage"]} asleep={s["asleep"]} level={s["active_13"]} streak={s["streak"]}')
