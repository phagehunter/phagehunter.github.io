# curtishoffmann.com

The landing page for Curtis Hoffmann's site, served from this repository by GitHub Pages with a custom domain. Every project linked from it lives in its own repository and is published under the same domain (for example `curtishoffmann.com/humanevolution/` comes from the `humanevolution` repository).

## What is here

```
index.html          the whole page: hero loom, project grid, bio, contact
CNAME               custom domain for GitHub Pages
site.webmanifest    name, colors and icons for home-screen installs
favicon.svg, favicon-32.png, apple-touch-icon.png, icon-192.png, icon-512.png
og-image.jpg        1200×630 social preview
symphony.mp3        optional background music; only downloaded if a visitor turns sound on
robots.txt, sitemap.xml
```

There is no build step and no dependency. Edit `index.html`, commit, and GitHub Pages publishes it within a minute or two.

## The loom

The animated threads at the top are drawn on a `<canvas>`. On a desktop, moving the pointer over them opens a constellation of eight nodes that link to the projects and profiles; on a phone, tapping does the same. The visible project grid underneath carries the same links as ordinary anchors, so the canvas is decoration rather than the only way in, and the page works without JavaScript or with reduced motion.

## Adding a project

1. Add a card to the grid in `index.html` (copy one of the existing `<a class="project">` blocks and change the title, blurb and link).
2. Add the same link to the `nodeData` list in the script so it appears in the loom.
3. Add the URL to `sitemap.xml` and to the `ItemList` in the JSON-LD block in the head.

Links should use `https://curtishoffmann.com/...` rather than `phagehunter.github.io/...` so visitors are not bounced through a redirect.

## Hosting notes

The domain is proxied through Cloudflare, so Cloudflare terminates HTTPS. GitHub cannot issue its own certificate while that is the case, which is why "Enforce HTTPS" is unavailable in the Pages settings. To make plain `http://` requests redirect, turn on "Always Use HTTPS" in the Cloudflare dashboard (SSL/TLS → Edge Certificates) and keep the encryption mode on "Full".
