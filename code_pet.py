"""Render assets/code-pet.svg from live GitHub data.

Usage: GH_TOKEN=... python scripts/code_pet.py <login>
       python scripts/code_pet.py --fixture data.json   (offline render for testing)
"""
import base64, datetime as dt, html, json, os, sys, urllib.request

QUERY = """query($login:String!){user(login:$login){
  name login bio avatarUrl(size:160) createdAt followers{totalCount}
  repositories(ownerAffiliations:OWNER, privacy:PUBLIC, isFork:false, first:100){
    totalCount nodes{stargazerCount languages(first:10){edges{size node{name color}}}}}
  contributionsCollection{contributionCalendar{totalContributions
    weeks{contributionDays{contributionCount date}}}}}}"""

BG, CARD, LINE = "#0a1020", "#111a2e", "#1e2a44"
INK, MUTED, TEAL, AMBER = "#e8ecf4", "#8592ad", "#2dd4bf", "#f5a524"
LEVELS = ["#16213a", "#134e4a", "#0f766e", "#14b8a6", "#5eead4"]

# Original pixel sprite. b=body d=shade e=eye w=shine m=mouth g=leaf
ADULT = ["....g..g....", ".....gg.....", "....bbbb....", "..bbbbbbbb..",
         ".bbbbbbbbbb.", ".bbewbbewbb.", ".bbeebbeebb.", ".bbbbbbbbbb.",
         ".bbbbmmbbbb.", "..bbbbbbbb..", "..dd....dd..", "............"]
BABY = ["............", "............", "............", "......g.....",
        "....bbbb....", "...bbbbbb...", "...bewbew...", "...beebee...",
        "...bbmmbb...", "....bbbb....", "....d..d....", "............"]
EGG = ["............", "............", ".....bb.....", "....bbbb....",
       "...bbgbbb...", "...bbbbbb...", "..bbbbbgbb..", "..bgbbbbbb..",
       "..bbbbbbbb..", "...bbbbbb...", "....bbbb....", "............"]


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


def sprite(stage, asleep, x, y, px=10):
    rows = {"egg": EGG, "baby": BABY, "adult": ADULT}[stage]
    if asleep and stage != "egg":  # closed eyes: drop the top eye row
        rows = [r.replace("e", "b").replace("w", "b") if "w" in r else r for r in rows]
    pal = {"b": TEAL, "d": "#0f766e", "e": BG, "w": "#ffffff", "m": "#0f766e", "g": AMBER}
    rects = [f'<rect x="{x + c * px}" y="{y + r * px}" width="{px}" height="{px}" fill="{pal[ch]}"/>'
             for r, row in enumerate(rows) for c, ch in enumerate(row) if ch != "."]
    return "".join(rects)


def card(x, y, w, h, body, label=None):
    lbl = f'<text x="{x + 24}" y="{y + 32}" class="lbl">{label}</text>' if label else ""
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="16" fill="{CARD}" stroke="{LINE}"/>{lbl}{body}'


def render(user, s):
    esc = lambda t: html.escape(t or "", quote=True)
    W = 800
    out = []

    # 1. pet card
    level = s["active_13"]
    mood = "asleep · a commit wakes it" if s["asleep"] else f'{s["stage"]} · {s["streak"]}-day streak'
    glow = f'<circle cx="150" cy="140" r="78" fill="{TEAL}" opacity=".18" class="pulse"/>' if s["glow"] else ""
    zzz = (f'<text x="230" y="80" class="zzz" fill="{MUTED}">z</text>'
           f'<text x="246" y="62" class="zzz d2" fill="{MUTED}">Z</text>') if s["asleep"] else ""
    grid = []
    for wi, w in enumerate(s["grid"]):
        for di, d in enumerate(w["contributionDays"]):
            c = d["contributionCount"]
            lv = 0 if c == 0 else 1 if c < 3 else 2 if c < 6 else 3 if c < 10 else 4
            grid.append(f'<rect x="{340 + wi * 30}" y="{56 + di * 22}" width="24" height="18" rx="4" fill="{LEVELS[lv]}"/>')
    meter_w = 390 * level / 13
    out.append(card(0, 0, W, 280,
        f'<text x="24" y="32" class="lbl">CODE PET · LEVEL {level}</text>{glow}'
        f'<g class="{"" if s["asleep"] else "bob"}">{sprite(s["stage"], s["asleep"], 90, 80)}</g>{zzz}'
        f'<text x="150" y="232" class="small" text-anchor="middle">{esc(mood)}</text>'
        + "".join(grid) +
        f'<text x="340" y="232" class="small">{level} / 13 active weeks</text>'
        f'<rect x="340" y="244" width="390" height="8" rx="4" fill="{LEVELS[0]}"/>'
        f'<rect x="340" y="244" width="{meter_w:.0f}" height="8" rx="4" fill="{AMBER}"/>'))

    # 2. profile card
    y = 300
    avatar = (f'<clipPath id="av"><circle cx="{W - 76}" cy="{y + 70}" r="44"/></clipPath>'
              f'<image href="data:image/png;base64,{user.get("avatar_b64", "")}" x="{W - 120}" y="{y + 26}" '
              f'width="88" height="88" clip-path="url(#av)"/>') if user.get("avatar_b64") else ""
    bio = esc((user.get("bio") or "")[:70])
    out.append(card(0, y, W, 140,
        f'<text x="24" y="{y + 32}" class="lbl">PROFILE</text>'
        f'<text x="24" y="{y + 76}" class="big">{esc(user.get("name") or user["login"])}</text>'
        f'<text x="24" y="{y + 102}" class="small">@{esc(user["login"])}</text>'
        f'<text x="24" y="{y + 124}" class="small">{bio}</text>{avatar}'))

    # 3. two stat cards
    y = 460
    for i, (lbl, val, sub) in enumerate([
        ("CONTRIBUTIONS", f'{s["year_total"]:,}', "in the last year"),
        ("REPOS · STARS", f'{user["repositories"]["totalCount"]} · {s["stars"]}', f'{user["followers"]["totalCount"]} followers'),
    ]):
        x = i * 410
        out.append(card(x, y, 390, 120,
            f'<text x="{x + 24}" y="{y + 32}" class="lbl">{lbl}</text>'
            f'<text x="{x + 24}" y="{y + 80}" class="big">{val}</text>'
            f'<text x="{x + 24}" y="{y + 104}" class="small">{sub}</text>'))

    # 4. languages
    y = 600
    bars = []
    for i, (name, color, share) in enumerate(s["langs"]):
        by = y + 56 + i * 30
        bars.append(f'<text x="24" y="{by + 12}" class="small">{esc(name)}</text>'
                    f'<rect x="160" y="{by}" width="560" height="14" rx="7" fill="{LEVELS[0]}"/>'
                    f'<rect x="160" y="{by}" width="{max(560 * share, 8):.0f}" height="14" rx="7" fill="{color}"/>'
                    f'<text x="{W - 24}" y="{by + 12}" class="small" text-anchor="end">{share:.0%}</text>')
    lang_h = 76 + 30 * len(s["langs"])
    out.append(card(0, y, W, lang_h, f'<text x="24" y="{y + 32}" class="lbl">TOP LANGUAGES</text>' + "".join(bars)))

    H = y + lang_h + 76  # 20px outer padding + footer
    stamp = dt.date.today().strftime("%d %b %Y")
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W + 40}" height="{H}" viewBox="0 0 {W + 40} {H}" role="img" aria-label="Code pet and GitHub stats for {esc(user["login"])}">
<style>
text{{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;fill:{INK}}}
.lbl{{font-size:11px;letter-spacing:2px;fill:{MUTED}}} .small{{font-size:13px;fill:{MUTED}}}
.big{{font-size:28px;font-weight:700}} .zzz{{font-size:18px;animation:z 3s infinite}} .d2{{animation-delay:1.5s}}
.bob{{animation:bob 1.6s ease-in-out infinite}} .pulse{{animation:pulse 3s ease-in-out infinite}}
@keyframes bob{{50%{{transform:translateY(-6px)}}}} @keyframes pulse{{50%{{opacity:.4}}}}
@keyframes z{{0%{{opacity:0}}50%{{opacity:1}}100%{{opacity:0;transform:translateY(-10px)}}}}
</style>
<rect width="{W + 40}" height="{H}" rx="20" fill="{BG}"/>
<g transform="translate(20 20)">{"".join(out)}</g>
<text x="20" y="{H - 16}" class="small">updated {stamp} · fed by real contributions</text>
</svg>'''


if __name__ == "__main__":
    if sys.argv[1] == "--fixture":
        user = json.load(open(sys.argv[2]))
    else:
        user = fetch(sys.argv[1])
    os.makedirs("assets", exist_ok=True)
    s = stats(user, dt.date.today())
    with open("assets/code-pet.svg", "w", encoding="utf-8") as f:
        f.write(render(user, s))
    print(f'stage={s["stage"]} asleep={s["asleep"]} level={s["active_13"]} streak={s["streak"]}')
