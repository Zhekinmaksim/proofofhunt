"""Generate the route/check H mark, site headers, favicons and social card.

The single silhouette combines Hunt's H with a descending then rising course
leg: a check made by completing the route. Geometry lives in mark.geometry.json
and is also imported by the video. Run from the repository root:

    pip install -r scripts/requirements-brand.txt
    python3 scripts/make_brand.py
"""

import io
import os
import json
from functools import lru_cache
from pathlib import Path
import struct
import sys
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import course as C

OUT = "web/brand"
# Use the licensed, checked-in web fonts; never depend on host font settings.
FONTS = Path(os.environ.get("POH_FONTS", "web/fonts"))
FONT_FILES = {
    "SofiaSansExtraCondensed": "sofia-sans-extra-condensed",
    "SofiaSans": "sofia-sans",
    "MartianMono": "martian-mono",
}
GEOMETRY = json.loads(Path(f"{OUT}/mark.geometry.json").read_text())
# ISOM paper colours: purple course, yellow open land, brown contours.
PAPER = (255, 255, 255)
WASH = (255, 196, 46)        # ISOM open land, the brand field
INK = (20, 20, 15)
INK_SOFT = (110, 112, 101)
OVERPRINT = (213, 0, 109)    # the course
CONTOUR = (164, 98, 42)
WATER = (0, 146, 212)
RULE = (194, 195, 185)
VEG = (171, 218, 168)

SS = 4  # supersampling factor


@lru_cache(maxsize=3)
def font_bytes(name):
    from fontTools.ttLib import TTFont
    path = FONTS / f"{name}.ttf"
    if not path.exists():
        path = FONTS / f"{FONT_FILES[name]}.woff2"
    face = TTFont(path)
    face.flavor = None
    buf = io.BytesIO()
    face.save(buf)
    return buf.getvalue()


def font(name, size, wght=400, wdth=None):
    face = ImageFont.truetype(io.BytesIO(font_bytes(name)), size)
    if face.get_variation_axes():
        axes = [wght if axis["name"] == b"Weight" else
                (wdth if wdth is not None else axis["default"])
                for axis in face.get_variation_axes()]
        face.set_variation_by_axes(axes)
    return face


def mark_svg(color="#d5006d", label=True):
    accessibility = ' role="img" aria-label="Proof of Hunt"' if label else ''
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{GEOMETRY["viewBox"]}" '
            f'width="32" height="32"{accessibility}>'
            f'<path fill="{color}" d="{GEOMETRY["path"]}"/></svg>\n')


def mark_image(size, bg=None, color="#d5006d", pad=0):
    import cairosvg
    inset = round(size * pad)
    extent = size - inset * 2
    data = cairosvg.svg2png(bytestring=mark_svg(color).encode(),
                           output_width=extent * SS, output_height=extent * SS)
    mark = Image.open(io.BytesIO(data)).convert("RGBA")
    image = Image.new("RGBA", (size * SS, size * SS), bg or (0, 0, 0, 0))
    image.alpha_composite(mark, (inset * SS, inset * SS))
    return image.resize((size, size), Image.Resampling.LANCZOS)


# ---------------------------------------------------------------------------
# OG image
# ---------------------------------------------------------------------------

def course_png(width, height):
    """
    Rasterise the shared course artwork for the social card.

    The map on the page and the map on the card are the same SVG rendered
    twice, not two drawings that happen to resemble each other. Anything else
    guarantees they drift apart the first time either is touched.

    Needs cairosvg, which is a build dependency only. Nothing at runtime and
    nothing on chain depends on it.
    """
    import cairosvg

    svg = C.svg(cleared=1, locked_opacity=".72")
    # The course module now emits literal ISOM hexes, so nothing is substituted
    # here. That is deliberate: a shared graphic that depends on the host page
    # defining the right CSS variables breaks silently, and did once.
    # The page styles the control numbers in CSS, so a standalone render has to
    # carry that type itself.
    svg = svg.replace(
        'class="ctrl-n" ',
        'font-family="Martian Mono" font-size="12" font-weight="600" ',
    )
    buf = cairosvg.svg2png(
        bytestring=svg.encode(), output_width=width, output_height=height
    )
    return Image.open(io.BytesIO(buf)).convert("RGBA")


def make_og(path, W=1200, H=630):
    im = Image.new("RGB", (W * 2, H * 2), PAPER)
    d = ImageDraw.Draw(im)
    w, h = W * 2, H * 2

    # ---- right hand panel: the course, on map wash ----------------------
    # The field is landscape and the panel is portrait, so the artwork is fitted
    # to the panel width and centred vertically. Filling the panel instead would
    # crop a third of the course off the edge, which on a map means losing
    # controls - the one thing this picture exists to show.
    px0 = int(w * 0.52)
    d.rectangle([px0, 0, w, h], fill=WASH)
    d.line([px0, 0, px0, h], fill=RULE, width=2)

    fw, fh = C.FIELD
    cw = w - px0
    ch = int(fh * (cw / fw))
    art = course_png(cw, ch)
    top = (h - ch) // 2
    im.paste(art, (px0, top), art)
    # The map is fitted to the panel width, so yellow shows above and below it.
    # A rule around the sheet turns that from a gap into a map laid on the open
    # ground, which is what the yellow is.
    d.rectangle([px0, top, w - 1, top + ch], outline=INK, width=3)

    # ---- left hand column -------------------------------------------------
    M = 96
    mk = mark_image(76)
    im.paste(mk, (M, 82), mk)
    d.text((M + 96, 120), "PROOF OF HUNT",
           font=font("SofiaSansExtraCondensed", 50, 800), fill=INK, anchor="lm")

    # Condensed capitals, as on the page. The size is fitted to the column
    # rather than chosen, because a fixed size that suits one face overruns
    # with the next: the first render of this card put the full stop of
    # "STORED." across the divider and onto the map.
    col = int(w * 0.52) - M - 40          # left column width, with a margin
    lines = ("TWELVE CLUES. NO", "ANSWER KEY IS STORED.")
    size = 210
    while size > 80:
        head = font("SofiaSansExtraCondensed", size, 800)
        if max(d.textlength(t, font=head) for t in lines) <= col:
            break
        size -= 4
    lead = int(size * 0.9)
    y = 236
    d.text((M, y), lines[0], font=head, fill=INK)
    y += lead
    d.text((M, y), "ANSWER KEY IS ", font=head, fill=INK)
    wid = d.textlength("ANSWER KEY IS ", font=head)
    d.text((M + wid, y), "STORED.", font=head, fill=OVERPRINT)
    y += size + 34

    sub = font("SofiaSans", 36, 400)
    d.text((M, y),
           "The answers are somewhere on the live web.\nA tribunal of validators reads the page and rules.",
           font=sub, fill=INK_SOFT, spacing=16)

    # ---- footer rule ------------------------------------------------------
    d.line([M, h - 108, px0 - M * 0.5, h - 108], fill=OVERPRINT, width=4)
    d.text((M, h - 72),
           "RACE 01  -  PAPER TRAIL  -  BUILT ON GENLAYER",
           font=font("MartianMono", 24, 600, 100), fill=INK_SOFT)

    im.resize((W, H), Image.LANCZOS).save(path, quality=95)


# ---------------------------------------------------------------------------
# SVG
# ---------------------------------------------------------------------------

def write_svgs():
    Path(f"{OUT}/mark.svg").write_text(mark_svg())
    Path(f"{OUT}/mark-on-dark.svg").write_text(mark_svg("#ffffff"))
    Path(f"{OUT}/favicon.svg").write_text(mark_svg(label=False))

    # Outline the wordmark: the exported lockup has no external font dependency.
    from fontTools.ttLib import TTFont
    from fontTools.varLib.instancer import instantiateVariableFont
    from fontTools.pens.svgPathPen import SVGPathPen
    from fontTools.pens.transformPen import TransformPen
    face = instantiateVariableFont(TTFont(io.BytesIO(font_bytes("SofiaSansExtraCondensed"))),
                                   {"wght": 800}, inplace=False)
    glyphs = face.getGlyphSet()
    cmap = face.getBestCmap()
    scale = 23 / face["head"].unitsPerEm
    x = 42.0
    paths = []
    for char in "PROOF OF HUNT":
        glyph = glyphs[cmap[ord(char)]]
        pen = SVGPathPen(glyphs)
        glyph.draw(TransformPen(pen, (scale, 0, 0, -scale, x, 24)))
        paths.append(pen.getCommands())
        x += glyph.width * scale + .3
    lockup = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {x:.2f} 32" '
              f'width="{x:.2f}" height="32" role="img" aria-label="Proof of Hunt">'
              f'<path fill="#d5006d" d="{GEOMETRY["path"]}"/>'
              f'<path fill="#14140f" d="{" ".join(paths)}"/></svg>\n')
    Path(f"{OUT}/logo-lockup.svg").write_text(lockup)

    # Replace only the nav mark; page structure, copy and accessibility stay put.
    for name in ("index", "play"):
        page = Path(f"web/{name}.html")
        html = page.read_text()
        inline = (f'<svg viewBox="{GEOMETRY["viewBox"]}" aria-hidden="true">'
                  f'<path fill="#d5006d" d="{GEOMETRY["path"]}"/></svg>')
        import re
        html, count = re.subn(r'<svg viewBox="0 0 32 32" aria-hidden="true">.*?</svg>',
                             inline, html, flags=re.S)
        if count != 1:
            raise ValueError(f"Expected exactly one brand mark in {page}, found {count}")
        page.write_text(html)


# ---------------------------------------------------------------------------

def write_ico(path, images):
    """
    Write a multi-size .ico from a list of separately rendered images.

    The format is a six byte header, one sixteen byte directory entry per
    image, then the image payloads. Entries are stored as PNG, which every
    browser released in the last fifteen years reads.
    """
    blobs = []
    for im in images:
        buf = io.BytesIO()
        im.save(buf, format="PNG")
        blobs.append(buf.getvalue())

    header = struct.pack("<HHH", 0, 1, len(blobs))
    offset = len(header) + 16 * len(blobs)
    entries, payload = b"", b""
    for im, blob in zip(images, blobs):
        w, h = im.size
        entries += struct.pack(
            "<BBBBHHII",
            0 if w >= 256 else w, 0 if h >= 256 else h,
            0, 0, 1, 32, len(blob), offset,
        )
        offset += len(blob)
        payload += blob

    with open(path, "wb") as f:
        f.write(header + entries + payload)


def make_preview(path):
    image = Image.new("RGB", (1200, 520), PAPER)
    draw = ImageDraw.Draw(image)
    draw.rectangle((800, 0, 1200, 520), fill=INK)
    for size, position, color in (
        (240, (66, 58), "#d5006d"), (150, (920, 60), "#ffffff"),
        (16, (58, 419), "#d5006d"), (24, (104, 415), "#d5006d"),
        (32, (161, 411), "#d5006d"), (48, (230, 403), "#d5006d"),
    ):
        mark = mark_image(size, color=color)
        image.paste(mark, position, mark)
    draw.text((360, 112), "PROOF\nOF HUNT",
              font=font("SofiaSansExtraCondensed", 76, 800), fill=INK, spacing=0)
    draw.text((61, 332), "HUNT / ROUTE / PROOF",
              font=font("MartianMono", 15, 600), fill=INK_SOFT)
    draw.text((857, 330), "ONE MARK.\nEVERY SCALE.",
              font=font("SofiaSansExtraCondensed", 38, 800), fill=PAPER, spacing=2)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    image.save(path)


def main():
    os.makedirs(OUT, exist_ok=True)
    write_svgs()

    write_ico(f"{OUT}/favicon.ico", [mark_image(size) for size in (16, 32, 48)])
    for size, name in ((32, "favicon-32.png"), (180, "apple-touch-icon.png"),
                       (512, "icon-512.png")):
        mark_image(size, bg=PAPER + (255,) if size >= 180 else None,
                   pad=.12 if size >= 180 else 0).save(f"{OUT}/{name}")

    mark_image(512).save(f"{OUT}/mark-512.png")
    make_og(f"{OUT}/og.png")
    make_preview("verification/brand/logo-preview.png")

    for f in sorted(os.listdir(OUT)):
        print(" ", f, os.path.getsize(f"{OUT}/{f}"), "bytes")


if __name__ == "__main__":
    main()
