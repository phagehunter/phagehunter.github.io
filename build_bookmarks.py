#!/usr/bin/env python3
"""Regenerate the Bookmarks section of index.html from data/bookmarks.json.

    python3 build_bookmarks.py

The generated markup sits between <!-- bookmarks:start --> and <!-- bookmarks:end -->: one <details> per collection,
whose panel is a sideways strip of link tiles with its own arrow buttons. Everything else in index.html is left alone.
"""
import html
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent
data = json.loads((ROOT / "data" / "bookmarks.json").read_text(encoding="utf-8"))
links = data["links"]
arrows = ('<div class="bm-strip-head"><button type="button" data-dir="-1" aria-label="Previous links"><svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M15 6l-6 6 6 6"/></svg></button>'
          '<button type="button" data-dir="1" aria-label="Next links"><svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M9 6l6 6-6 6"/></svg></button></div>')
parts = []
for g in data["groups"]:
    items = [b for b in links if b["group"] == g]
    if not items:
        continue
    pid = "bm-" + re.sub(r"[^a-z0-9]+", "-", g.lower()).strip("-")
    lis = "".join(f'<li><a href="{html.escape(b["url"])}" rel="noopener"><span class="t">{html.escape(b["name"])}</span><span class="d">{html.escape(b["domain"])}</span></a></li>' for b in items)
    parts.append(f'''<details class="bm-group" id="{pid}">
  <summary><span class="g">{html.escape(g)}</span><span class="n" data-total="{len(items)}">{len(items)}</span></summary>
  <div class="bm-strip-wrap">{arrows}<ul class="bm-list bm-strip" tabindex="0" aria-label="{html.escape(g)}, scroll sideways">{lis}</ul></div>
</details>''')
block = "\n".join(parts)
page = (ROOT / "index.html").read_text(encoding="utf-8")
new, n = re.subn(r"(<!-- bookmarks:start -->).*?(<!-- bookmarks:end -->)", lambda m: m.group(1) + "\n" + block + "\n" + m.group(2), page, flags=re.S)
assert n == 1, "markers not found in index.html"
(ROOT / "index.html").write_text(new, encoding="utf-8")
print(f"bookmarks: {len(links)} links in {len(parts)} groups written into index.html")
