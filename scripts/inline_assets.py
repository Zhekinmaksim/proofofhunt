"""
Make each page a single self-contained file.

Pages used to load their fonts from web/fonts/ and the play view loaded its map
from web/brand/course.svg. That is correct for a deployed site and wrong for
everything else: open index.html on its own, from a download or an email, and
the fonts silently fall back to a wider system face. The headline then sets in
four lines instead of two and the title block overflows the hero. That
happened, which is why this script exists.

So the fonts are embedded as data URIs and the play view's map is embedded as
inline SVG. web/fonts/ stays the source of truth: edit or replace a woff2 there
and re-run this.

    python3 scripts/inline_assets.py

Idempotent. It finds each @font-face by family name and rewrites its src,
whether that src is currently a file path or an earlier data URI.
"""

import base64
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

FONTS = {
    "Sofia Sans Extra Condensed": "sofia-sans-extra-condensed.woff2",
    "Sofia Sans": "sofia-sans.woff2",
    "Martian Mono": "martian-mono.woff2",
}
PAGES = ["web/index.html", "web/play.html"]


def data_uri(name):
    with open(os.path.join(ROOT, "web", "fonts", name), "rb") as f:
        return "data:font/woff2;base64," + base64.b64encode(f.read()).decode()


def embed_fonts(html):
    for family, file in FONTS.items():
        # match this family's @font-face exactly, so "Sofia Sans" does not also
        # catch "Sofia Sans Extra Condensed"
        pat = re.compile(
            r'(@font-face\{font-family:"' + re.escape(family) + r'";\s*src:url\()'
            r'("[^"]*"|[^)]*)'
            r'(\))'
        )
        html, n = pat.subn(lambda m: m.group(1) + '"' + data_uri(file) + '"' + m.group(3), html)
        if n != 1:
            raise SystemExit(f"expected one @font-face for {family!r}, found {n}")
    # Preloading a file that is now embedded would 404 when the page is opened
    # on its own, and buys nothing when it is not.
    html = re.sub(r'<link rel="preload" href="fonts/[^"]*"[^>]*>\n?', "", html)
    return html


def embed_play_map(html):
    import course as C
    svg = C.svg(cleared=1, locked_opacity=".72")
    svg = svg.replace("<svg ", '<svg class="sheet-svg" ', 1)
    # an <img> pointing at the file, or a previously embedded copy
    html, n = re.subn(r'<img src="brand/course\.svg"[^>]*>', svg, html)
    if n == 0:
        html, n = re.subn(r'<svg class="sheet-svg".*?</svg>', lambda m: svg, html, flags=re.S)
    return html


def main():
    for rel in PAGES:
        path = os.path.join(ROOT, rel)
        html = open(path).read()
        html = embed_fonts(html)
        if rel.endswith("play.html"):
            html = embed_play_map(html)
        open(path, "w").write(html)
        left = re.findall(r'url\("fonts/|src="brand/course', html)
        print(f"{rel}: {len(html) // 1024} KB, external font or map refs left: {len(left)}")


if __name__ == "__main__":
    main()
