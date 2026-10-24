#!/usr/bin/env python3
"""Rebuild the project docket of the landing page from data/projects.json.

    python3 build_projects.py                      rebuild every page that carries the markers
    python3 build_projects.py add --title "Name" --href URL --blurb "One or two sentences." \
                                  --go "Open atlas" --cta "One-sentence invitation." [--icon icon.svg] [--phone] [--short "Short name"]
    python3 build_projects.py check [YYYY-MM-DD]   print the Spotlight pick for a date and the two weeks after it
    python3 build_projects.py --file some.html     rebuild one page only

What one entry in data/projects.json drives:
  - the project grid (a card, in list order),
  - the constellation in the hero (a bloom node with the project's name on hover; threads are re-laid for the new count),
  - the Spotlight line (the project joins the daily rotation; for its first `new_project_days` days it takes the spotlight outright),
  - the loom's nodeData on the live page, if that page carries the markers.

Markers the script rewrites (everything outside them is left alone):
  <!-- projects:start --> ... <!-- projects:end -->               the grid
  <!-- constellation:start --> ... <!-- constellation:end -->     threads and nodes inside the hero SVG
  <!-- spotlight-fallback:start --> ... <!-- spotlight-fallback:end -->   the prerendered Spotlight line
  /* spotlight:start */ ... /* spotlight:end */                   the data the Spotlight script reads
  // nodeData:start ... // nodeData:end                           the live loom's node list (live page only)

Spotlight rule (also implemented in the page script, so the page and this check agree):
  day = UTC day number. If any project was added within the last `new_project_days` days, those projects take the
  spotlight, cycling if there are several. Otherwise the pick is the project at
  (index of anchor_title + (day - anchor_date)) mod N, in list order. So a new entry gets a few days up front,
  then joins the cycle, and nothing else needs editing.
"""
import argparse
import datetime as dt
import html
import json
import math
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent
DATA = ROOT / "data" / "projects.json"
PAGES = [ROOT / "index.html"]


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def save(data):
    DATA.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


# ── rendering ──────────────────────────────────────────────────────────────

def render_cards_b(projects):
    """Mockup B's cards: icon and title on one line, blurb, call-to-action label."""
    out = []
    for p in projects:
        out.append(f'''        <a class="card" href="{html.escape(p["href"])}">
          <div class="head">{p["icon"]}<h3>{html.escape(p["title"])}</h3></div>
          <p>{html.escape(p["blurb"])}</p>
          <span class="go">{html.escape(p["go"])}<svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 12h14M13 6l6 6-6 6"/></svg></span>
        </a>''')
    return "\n".join(out)


def render_cards_live(projects):
    """The live page's cards."""
    out = []
    for p in projects:
        out.append(f'''        <a class="project" href="{html.escape(p["href"])}">
          {p["icon"]}
          <h3>{html.escape(p["title"])}</h3>
          <p>{html.escape(p["blurb"])}</p>
          <span class="go">{html.escape(p["go"])} →</span>
        </a>''')
    return "\n".join(out)


def label_lines(title):
    words = title.upper().split()
    if len(title) > 14 and len(words) > 1:
        best = min(range(1, len(words)), key=lambda k: abs(len(" ".join(words[:k])) - len(" ".join(words[k:]))))
        return [" ".join(words[:best]), " ".join(words[best:])]
    return [" ".join(words)]


def render_constellation(projects):
    """Threads and bloom nodes for the hero SVG (viewBox 0 0 420 420), laid out for any number of projects."""
    n = len(projects)
    pts, nodes, threads = [], [], []
    for i, p in enumerate(projects):
        a = -math.pi / 2 + i * 2 * math.pi / n
        r = 150 if i % 2 == 0 else 112
        x, y = 210 + r * math.cos(a), 210 + r * math.sin(a)
        pts.append((x, y))
        sz = 17 if i % 2 == 0 else 13
        petals = "".join(f'<circle cx="{sz / 2.5 * math.cos(k * math.pi / 3):.2f}" cy="{sz / 2.5 * math.sin(k * math.pi / 3):.2f}" r="{sz / 1.8:.2f}"/>' for k in range(6))
        ly = (sz / 1.8 + sz / 2.5) + 14
        tspans = "".join(f'<tspan x="0" dy="{0 if k == 0 else 11}">{html.escape(l)}</tspan>' for k, l in enumerate(label_lines(p["title"])))
        nodes.append(f'<a href="{html.escape(p["href"])}" aria-label="{html.escape(p["title"])}"><g class="node" transform="translate({x:.1f} {y:.1f})"><circle class="halo" r="{sz + 8}"/><g class="bloom">{petals}</g><circle r="1.6" class="core"/><text class="lbl" y="{ly:.0f}" text-anchor="middle">{tspans}</text></g></a>')
    for i in range(n):
        (x1, y1), (x2, y2) = pts[i], pts[(i + 1) % n]
        threads.append(f'<path d="M{x1:.1f} {y1:.1f} Q 210 210 {x2:.1f} {y2:.1f}"/>')
    for i in range(0, n, 3):
        (x1, y1), (x2, y2) = pts[i], pts[(i + 5) % n]
        threads.append(f'<path d="M{x1:.1f} {y1:.1f} Q 210 210 {x2:.1f} {y2:.1f}" opacity=".5"/>')
    return (f'<g class="threads" fill="none" stroke="var(--gold)" stroke-width=".7" opacity=".55">{"".join(threads)}</g>\n'
            f'        {render_phages()}\n'
            f'        <g class="nodes" fill="none" stroke="var(--gold)" stroke-width=".9">{"".join(nodes)}</g>')


def render_head(R=17):
    """An icosahedral capsid seen down its three-fold axis: hexagon, inner triangle, nine facet edges. Centered on the origin."""
    V = [(R * math.cos(math.radians(90 + 60 * k)), -R * math.sin(math.radians(90 + 60 * k))) for k in range(6)]
    T = [(0.5 * R * math.cos(math.radians(90 + 120 * j)), -0.5 * R * math.sin(math.radians(90 + 120 * j))) for j in range(3)]
    fmt = lambda pt: f"{pt[0]:.1f} {pt[1]:.1f}"
    hexagon = "M" + " L".join(fmt(v) for v in V) + " Z"
    tri = "M" + " L".join(fmt(t) for t in T) + " Z"
    edges = [(0, 0), (2, 1), (4, 2), (1, 0), (1, 1), (3, 1), (3, 2), (5, 2), (5, 0)]
    facets = "".join(f"M{fmt(V[a])} L{fmt(T[b])}" for a, b in edges)
    return f'<path class="head" d="{hexagon}"/><path d="{tri}"/><path d="{facets}" opacity=".8"/>'


def render_phage():
    """A bacteriophage, head centered on the origin, tail pointing down: capsid, collar, striated tail sheath, baseplate, six tail fibers."""
    R = 17
    y0 = R + 1
    sheath_top, sheath_len, w = y0 + 4, 24, 3.2
    stria = "".join(f"M{-w} {sheath_top + 4 + k * 4:.1f}H{w}" for k in range(5))
    base_y = sheath_top + sheath_len
    fibers = (f"M-5 {base_y + 2} C -11 {base_y + 6}, -13 {base_y + 10}, -15 {base_y + 17}"
              f"M-3 {base_y + 3} C -7 {base_y + 9}, -8 {base_y + 13}, -9 {base_y + 19}"
              f"M-1 {base_y + 3} C -2 {base_y + 10}, -3 {base_y + 14}, -3 {base_y + 20}"
              f"M5 {base_y + 2} C 11 {base_y + 6}, 13 {base_y + 10}, 15 {base_y + 17}"
              f"M3 {base_y + 3} C 7 {base_y + 9}, 8 {base_y + 13}, 9 {base_y + 19}"
              f"M1 {base_y + 3} C 2 {base_y + 10}, 3 {base_y + 14}, 3 {base_y + 20}")
    return (render_head(R)
            + f'<path d="M-4 {y0}H4V{y0 + 4}H-4Z"/>'
            + f'<path d="M{-w} {sheath_top}H{w}V{base_y}H{-w}Z"/><path d="{stria}" opacity=".7"/>'
            + f'<path d="M-6 {base_y}H6L7.5 {base_y + 3}H-7.5Z"/>'
            + f'<path d="{fibers}" stroke-linecap="round"/>')


def render_bacterium():
    """A rod-shaped bacterium with cilia: a capsule 36 x 13 with short wavy hairs all round, centered on the origin."""
    L, r = 36, 6.5
    body = f'<rect x="{-L / 2}" y="{-r}" width="{L}" height="{2 * r}" rx="{r}"/>'
    hairs = []
    n = 16
    for k in range(n):
        t = k / n
        # walk the capsule outline: two flat sides and two half-circles
        per = 2 * (L - 2 * r) + 2 * math.pi * r
        d = t * per
        if d < L - 2 * r: x, y, nx, ny = -L / 2 + r + d, -r, 0, -1
        elif d < L - 2 * r + math.pi * r:
            a = (d - (L - 2 * r)) / r; x, y = L / 2 - r + r * math.sin(a), -r * math.cos(a); nx, ny = math.sin(a), -math.cos(a)
        elif d < 2 * (L - 2 * r) + math.pi * r:
            e = d - (L - 2 * r + math.pi * r); x, y, nx, ny = L / 2 - r - e, r, 0, 1
        else:
            a = (d - (2 * (L - 2 * r) + math.pi * r)) / r; x, y = -L / 2 + r - r * math.sin(a), r * math.cos(a); nx, ny = -math.sin(a), math.cos(a)
        h = 6.5; px, py = -ny, nx                                    # a wave sideways along the hair
        hairs.append(f"M{x:.1f} {y:.1f} C {x + nx * h * .4 + px * 1.6:.1f} {y + ny * h * .4 + py * 1.6:.1f}, {x + nx * h * .7 - px * 1.6:.1f} {y + ny * h * .7 - py * 1.6:.1f}, {x + nx * h:.1f} {y + ny * h:.1f}")
    return body + f'<path d="{"".join(hairs)}" stroke-linecap="round" opacity=".8"/>'


def render_phages():
    """The hero's center: one phage floating, three bare capsids and a ciliated bacterium drifting beside it. Each outer group
    carries its resting place in data attributes; the inner group takes the pointer's nudge. The page's style floats them; its script eases them."""
    spec = [(210, 196, 1.0, 0, "main", render_phage()),
            (156, 160, .55, 12, "cap c1", render_head()),
            (270, 164, .42, -20, "cap c2", render_head()),
            (252, 268, .48, 30, "cap c3", render_head()),
            (160, 262, .85, -28, "bac", render_bacterium())]
    out = []
    for x, y, k, rot, cls, body in spec:
        out.append(f'<g class="phage {cls}" data-x="{x}" data-y="{y}" data-k="{k}" transform="translate({x} {y}) scale({k}) rotate({rot})"><g class="nudge"><g class="body">{body}</g></g></g>')
    return f'<g class="phages" fill="none" stroke="var(--gold)" stroke-width="1" stroke-linejoin="round">{"".join(out)}</g>'


def render_spotlight_data(data):
    sp = data["spotlight"]
    y, m, d = (int(v) for v in sp["anchor_date"].split("-"))
    P = [{"title": p["title"], "href": p["href"], "cta": p["cta"], "added": p.get("added")} for p in data["projects"]]
    return (f"const P = {json.dumps(P, ensure_ascii=False)};\n"
            f"      const SPOT = {{ anchor: Date.UTC({y}, {m - 1}, {d}), anchorTitle: {json.dumps(sp['anchor_title'])}, newDays: {int(sp.get('new_project_days', 3))} }};")


def render_fallback(data, when=None):
    p = pick(data, when or dt.date.today())
    return f'<span class="fl">Check out</span> <a href="{html.escape(p["href"])}">{html.escape(p["title"])}</a><span class="cta">{html.escape(p["cta"])}</span>'


def render_nodedata(projects):
    """The live loom's node list."""
    out = []
    for p in projects:
        phone = ", phone: true" if p.get("phone") else ""
        out.append(f'      {{ label: {json.dumps(p.get("short") or p["title"])}, link: {json.dumps(p["href"])}, hoverState: 0{phone} }},')
    return "\n".join(out)


# ── the Spotlight rule, in Python, for `check` and the prerendered line ──

def day_number(d):
    return (d - dt.date(1970, 1, 1)).days


def pick(data, d):
    sp = data["spotlight"]; P = data["projects"]
    day = day_number(d)
    fresh = []
    for p in P:
        if p.get("added"):
            age = day - day_number(dt.date.fromisoformat(p["added"]))
            if 0 <= age < int(sp.get("new_project_days", 3)):
                fresh.append(p)
    if fresh:
        return fresh[day % len(fresh)]
    a = next((i for i, p in enumerate(P) if p["title"] == sp["anchor_title"]), 0)
    delta = day - day_number(dt.date.fromisoformat(sp["anchor_date"]))
    return P[(a + delta) % len(P)]


# ── applying the markers ──

def between(text, start, end, new, required=False):
    pat = re.compile(re.escape(start) + r".*?" + re.escape(end), re.S)
    if not pat.search(text):
        if required:
            raise SystemExit(f"marker not found: {start}")
        return text, False
    return pat.sub(lambda m: start + "\n" + new + "\n" + end, text, count=1), True


def rebuild(page, data, when=None):
    text = page.read_text(encoding="utf-8")
    P = data["projects"]; touched = []
    live = 'class="project"' in text and 'class="card"' not in text
    cards = render_cards_live(P) if live else render_cards_b(P)
    text, ok = between(text, "<!-- projects:start -->", "<!-- projects:end -->", cards); touched += ["grid"] if ok else []
    text, ok = between(text, "<!-- constellation:start -->", "<!-- constellation:end -->", "        " + render_constellation(P)); touched += ["constellation"] if ok else []
    text, ok = between(text, "<!-- spotlight-fallback:start -->", "<!-- spotlight-fallback:end -->", render_fallback(data, when)); touched += ["spotlight line"] if ok else []
    text, ok = between(text, "/* spotlight:start */", "/* spotlight:end */", "      " + render_spotlight_data(data)); touched += ["spotlight data"] if ok else []
    text, ok = between(text, "// nodeData:start", "// nodeData:end", render_nodedata(P)); touched += ["nodeData"] if ok else []
    if touched:
        page.write_text(text, encoding="utf-8")
    return touched


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--file", help="rebuild this page only")
    sub = ap.add_subparsers(dest="cmd")
    a = sub.add_parser("add", help="append a project and rebuild")
    a.add_argument("--title", required=True); a.add_argument("--href", required=True); a.add_argument("--blurb", required=True)
    a.add_argument("--go", required=True, help='call-to-action label, e.g. "Open atlas"'); a.add_argument("--cta", required=True, help="one-sentence invitation for the Spotlight line")
    a.add_argument("--icon", help="an SVG file for the card icon (48x48 viewBox, strokes in currentColor); a generic bloom is used if omitted")
    a.add_argument("--short", help="short name for the live loom's label"); a.add_argument("--phone", action="store_true", help="show in the live loom's six-node phone layout")
    a.add_argument("--added", help="date added, YYYY-MM-DD (default: today, UTC)")
    c = sub.add_parser("check", help="show the Spotlight pick for a date and the fortnight after"); c.add_argument("date", nargs="?")
    args = ap.parse_args(argv)
    data = load()

    if args.cmd == "add":
        if any(p["title"].lower() == args.title.lower() for p in data["projects"]):
            raise SystemExit(f"a project titled {args.title!r} already exists")
        if args.icon:
            icon = pathlib.Path(args.icon).read_text(encoding="utf-8").strip()
            if "<svg" not in icon:
                raise SystemExit("--icon must be an SVG file")
            icon = re.sub(r"<svg\b", '<svg class="ico"', icon, count=1) if 'class="ico"' not in icon else icon
        else:
            icon = ('<svg class="ico" viewBox="0 0 48 48" fill="none" stroke="currentColor" stroke-width="1.4" aria-hidden="true">'
                    + "".join(f'<circle cx="{24 + 6.8 * math.cos(k * math.pi / 3):.1f}" cy="{24 + 6.8 * math.sin(k * math.pi / 3):.1f}" r="9.4"/>' for k in range(6))
                    + '<circle cx="24" cy="24" r="1.6" fill="currentColor"/></svg>')
        data["projects"].append({"title": args.title, "href": args.href, "blurb": args.blurb, "go": args.go, "cta": args.cta,
                                 "short": args.short or args.title, "phone": bool(args.phone), "icon": icon,
                                 "added": args.added or dt.datetime.now(dt.timezone.utc).date().isoformat()})
        save(data)
        print(f"added {args.title!r}; the docket now has {len(data['projects'])} projects")

    if args.cmd == "check":
        d0 = dt.date.fromisoformat(args.date) if args.date else dt.datetime.now(dt.timezone.utc).date()
        for k in range(15):
            d = d0 + dt.timedelta(days=k)
            print(f"{d}  {pick(data, d)['title']}")
        return

    pages = [pathlib.Path(args.file)] if args.file else PAGES
    for page in pages:
        if not page.exists():
            continue
        touched = rebuild(page, data)
        print(f"{page.relative_to(ROOT) if page.is_relative_to(ROOT) else page}: {', '.join(touched) if touched else 'no markers, left alone'}")


if __name__ == "__main__":
    main(sys.argv[1:])
