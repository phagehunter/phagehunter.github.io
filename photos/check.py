#!/usr/bin/env python3
"""Report any metadata left inside image files. Standard library only.

    python3 photos/check.py photos/web            # scan a folder
    python3 photos/check.py some.jpg other.webp   # scan files

Exit status 1 if any file still carries EXIF, XMP, IPTC, an ICC profile or a
comment block. Used by add.py after every export and by the photo-guard
GitHub Action on every push that touches photos/.
"""
import pathlib
import struct
import sys

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".webp", ".png"}


def jpeg_blocks(data):
    """Yield (marker, payload) for every APPn/COM segment before the scan data."""
    i = 2
    while i + 4 <= len(data):
        if data[i] != 0xFF:
            i += 1
            continue
        marker = data[i + 1]
        if marker in (0xD8, 0x01) or 0xD0 <= marker <= 0xD7:
            i += 2
            continue
        if marker == 0xDA:  # start of scan: metadata segments end here
            return
        length = struct.unpack(">H", data[i + 2:i + 4])[0]
        yield marker, data[i + 4:i + 2 + length]
        i += 2 + length


def findings_jpeg(data):
    out = []
    for marker, payload in jpeg_blocks(data):
        head = payload[:32]
        if marker == 0xE1 and head.startswith(b"Exif"):
            out.append("EXIF segment (APP1)")
        elif marker == 0xE1 and b"ns.adobe.com/xap" in head:
            out.append("XMP segment (APP1)")
        elif marker == 0xE2 and head.startswith(b"ICC_PROFILE"):
            out.append("ICC profile (APP2)")
        elif marker == 0xED and head.startswith(b"Photoshop"):
            out.append("IPTC/Photoshop segment (APP13)")
        elif marker == 0xFE:
            out.append("comment block (COM)")
        elif 0xE0 < marker <= 0xEF and marker != 0xE0:
            out.append(f"application segment APP{marker - 0xE0}")
    return out


def findings_webp(data):
    out = []
    if data[:4] != b"RIFF" or data[8:12] != b"WEBP":
        return ["not a WebP file"]
    i = 12
    while i + 8 <= len(data):
        fourcc = data[i:i + 4]
        size = struct.unpack("<I", data[i + 4:i + 8])[0]
        if fourcc == b"EXIF":
            out.append("EXIF chunk")
        elif fourcc == b"XMP ":
            out.append("XMP chunk")
        elif fourcc == b"ICCP":
            out.append("ICC profile chunk")
        i += 8 + size + (size & 1)
    return out


def findings_png(data):
    out = []
    i = 8
    while i + 8 <= len(data):
        size = struct.unpack(">I", data[i:i + 4])[0]
        ctype = data[i + 4:i + 8]
        payload = data[i + 8:i + 8 + size]
        if ctype == b"eXIf":
            out.append("eXIf chunk")
        elif ctype == b"iCCP":
            out.append("ICC profile chunk")
        elif ctype in (b"tEXt", b"zTXt", b"iTXt"):
            key = payload.split(b"\0", 1)[0].decode("latin-1", "replace")
            out.append(f"text chunk {ctype.decode()} ({key})")
        elif ctype == b"tIME":
            out.append("tIME chunk")
        i += 12 + size
    return out


def findings(path):
    data = pathlib.Path(path).read_bytes()
    if data[:2] == b"\xff\xd8":
        return findings_jpeg(data)
    if data[:4] == b"RIFF":
        return findings_webp(data)
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return findings_png(data)
    return ["unknown file type"]


def main(argv):
    targets = []
    for a in argv[1:] or ["photos/web"]:
        p = pathlib.Path(a)
        if p.is_dir():
            targets += sorted(x for x in p.rglob("*") if x.suffix.lower() in IMAGE_SUFFIXES)
        elif p.is_file():
            targets.append(p)
        else:
            print(f"ok   {p}: nothing to scan (does not exist yet)")
    bad = 0
    for p in targets:
        f = findings(p)
        print(f"{'FAIL' if f else 'ok  '} {p}" + (": " + ", ".join(f) if f else ""))
        bad += bool(f)
    print(f"{len(targets)} files scanned, {bad} with metadata")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
