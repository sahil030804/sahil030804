"""
Generate the animated SVGs used by the profile README (light + dark variants).

    python -m venv .venv && .venv/bin/pip install fonttools brotli
    .venv/bin/python tools/generate.py

GitHub renders README images as <img>, which strips scripts but keeps CSS
animations inside SVGs, so every effect here is pure CSS keyframes. Each file
embeds only the glyphs it needs (fonts are OFL: Bricolage Grotesque,
Instrument Sans, JetBrains Mono). Motion is disabled under
prefers-reduced-motion, and every element's resting state is its final state.

Content policy: every fact comes from the resume. Nothing invented.
"""
import base64
import io
import math
import random
from pathlib import Path

from fontTools import subset
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

ROOT = Path(__file__).resolve().parent.parent
FONTS = ROOT / "tools" / "fonts"
OUT = ROOT / "assets"

PALETTES = {
    "light": dict(bg="#f2f2ef", surface="#fafaf8", ink="#121316", muted="#5a5d64", faint="#a3a5aa", rule="#d8d8d3"),
    "dark": dict(bg="#0b0c0e", surface="#141518", ink="#ecece7", muted="#9c9fa6", faint="#4a4d53", rule="#25272b"),
}

# Font roles: (file, variation axes)
DISPLAY = ("BricolageGrotesque-latin.woff2", {"wght": 700, "wdth": 85, "opsz": 96})
SANS = ("InstrumentSans-latin.woff2", {"wght": 400})
MONO = ("JetBrainsMono-latin.woff2", {"wght": 400})

# Typewriter covers are hidden outright when motion is reduced so text stays visible.
REDUCED_MOTION = "@media (prefers-reduced-motion: reduce){*{animation:none!important}.cover{display:none}}"

_instances = {}


def instance(role):
    """Static (non-variable) TTFont for a font role, cached."""
    key = role[0]
    if key not in _instances:
        font = TTFont(FONTS / role[0])
        _instances[key] = instancer.instantiateVariableFont(font, role[1])
    return _instances[key]


def advance(role, text, size, tracking=0.0):
    """Width in px of `text` set at `size` with extra `tracking` per glyph."""
    font = instance(role)
    cmap, hmtx = font.getBestCmap(), font["hmtx"]
    upm = font["head"].unitsPerEm
    return sum(hmtx[cmap[ord(ch)]][0] * size / upm + tracking for ch in text)


def glyph_advances(role, text, size, tracking=0.0):
    return [advance(role, ch, size, tracking) for ch in text]


def font_face(family, role, text):
    """@font-face rule embedding `role` subset to the glyphs in `text`."""
    buf = io.BytesIO()
    font = TTFont(FONTS / role[0])
    font = instancer.instantiateVariableFont(font, role[1])
    opts = subset.Options()
    opts.flavor = "woff2"
    opts.layout_features = ["kern", "liga"]
    sub = subset.Subsetter(opts)
    sub.populate(text=text + " ")
    sub.subset(font)
    font.flavor = "woff2"
    font.save(buf)
    data = base64.b64encode(buf.getvalue()).decode()
    return f'@font-face{{font-family:{family};src:url(data:font/woff2;base64,{data}) format("woff2")}}'


def esc(text):
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("|", "&#124;")


def svg_doc(width, height, label, style, body, p):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" '
        f'role="img" aria-label="{esc(label)}">\n<style>\n{style}\n{REDUCED_MOTION}\n</style>\n'
        f'<rect width="{width}" height="{height}" fill="{p["bg"]}"/>\n{body}\n'
        f'<rect x="0.5" y="0.5" width="{width-1}" height="{height-1}" fill="none" stroke="{p["rule"]}"/>\n</svg>\n'
    )


_typewriter_ids = iter(range(10**6))


def typewriter(x, y, text, role, size, p, start, per_char, cls, fill, cover_fill):
    """
    Text revealed left-to-right by a sliding cover rect, which then fades
    out so it never masks the background once typing has finished.
    Returns (svg, css, end_time).
    """
    width = advance(role, text, size)
    n = max(len(text), 1)
    dur = per_char * n
    anim = f"tw{next(_typewriter_ids)}"
    keyframes = (
        f"@keyframes {anim}{{from{{transform:translateX(0)}}to{{transform:translateX({width:.1f}px)}}}}"
        f".{anim}{{animation:{anim} {dur:.2f}s steps({n}) {start:.2f}s both,hide .01s {start + dur:.2f}s both}}"
        "@keyframes hide{to{opacity:0}}"
    )
    body = (
        f'<text x="{x}" y="{y}" class="{cls}" font-size="{size}" fill="{fill}">{esc(text)}</text>'
        f'<g class="cover {anim}"><rect x="{x}" y="{y-size}" width="{width+size:.1f}" height="{size*1.35:.1f}" fill="{cover_fill}"/></g>'
    )
    return body, keyframes, start + dur


# ---------------------------------------------------------------------------
# Hero: kinetic name, drifting particles, live request trace with burst
# ---------------------------------------------------------------------------
NAME = "Sahil Ranpariya"
ROLE_LINE = "Backend Engineer | Node.js"
LEDE = "Building scalable SaaS products from scratch."
TRACE_TITLE = "Layered service architecture"
LAYERS = ["route", "controller", "service", "data access"]


def hero(mode, p):
    W, H = 1280, 380
    rnd = random.Random(7)
    css, body = [], []

    css.append(font_face("D", DISPLAY, NAME + TRACE_TITLE))
    css.append(font_face("S", SANS, LEDE))
    css.append(font_face("M", MONO, ROLE_LINE + "".join(LAYERS) + "0123456789request"))
    css.append(".d{font-family:D,system-ui,sans-serif;font-weight:700}.s{font-family:S,system-ui,sans-serif}.m{font-family:M,ui-monospace,monospace}")

    # Dot grid + drifting particles
    body.append(
        f'<defs><pattern id="grid" width="24" height="24" patternUnits="userSpaceOnUse">'
        f'<circle cx="1" cy="1" r="1" fill="{p["rule"]}"/></pattern></defs>'
        f'<rect width="{W}" height="{H}" fill="url(#grid)"/>'
    )
    css.append("@keyframes drift{0%{transform:translateY(0);opacity:0}15%{opacity:var(--o)}85%{opacity:var(--o)}100%{transform:translateY(-70px);opacity:0}}")
    for i in range(46):
        x, y = rnd.uniform(0, W), rnd.uniform(40, H)
        size = rnd.choice([2, 2, 3, 4])
        dur, delay, op = rnd.uniform(6, 12), rnd.uniform(-12, 0), rnd.uniform(0.35, 0.8)
        body.append(
            f'<rect x="{x:.0f}" y="{y:.0f}" width="{size}" height="{size}" fill="{p["faint"]}" '
            f'style="--o:{op:.2f};animation:drift {dur:.1f}s linear {delay:.1f}s infinite;opacity:0"/>'
        )

    # Role line: typewriter
    role_body, role_css, role_end = typewriter(64, 96, ROLE_LINE, MONO, 18, p, 0.2, 0.045, "m", p["muted"], p["bg"])
    css.append(role_css)
    body.append(role_body)

    # Name: letters rise in, staggered
    size, tracking = 108, -3.8
    css.append("@keyframes rise{from{transform:translateY(46px);opacity:0}to{transform:translateY(0);opacity:1}}")
    x = 60.0
    for i, (ch, adv) in enumerate(zip(NAME, glyph_advances(DISPLAY, NAME, size, tracking))):
        if ch != " ":
            body.append(
                f'<text x="{x:.1f}" y="222" class="d" font-size="{size}" fill="{p["ink"]}" '
                f'style="animation:rise .9s cubic-bezier(.16,1,.3,1) {0.35 + i*0.045:.3f}s both">{esc(ch)}</text>'
            )
        x += adv

    # Lede fades up after the name
    body.append(
        f'<text x="64" y="282" class="s" font-size="26" fill="{p["muted"]}" '
        f'style="animation:rise 1s cubic-bezier(.16,1,.3,1) 1.2s both">{esc(LEDE)}</text>'
    )

    # Trace panel
    PX, PY, PW, PH = 876, 44, 348, 292
    body.append(f'<rect x="{PX}.5" y="{PY}.5" width="{PW}" height="{PH}" fill="{p["surface"]}" stroke="{p["rule"]}"/>')
    body.append(f'<text x="{PX+22}" y="{PY+35}" class="d" font-size="17" letter-spacing="0.4" fill="{p["ink"]}">{esc(TRACE_TITLE)}</text>')
    body.append(f'<line x1="{PX}" y1="{PY+55}.5" x2="{PX+PW}" y2="{PY+55}.5" stroke="{p["rule"]}"/>')

    node_x = PX + 38
    ys = [PY + 96 + i * 54 for i in range(len(LAYERS))]
    body.append(f'<line x1="{node_x}" y1="{ys[0]}" x2="{node_x}" y2="{ys[-1]}" stroke="{p["ink"]}"/>')

    # Timeline (seconds) of one request, looping
    cycle = 5.2
    arrive = [0.6, 1.4, 2.2, 3.0]  # packet arrives at node i
    dwell = 0.35

    def pct(t):
        return f"{t / cycle * 100:.2f}%"

    # Packet travels down the spine, pausing at each node
    frames = [f"0%{{transform:translateY({ys[0]-8}px);opacity:0}}", f"{pct(0.35)}{{transform:translateY({ys[0]-8}px);opacity:1}}"]
    for i, t in enumerate(arrive):
        frames.append(f"{pct(t)}{{transform:translateY({ys[i]}px);opacity:1}}")
        frames.append(f"{pct(t + dwell)}{{transform:translateY({ys[i]}px);opacity:1}}")
    frames.append(f"{pct(arrive[-1] + dwell + 0.01)}{{transform:translateY({ys[-1]}px);opacity:0}}")
    frames.append(f"100%{{transform:translateY({ys[-1]}px);opacity:0}}")
    css.append("@keyframes packet{" + "".join(frames) + "}")
    body.append(
        f'<g style="animation:packet {cycle}s cubic-bezier(.65,0,.35,1) 1.2s infinite both;opacity:0">'
        f'<rect x="{node_x-5}" y="-5" width="10" height="10" fill="{p["ink"]}"/></g>'
    )

    # Nodes invert while the packet is inside them
    for i, (layer, y) in enumerate(zip(LAYERS, ys)):
        t0, t1 = arrive[i] - 0.05, arrive[i] + dwell + 0.25
        css.append(
            f"@keyframes n{i}{{0%,{pct(t0)}{{fill:{p['surface']}}}{pct(t0+0.05)},{pct(t1)}{{fill:{p['ink']}}}{pct(t1+0.2)},100%{{fill:{p['surface']}}}}}"
            f"@keyframes t{i}{{0%,{pct(t0)}{{fill:{p['ink']}}}{pct(t0+0.05)},{pct(t1)}{{fill:{p['surface']}}}{pct(t1+0.2)},100%{{fill:{p['ink']}}}}}"
        )
        anim = f"{cycle}s linear 1.2s infinite"
        body.append(
            f'<rect x="{node_x-16}" y="{y-16}" width="32" height="32" stroke="{p["ink"]}" fill="{p["surface"]}" style="animation:n{i} {anim}"/>'
            f'<text x="{node_x}" y="{y+4.5}" class="m" font-size="12" text-anchor="middle" fill="{p["ink"]}" style="animation:t{i} {anim}">{i+1:02d}</text>'
            f'<text x="{node_x+34}" y="{y+6}" class="m" font-size="17" fill="{p["ink"]}">{esc(layer)}</text>'
        )

    # Particle burst when the request reaches the data layer
    burst_t = arrive[-1] + dwell
    bx, by = node_x, ys[-1]
    for k in range(22):
        angle = 2 * math.pi * k / 22 + rnd.uniform(-0.15, 0.15)
        dist = rnd.uniform(50, 118)
        dx, dy = math.cos(angle) * dist, math.sin(angle) * dist
        s = rnd.choice([4, 5, 6, 7])
        css.append(
            f"@keyframes b{k}{{0%,{pct(burst_t)}{{transform:translate(0,0) scale(1);opacity:0}}"
            f"{pct(burst_t+0.02)}{{opacity:1}}"
            f"{pct(burst_t+0.7)}{{transform:translate({dx*0.8:.1f}px,{dy*0.8:.1f}px) scale(1);opacity:1}}"
            f"{pct(burst_t+1.2)},100%{{transform:translate({dx:.1f}px,{dy:.1f}px) scale(.4);opacity:0}}}}"
        )
        body.append(
            f'<rect x="{bx - s/2:.1f}" y="{by - s/2:.1f}" width="{s}" height="{s}" fill="{p["ink"]}" '
            f'style="transform-box:fill-box;transform-origin:center;animation:b{k} {cycle}s cubic-bezier(.16,1,.3,1) 1.2s infinite both;opacity:0"/>'
        )

    # Shockwave: square ring expanding out of the data-access node
    css.append(
        f"@keyframes ring{{0%,{pct(burst_t)}{{transform:scale(1);opacity:0}}{pct(burst_t+0.02)}{{opacity:.9}}"
        f"{pct(burst_t+0.9)},100%{{transform:scale(3.4);opacity:0}}}}"
    )
    body.append(
        f'<rect x="{bx-16}" y="{by-16}" width="32" height="32" fill="none" stroke="{p["ink"]}" '
        f'style="transform-box:fill-box;transform-origin:center;animation:ring {cycle}s cubic-bezier(.16,1,.3,1) 1.2s infinite both;opacity:0"/>'
    )

    return svg_doc(W, H, f"{NAME}, {ROLE_LINE}", "\n".join(css), "\n".join(body), p)


# ---------------------------------------------------------------------------
# Terminal: `whoami` session typed out, facts from the resume summary
# ---------------------------------------------------------------------------
SESSION = [
    ("whoami", ["sahil ranpariya  /  backend engineer, node.js"]),
    ("cat focus.txt", ["REST APIs, third-party integrations, OAuth, webhooks,", "event-driven systems, AI-powered applications"]),
    ("ls domains/", ["calendar/   e-commerce/   messaging/   payments/"]),
    ("echo $LOCATION", ["Surat, Gujarat"]),
]


def terminal(mode, p):
    W = 1280
    line_h, size = 34, 19
    rows = sum(1 + len(out) for _, out in SESSION) + 1
    H = 64 + rows * line_h + 24
    all_text = "".join(cmd + "".join(out) for cmd, out in SESSION) + "$ "
    css = [
        font_face("M", MONO, all_text),
        ".m{font-family:M,ui-monospace,monospace;white-space:pre}",
        "@keyframes show{from{opacity:0}to{opacity:1}}",
        "@keyframes blink{0%,49%{opacity:1}50%,100%{opacity:0}}",
    ]
    body = [
        f'<rect x="0" y="0" width="{W}" height="44" fill="{p["surface"]}"/>',
        f'<line x1="0" y1="44.5" x2="{W}" y2="44.5" stroke="{p["rule"]}"/>',
    ]
    for i in range(3):
        body.append(f'<circle cx="{28 + i*20}" cy="22" r="6" fill="none" stroke="{p["faint"]}"/>')
    body.append(f'<text x="{W/2}" y="27" class="m" font-size="13" text-anchor="middle" fill="{p["muted"]}">sahil@github: ~</text>')
    css[0] = font_face("M", MONO, all_text + "sahil@github: ~")

    y, t = 64 + line_h - 8, 0.5
    prompt_w = advance(MONO, "$ ", size)
    for cmd, outputs in SESSION:
        body.append(f'<text x="48" y="{y}" class="m" font-size="{size}" fill="{p["muted"]}" style="animation:show .01s {t:.2f}s both">$</text>')
        tw_body, tw_css, t = typewriter(48 + prompt_w, y, cmd, MONO, size, p, t + 0.25, 0.07, "m", p["ink"], p["bg"])
        body.append(tw_body)
        css.append(tw_css)
        t += 0.25
        for out in outputs:
            y += line_h
            body.append(f'<text x="48" y="{y}" class="m" font-size="{size}" fill="{p["muted"]}" style="animation:show .15s {t:.2f}s both">{esc(out)}</text>')
            t += 0.12
        y += line_h
        t += 0.35

    body.append(f'<text x="48" y="{y}" class="m" font-size="{size}" fill="{p["muted"]}" style="animation:show .01s {t:.2f}s both">$</text>')
    body.append(
        f'<rect x="{48 + prompt_w:.1f}" y="{y - size + 3}" width="11" height="{size + 2}" fill="{p["ink"]}" '
        f'style="animation:show .01s {t:.2f}s both,blink 1.1s steps(1) {t:.2f}s infinite"/>'
    )
    return svg_doc(W, H, "whoami: Sahil Ranpariya, backend engineer", "\n".join(css), "\n".join(body), p)


# ---------------------------------------------------------------------------
# Project cards, each with its own motif
# ---------------------------------------------------------------------------
CARDS = {
    "stripe-billing": dict(
        meta="2025",
        title="Stripe Billing Service",
        lines=["Subscriptions, one-time payments and", "idempotent webhook reconciliation."],
        stack="Express · PostgreSQL · BullMQ · Stripe",
        motif="queue",
    ),
    "jawabai": dict(
        meta="2026 · Pending deployment",
        title="JawabAI",
        lines=["WhatsApp AI support platform with a", "queue-based retrieval pipeline."],
        stack="Express 5 · PostgreSQL · BullMQ · ONNX",
        motif="chat",
    ),
    "switchboard": dict(
        meta="2026 - Present",
        title="Switchboard",
        lines=["Commerce operations platform with a", "hardened session and CSRF layer."],
        stack="Node 22 · Express 5 · PostgreSQL · Zod",
        motif="hash",
    ),
}


def motif_queue(p, x, y):
    """Webhook events flow into a queue."""
    css = ["@keyframes ev{0%{transform:translateX(0);opacity:0}15%{opacity:1}70%{transform:translateX(64px);opacity:1}85%,100%{transform:translateX(64px);opacity:0}}"]
    body = [
        f'<line x1="{x}" y1="{y+22}" x2="{x+70}" y2="{y+22}" stroke="{p["rule"]}"/>',
        f'<rect x="{x+72}.5" y="{y+6}.5" width="36" height="32" fill="none" stroke="{p["ink"]}"/>',
    ]
    for i in range(3):
        body.append(
            f'<rect x="{x}" y="{y+18}" width="8" height="8" fill="{p["ink"]}" '
            f'style="animation:ev 2.4s cubic-bezier(.65,0,.35,1) {i*0.8:.1f}s infinite both"/>'
        )
    for i in range(3):
        body.append(f'<rect x="{x+78+i*9}" y="{y+18}" width="6" height="8" fill="{p["faint"]}"/>')
    return css, body


def motif_chat(p, x, y):
    """Customer message in, answer out."""
    css = [
        "@keyframes cin{0%,5%{opacity:0;transform:translateY(6px)}15%,85%{opacity:1;transform:none}95%,100%{opacity:0}}",
        "@keyframes cdot{0%,25%{opacity:0}30%,50%{opacity:1}55%,100%{opacity:0}}",
        "@keyframes cout{0%,50%{opacity:0;transform:translateY(6px)}60%,85%{opacity:1;transform:none}95%,100%{opacity:0}}",
    ]
    anim = "4s cubic-bezier(.16,1,.3,1) infinite both"
    body = [
        f'<g style="animation:cin {anim}"><rect x="{x}" y="{y}" width="72" height="22" fill="none" stroke="{p["ink"]}"/>'
        f'<rect x="{x+8}" y="{y+7}" width="44" height="2" fill="{p["muted"]}"/><rect x="{x+8}" y="{y+13}" width="30" height="2" fill="{p["muted"]}"/></g>',
        f'<g style="animation:cdot {anim}">' + "".join(
            f'<rect x="{x+72+i*8}" y="{y+32}" width="4" height="4" fill="{p["faint"]}"/>' for i in range(3)
        ) + "</g>",
        f'<g style="animation:cout {anim}"><rect x="{x+36}" y="{y+30}" width="72" height="22" fill="{p["ink"]}"/>'
        f'<rect x="{x+44}" y="{y+37}" width="50" height="2" fill="{p["surface"]}"/><rect x="{x+44}" y="{y+43}" width="36" height="2" fill="{p["surface"]}"/></g>',
    ]
    return css, body


def motif_hash(p, x, y):
    """Opaque token hash scrambling."""
    variants = ["9f2c 41ab e7d0", "c83e 0b94 5f1a", "2d7f a60c 19e8", "e41b 7c03 b8d5"]
    css = [f"@keyframes h{i}{{0%,{i*25}%{{opacity:0}}{i*25+1}%,{i*25+24}%{{opacity:1}}{i*25+25}%,100%{{opacity:0}}}}" for i in range(4)]
    body = [f'<text x="{x}" y="{y+10}" class="m" font-size="11" fill="{p["muted"]}">sha-256</text>']
    for i, v in enumerate(variants):
        body.append(
            f'<text x="{x}" y="{y+34}" class="m" font-size="15" fill="{p["ink"]}" '
            f'style="animation:h{i} 1.6s steps(1) infinite;opacity:{1 if i == 0 else 0}">{v}</text>'
        )
    return css, body, "".join(variants) + "sha-256"


def card(key, mode, p):
    c = CARDS[key]
    W, H = 420, 270
    motif_css, motif_body, extra = [], [], ""
    mx, my = W - 140, 24
    if c["motif"] == "queue":
        motif_css, motif_body = motif_queue(p, mx, my)
    elif c["motif"] == "chat":
        motif_css, motif_body = motif_chat(p, mx, my)
    else:
        motif_css, motif_body, extra = motif_hash(p, mx, my)

    css = [
        font_face("D", DISPLAY, c["title"]),
        font_face("S", SANS, "".join(c["lines"])),
        font_face("M", MONO, c["meta"] + c["stack"] + extra),
        ".d{font-family:D,system-ui,sans-serif;font-weight:700}.s{font-family:S,system-ui,sans-serif}.m{font-family:M,ui-monospace,monospace}",
        *motif_css,
    ]
    title_size = 44 if advance(DISPLAY, c["title"], 44, -1.4) < W - 56 else 38
    body = [
        f'<rect x="0" y="0" width="{W}" height="{H}" fill="{p["surface"]}"/>',
        f'<text x="28" y="44" class="m" font-size="14" fill="{p["muted"]}">{esc(c["meta"])}</text>',
        *motif_body,
        f'<text x="25" y="128" class="d" font-size="{title_size}" letter-spacing="-1.4" fill="{p["ink"]}">{esc(c["title"])}</text>',
        *[f'<text x="28" y="{164 + i*26}" class="s" font-size="19" fill="{p["muted"]}">{esc(line)}</text>' for i, line in enumerate(c["lines"])],
        f'<line x1="28" y1="{H-50}.5" x2="{W-28}" y2="{H-50}.5" stroke="{p["rule"]}"/>',
        f'<text x="28" y="{H-21}" class="m" font-size="14" fill="{p["muted"]}">{esc(c["stack"])}</text>',
    ]
    return svg_doc(W, H, f'{c["title"]}: {" ".join(c["lines"])}', "\n".join(css), "\n".join(body), p)


# ---------------------------------------------------------------------------
# Stack ticker: two rows drifting in opposite directions
# ---------------------------------------------------------------------------
ROW_A = ["Node.js", "Express", "PostgreSQL", "MongoDB", "Redis", "BullMQ", "Sequelize", "Mongoose", "JWT", "OAuth 2.0"]
ROW_B = ["Stripe", "Shopify", "Squarespace", "Google Calendar", "Microsoft Graph", "Apple CalDAV", "Mailgun", "AWS S3", "CloudFront", "Nginx"]


def ticker(mode, p):
    W, H = 1280, 132
    size, gap = 20, 22
    sep = "  /  "
    css = [
        font_face("M", MONO, "".join(ROW_A + ROW_B) + sep),
        ".m{font-family:M,ui-monospace,monospace}",
    ]
    body = []
    for row, (items, y, direction, dur) in enumerate([(ROW_A, 54, -1, 38), (ROW_B, 98, 1, 44)]):
        text = sep.join(items) + sep
        width = advance(MONO, text, size)
        start, end = (0, -width) if direction < 0 else (-width, 0)
        css.append(f"@keyframes r{row}{{from{{transform:translateX({start:.1f}px)}}to{{transform:translateX({end:.1f}px)}}}}")
        fill = p["ink"] if row == 0 else p["muted"]
        copies = "".join(
            f'<text x="{k*width:.1f}" y="{y}" class="m" font-size="{size}" fill="{fill}">{esc(text)}</text>' for k in range(3)
        )
        body.append(f'<g style="animation:r{row} {dur}s linear infinite">{copies}</g>')
    # Soft fade at both edges
    body.append(
        f'<defs><linearGradient id="fl"><stop offset="0" stop-color="{p["bg"]}"/><stop offset="1" stop-color="{p["bg"]}" stop-opacity="0"/></linearGradient>'
        f'<linearGradient id="fr"><stop offset="0" stop-color="{p["bg"]}" stop-opacity="0"/><stop offset="1" stop-color="{p["bg"]}"/></linearGradient></defs>'
        f'<rect x="0" y="0" width="120" height="{H}" fill="url(#fl)"/><rect x="{W-120}" y="0" width="120" height="{H}" fill="url(#fr)"/>'
    )
    return svg_doc(W, H, "Stack: " + ", ".join(ROW_A + ROW_B), "\n".join(css), "\n".join(body), p)


# ---------------------------------------------------------------------------
# Connect buttons
# ---------------------------------------------------------------------------
BUTTONS = {"linkedin": "LinkedIn", "email": "Email"}


def button(key, mode, p):
    label = BUTTONS[key]
    size = 15
    W, H = int(advance(MONO, label, size) + 76), 44
    css = [
        font_face("M", MONO, label),
        ".m{font-family:M,ui-monospace,monospace}",
        "@keyframes nudge{0%,70%,100%{transform:translateX(0)}80%{transform:translateX(4px)}}",
    ]
    ax = W - 34
    body = [
        f'<rect x="0" y="0" width="{W}" height="{H}" fill="{p["surface"]}"/>',
        f'<text x="20" y="28" class="m" font-size="{size}" fill="{p["ink"]}">{esc(label)}</text>',
        f'<g style="animation:nudge 3s cubic-bezier(.16,1,.3,1) infinite">'
        f'<path d="M{ax} 22 h12 M{ax+7} 16 l6 6 l-6 6" fill="none" stroke="{p["ink"]}" stroke-width="1.5"/></g>',
    ]
    return svg_doc(W, H, label, "\n".join(css), "\n".join(body), p)


def main():
    OUT.mkdir(exist_ok=True)
    outputs = {"hero": hero, "terminal": terminal, "stack": ticker}
    for key in CARDS:
        outputs[f"card-{key}"] = lambda mode, p, key=key: card(key, mode, p)
    for key in BUTTONS:
        outputs[f"btn-{key}"] = lambda mode, p, key=key: button(key, mode, p)

    for name, build in outputs.items():
        for mode, palette in PALETTES.items():
            path = OUT / f"{name}-{mode}.svg"
            path.write_text(build(mode, palette))
            print(f"{path.relative_to(ROOT)}  {path.stat().st_size // 1024} KB")


if __name__ == "__main__":
    main()
