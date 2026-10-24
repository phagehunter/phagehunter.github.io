# curtishoffmann.com

The landing page for Curtis Hoffmann's site, served from this repository by GitHub Pages with a custom domain. Every project linked from it lives in its own repository and is published under the same domain (for example `curtishoffmann.com/humanevolution/` comes from the `humanevolution` repository).

## What is here

```
index.html          the whole page: hero constellation, daily pick, project grid, about with fellowships and education, contact form, bookmarks
CNAME               custom domain for GitHub Pages
site.webmanifest    name, colors and icons for home-screen installs
favicon.svg, favicon-32.png, apple-touch-icon.png, icon-192.png, icon-512.png
og-image.jpg        1200×630 social preview
symphony.mp3        optional background music; only downloaded if a visitor turns sound on
robots.txt, sitemap.xml, llms.txt
data/projects.json, build_projects.py     the project docket: grid, hero constellation and daily pick (see below)
data/bookmarks.json, build_bookmarks.py   the Bookmarks section (see below)
photos/                                   the photography pipeline; not shown on the current page (see below)
```

There is no build step and no dependency. Edit `index.html`, commit, and GitHub Pages publishes it within a minute or two.

## The hero

The right half of the hero is a constellation drawn in SVG: twelve blooms, one per project, joined by arched threads around a floating bacteriophage and a few smaller microbes. Hovering a bloom lights it and shows the project's name; clicking opens the project. The threads at the foot of the page are the loom from the previous design, drawn on a `<canvas>`; the pointer parts them. The project grid carries the same links as ordinary anchors, so the drawings are decoration rather than the only way in, and the page works without JavaScript or with reduced motion.

Under the hero buttons, "Check out" names one project a day: the UTC day number walks the docket in order from an anchor date, so every visitor sees the same pick on a given day, and a newly added project takes the pick for its first three days.

Faint geometric viruses float behind the Projects, About and Bookmarks bands. They drift away from the pointer and can be dragged with a mouse or pen. Drop one onto another in the same band and the two reassort, the way influenza does: both split into eight RNA segments, the segments gather, and eight of them, four from each parent, reassemble into a new design in a new color. The new virus is a shadow like any other and can be reassorted again. All of this is plain JavaScript in the page; nothing is loaded.

## Adding a project

The grid, the constellation and the daily pick are all generated from `data/projects.json` by `build_projects.py`, which rewrites the blocks between the `projects`, `constellation`, `spotlight` and `spotlight-fallback` markers in `index.html`. One command adds a project and rebuilds everything:

```
python3 build_projects.py add --title "Name" --href https://curtishoffmann.com/name/ --blurb "What it is." --go "Open atlas" --cta "One-sentence invitation." --icon name.svg
```

`python3 build_projects.py` alone rebuilds from the JSON; `python3 build_projects.py check` prints the coming picks. Two things are still by hand: add the URL to `sitemap.xml` and to the `ItemList` in the JSON-LD block in the head. Links should use `https://curtishoffmann.com/...` rather than `phagehunter.github.io/...` so visitors are not bounced through a redirect.

## Contact form

The Contact section posts to StaticForms, a hosted form endpoint, so the page can take messages without a server. The form's key is the hidden `apiKey` field in `index.html`; it is a public form key, not an account credential, and can be regenerated in the StaticForms dashboard. The page posts the form in the background and reports under the Send button, so visitors stay on the page; if that request cannot be made at all, the form falls back to an ordinary post, which lands on the service's own page. The dashboard also offers a domain restriction and a honeypot, both worth turning on.

## Hosting notes

The domain is proxied through Cloudflare, so Cloudflare terminates HTTPS. "Enforce HTTPS" in the Pages settings does take effect on the project repositories (those that have it on redirect plain `http://` to `https://`), but this root repository, which carries the custom-domain record, may refuse it until GitHub sees a certificate. The fallback is "Always Use HTTPS" in the Cloudflare dashboard (SSL/TLS → Edge Certificates), with the encryption mode on "Full".

## Photography

The current page has no Photography section. The pipeline is kept for when it returns: drop originals into `photos/inbox/` (ignored by git) and double-click `Add photos.command`; it strips every trace of metadata (GPS, camera, dates, XMP, color profile), writes hashed WebP and JPEG copies into `photos/web/`, updates `photos/manifest.json`, and offers to commit and push. A GitHub Action re-scans every push that touches the folder and fails if metadata or an original slipped through. Details in [photos/README.md](photos/README.md).

## Bookmarks

The Bookmarks section is generated from `data/bookmarks.json` by `build_bookmarks.py`, which rewrites the block between the `bookmarks:start` and `bookmarks:end` markers in `index.html`: one dropdown per collection, whose panel is a sideways strip of link tiles. Add or remove a link in the JSON, run the script, commit both files.
