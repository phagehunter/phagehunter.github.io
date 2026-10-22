#!/usr/bin/env python3
"""Prepare photographs for the site: strip metadata, resize, hash, update the manifest.

    python3 photos/add.py              # process everything in photos/inbox/
    python3 photos/add.py --mark       # also burn a faint copyright mark in a corner
    python3 photos/add.py a.jpg b.jpg  # process specific files instead of the inbox

For each image the script
  1. applies the EXIF orientation, so nothing comes out sideways;
  2. converts the colors to sRGB (using the embedded profile when there is one)
     and then rebuilds the image from pixels only, which drops EXIF (GPS,
     camera serial, dates, lens), XMP, IPTC, thumbnails, comments and the
     profile itself;
  3. writes photos/web/<hash>.webp (1600 px long edge), <hash>-t.webp (480 px
     thumbnail) and <hash>.jpg (fallback), named by a hash of the pixels, never
     by the original file name;
  4. adds an entry to photos/manifest.json with the size, a dominant color for
     the blur-up placeholder, and empty "caption" and "alt" fields to fill in;
  5. re-reads every file it wrote and refuses to finish if any metadata remains;
  6. moves the original into photos/inbox/done/ (ignored by git).

Needs Pillow (python3 -c "import PIL" should work). Standard library otherwise.
"""
import datetime
import hashlib
import io
import json
import pathlib
import shutil
import sys

try:
    from PIL import Image, ImageCms, ImageDraw, ImageFont, ImageOps
except ImportError:
    sys.exit("Pillow is not installed. Install it once with: python3 -m pip install --user pillow")

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import check  # noqa: E402  (photos/check.py, metadata scanner)

ROOT = pathlib.Path(__file__).resolve().parent
INBOX, DONE, WEB = ROOT / "inbox", ROOT / "inbox" / "done", ROOT / "web"
MANIFEST = ROOT / "manifest.json"
LONG_EDGE, THUMB_EDGE = 1600, 480
WEBP_QUALITY, JPEG_QUALITY = 82, 84
SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff", ".heic"}
MARK_TEXT = "© Curtis Hoffmann"
Image.MAX_IMAGE_PIXELS = 120_000_000


def load_manifest():
    if MANIFEST.exists():
        return json.loads(MANIFEST.read_text(encoding="utf-8"))
    return {"photos": []}


def to_srgb(img):
    """Return an RGB image in sRGB with no metadata attached."""
    img = ImageOps.exif_transpose(img)
    icc = img.info.get("icc_profile")
    if img.mode not in ("RGB", "RGBA"):
        img = img.convert("RGBA" if "A" in img.mode or img.mode == "P" else "RGB")
    if icc:
        try:
            src = ImageCms.ImageCmsProfile(io.BytesIO(icc))
            img = ImageCms.profileToProfile(img, src, ImageCms.createProfile("sRGB"), outputMode=img.mode)
        except Exception as e:  # a broken profile should not stop the export
            print(f"   note: embedded color profile ignored ({e})")
    if img.mode == "RGBA":  # flatten onto the site's midnight so transparent PNGs look intended
        bg = Image.new("RGB", img.size, (0, 11, 24))
        bg.paste(img, mask=img.split()[3])
        img = bg
    clean = Image.frombytes("RGB", img.size, img.tobytes())  # pixels only: no info dict at all
    return clean


def resized(img, edge):
    out = img.copy()
    out.thumbnail((edge, edge), Image.LANCZOS)
    return out


def dominant_color(img):
    r, g, b = img.resize((1, 1), Image.BOX).getpixel((0, 0))
    return f"#{r:02x}{g:02x}{b:02x}"


def mark(img):
    """Burn a faint copyright line into the lower-right corner."""
    size = max(14, img.width // 60)
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Georgia.ttf", size)
    except OSError:
        font = ImageFont.load_default(size)
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    x0, y0, x1, y1 = d.textbbox((0, 0), MARK_TEXT, font=font)
    pad = size
    d.text((img.width - (x1 - x0) - pad, img.height - (y1 - y0) - pad), MARK_TEXT, font=font, fill=(255, 255, 255, 56))
    out = Image.alpha_composite(img.convert("RGBA"), layer).convert("RGB")
    return Image.frombytes("RGB", out.size, out.tobytes())


def process(path, manifest, burn_mark):
    print(f"-> {path.name}")
    with Image.open(path) as raw:
        img = to_srgb(raw)
    display = resized(img, LONG_EDGE)
    if burn_mark:
        display = mark(display)
    digest = hashlib.sha256(display.tobytes()).hexdigest()[:10]
    pid = f"p-{digest}"
    if any(p["id"] == pid for p in manifest["photos"]):
        print("   already in the manifest, skipped")
        return []
    thumb = resized(display, THUMB_EDGE)
    WEB.mkdir(parents=True, exist_ok=True)
    files = [WEB / f"{pid}.webp", WEB / f"{pid}-t.webp", WEB / f"{pid}.jpg"]
    display.save(files[0], "WEBP", quality=WEBP_QUALITY, method=6)
    thumb.save(files[1], "WEBP", quality=74, method=6)
    display.save(files[2], "JPEG", quality=JPEG_QUALITY, optimize=True, progressive=True)
    manifest["photos"].append({
        "id": pid, "src": f"photos/web/{pid}.webp", "thumb": f"photos/web/{pid}-t.webp",
        "fallback": f"photos/web/{pid}.jpg", "w": display.width, "h": display.height,
        "color": dominant_color(display), "caption": "", "alt": "",
        "added": datetime.date.today().isoformat()})
    kb = {p.name: p.stat().st_size // 1024 for p in files}
    print(f"   {display.width}x{display.height}, " + ", ".join(f"{n} {k} KB" for n, k in kb.items()))
    return list(files)


def main(argv):
    burn_mark = "--mark" in argv
    args = [a for a in argv[1:] if not a.startswith("--")]
    if args:
        sources = [pathlib.Path(a) for a in args]
    else:
        INBOX.mkdir(exist_ok=True)
        sources = sorted(p for p in INBOX.iterdir() if p.suffix.lower() in SUFFIXES and p.is_file())
    if not sources:
        print(f"Nothing to do: put photographs in {INBOX} and run again.")
        return 0
    manifest = load_manifest()
    written, failed = [], []
    for src in sources:
        try:
            written += process(src, manifest, burn_mark)
        except Exception as e:
            failed.append((src.name, str(e)))
            print(f"   failed: {e}")
    MANIFEST.write_text(json.dumps(manifest, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    # verification pass: nothing leaves this script unchecked
    leftovers = {str(p): check.findings(p) for p in written}
    leftovers = {k: v for k, v in leftovers.items() if v}
    if leftovers:
        for k, v in leftovers.items():
            print(f"METADATA LEFT in {k}: {', '.join(v)}")
        print("Stopped: the files above were NOT cleaned. Do not commit photos/web until this is fixed.")
        return 2
    print(f"verified: {len(written)} files, no EXIF, XMP, IPTC, ICC or comment blocks")
    if not args:
        DONE.mkdir(exist_ok=True)
        for src in sources:
            if src.name not in dict(failed):
                shutil.move(str(src), str(DONE / src.name))
        print(f"originals moved to {DONE} (ignored by git)")
    print(f"manifest: {len(manifest['photos'])} photographs. Fill in caption and alt in {MANIFEST.name} when ready.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
