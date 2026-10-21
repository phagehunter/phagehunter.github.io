# Photographs

The photography section of curtishoffmann.com is driven by `manifest.json` and the files in `web/`. Nothing here is hand-edited except captions.

## Adding photographs

1. Drop the pictures (JPEG, PNG, WebP, TIFF; convert HEIC to JPEG first, Preview does it with File → Export) into `photos/inbox/`. That folder is ignored by git, so originals cannot be pushed by mistake.
2. Double-click `Add photos.command` in the repository root. It cleans every file, shows what it wrote, and asks before committing and pushing. The site updates about a minute after the push.
3. When there is time, open `manifest.json` and fill in `caption` (shown under the image) and `alt` (read by screen readers and search engines) for each entry. Both are optional; an entry with an empty caption shows no caption.

The same thing from a terminal:

```bash
python3 photos/add.py          # add --mark to burn a faint copyright line into the corner
```

## What the script does to each file

- Applies the orientation flag, then converts the colors to sRGB using the embedded profile.
- Rebuilds the image from pixels only. EXIF (GPS, camera, serial number, dates, lens), XMP, IPTC, embedded thumbnails, comments and the color profile are all gone.
- Writes a 1600 px WebP for display, a 480 px thumbnail and a JPEG fallback, named by a hash of the pixels, so the original file name (which can carry a date or a device name) is not published either.
- Re-reads everything it wrote and stops with an error if any metadata block is still present.
- Moves the original into `photos/inbox/done/` (also ignored).

`check.py` is the scanner. It runs again on GitHub for every push that touches `photos/` (`.github/workflows/photo-guard.yml`) and fails the check if a file with metadata, or anything under `inbox/`, has been committed.

## Why the GitHub web uploader is not the way in

A file pushed to GitHub stays in the repository's history even after it is deleted, and this repository does not rewrite history. Metadata has to be removed before the push, which is what the script is for. If a photo ever does get committed with its metadata, treat the location as public and remove the file in a new commit anyway.

## Removing a photograph

Delete its three files from `web/` and its entry from `manifest.json`, then commit.
