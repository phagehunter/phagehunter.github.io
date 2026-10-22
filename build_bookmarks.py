#!/usr/bin/env python3
"""Regenerate the Bookmarks section of index.html from data/bookmarks.json.

    python3 build_bookmarks.py

The generated markup sits between <!-- bookmarks:start --> and <!-- bookmarks:end -->.
Everything else in index.html is left alone.
"""
import html
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent
data = json.loads((ROOT / "data" / "bookmarks.json").read_text(encoding="utf-8"))
links = data["links"]
chevron = '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M6 9l6 6 6-6"/></svg>'
parts = []
for i, g in enumerate(data["groups"]):
    items = [b for b in links if b["group"] == g]
    if not items:
        continue
    pid = "bm-" + re.sub(r"[^a-z0-9]+", "-", g.lower()).strip("-")
    lis = "".join(f'<li><a href="{html.escape(b["url"])}" rel="noopener"><span class="t">{html.escape(b["name"])}</span><span class="d">{html.escape(b["domain"])}</span></a></li>' for b in items)
    parts.append(f'''        <div class="bm-group">
          <h3><button class="bm-toggle" type="button" aria-expanded="{"true" if i == 0 else "false"}" aria-controls="{pid}"><span>{html.escape(g)}</span><span class="n" data-total="{len(items)}">{len(items)}</span>{chevron}</button></h3>
          <div class="bm-panel" id="{pid}"><div><ul class="bm-list">{lis}</ul></div></div>
        </div>''')
block = "\n".join(parts)
page = (ROOT / "index.html").read_text(encoding="utf-8")
new, n = re.subn(r"(<!-- bookmarks:start -->).*?(<!-- bookmarks:end -->)", lambda m: m.group(1) + "\n" + block + "\n        " + m.group(2), page, flags=re.S)
assert n == 1, "markers not found in index.html"
(ROOT / "index.html").write_text(new, encoding="utf-8")
print(f"bookmarks: {len(links)} links in {len(parts)} groups written into index.html")
