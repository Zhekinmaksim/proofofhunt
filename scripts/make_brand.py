"""
Generate the Proof of Hunt brand set.

The mark is a control point that has been punched.

The ring is the map symbol for a control: on every orienteering map in the
world, a control is a circle drawn in magenta over the terrain, with the legs
of the course stopping at its edge rather than crossing it. The dots inside are
the pin pattern a control punch leaves in a runner's card - the thing that
proves you stood there, as opposed to merely finishing. One glyph, both halves
of the name: the place an answer was hidden, and the evidence you found it.

The pin arrangement is deliberately asymmetric. Real punches are, because a
symmetric pattern would be unreadable when the card is turned over, and because
distinguishing one control's punch from another's is the entire point.

    python3 scripts/make_brand.py
"""

import io
import os
import math
import struct
import sys
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import course as C

OUT = "web/brand"
# Fonts are resolved from a local directory if present, so a checkout with the
# TTFs dropped in renders identically to the original. Without them Pillow falls
# back to whatever fontconfig offers, which changes the card but not the icons.
FONTS = os.environ.get("POH_FONTS", "fonts")

# Night course. The daylight palette was ISOM on paper: magenta overprint on a
# cool white sheet. This is the same map read under a headlamp - terrain drops
# to near black and the course changes to a lime that survives it. The rule is
# unchanged: everything belonging to the race is the overprint colour, and
# nothing else is.
# The palette is quoted from ISOM, the IOF printing standard for orienteering
# maps: purple is the course overprint, yellow is open land, brown is landform,
# blue is water, black is paths and rock. Yellow is a ground colour and purple
# is the only accent, which is the same rule the page runs on.
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


def font(name, size, wght=400, wdth=None):
    path = f"{FONTS}/{name}.ttf"
    if not os.path.exists(path):
        path = name.replace("SofiaSansExtraCondensed", "Sofia Sans Extra Condensed") \
                   .replace("SofiaSans", "Sofia Sans") \
                   .replace("MartianMono", "Martian Mono")
    f = ImageFont.truetype(path, size)
    try:
        axes = [wght] if wdth is None else [wdth, wght]
        f.set_variation_by_axes(axes)
    except Exception:
        pass
    return f


# ---------------------------------------------------------------------------
# The mark
# ---------------------------------------------------------------------------

# Pin lattice inside the ring, as offsets on a 3x3 grid. Five pins, no axis of
# symmetry, which is what makes a punch pattern identifiable.
PINS = [(0, 0), (2, 0), (1, 1), (0, 2), (1, 2)]

# Below about twenty pixels five pins stop being five pins and become a smudge.
# Three survive, keep the asymmetry, and still read as holes rather than as a
# filled dot, which is the only thing the mark needs to say at that size.
PINS_SMALL = [(0, 0), (2, 0), (1, 2)]


def draw_mark(d, cx, cy, r, stroke, pin_r, pitch, legs=True, ring=OVERPRINT, pin=INK,
              pins=None):
    if legs:
        # The course arrives from the lower left and leaves to the upper right,
        # stopping at the circle the way a printed leg does.
        k = math.sqrt(0.5)
        for sx, sy in ((-1, 1), (1, -1)):
            x0, y0 = cx + sx * r * k, cy + sy * r * k
            x1, y1 = cx + sx * r * 1.62 * k, cy + sy * r * 1.62 * k
            d.line([x0, y0, x1, y1], fill=ring, width=stroke)

    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=ring, width=stroke)

    ox = cx - pitch
    oy = cy - pitch
    for gx, gy in (pins or PINS):
        px, py = ox + gx * pitch, oy + gy * pitch
        d.ellipse([px - pin_r, py - pin_r, px + pin_r, py + pin_r], fill=pin)


def mark_image(size, legs=True, bg=None, ring=OVERPRINT, pin=INK, pad=0.14):
    im = Image.new("RGBA", (size * SS, size * SS), bg or (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    s = size * SS
    cx = cy = s / 2
    r = s * (0.5 - pad) * (0.78 if legs else 0.92)
    small = size <= 20
    draw_mark(
        d, cx, cy, r,
        stroke=max(SS, int(round(s * (0.075 if small else 0.062)))),
        pin_r=s * (0.045 if small else 0.032),
        pitch=r * (0.54 if small else 0.47),
        legs=legs, ring=ring, pin=pin,
        pins=PINS_SMALL if small else None,
    )
    return im.resize((size, size), Image.LANCZOS)


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
    mk = mark_image(76, legs=True)
    im.paste(mk, (M, 82), mk)
    d.text((M + 96, 120), "PROOF OF HUNT",
           font=font("SofiaSansExtraCondensed", 50, 800), fill=INK, anchor="lm")

    # Condensed capitals, as on the page. The size is fitted to the column
    # rather than chosen, because a fixed size that suits one face overruns
    # with the next: the first render of this card put the full stop of
    # "STORED." across the divider and onto the map.
    col = int(w * 0.52) - M - 40          # left column width, with a margin
    lines = ("TWELVE CLUES. NO", "ANSWER IS STORED.")
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
    d.text((M, y), "ANSWER IS ", font=head, fill=INK)
    wid = d.textlength("ANSWER IS ", font=head)
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

def pin_svg(cx, cy, pitch, r, fill=None, pins=None):
    """The punched pins, in ink. White pins on a white page vanish and leave the
    mark as a bare ring, which is what it silently was after the palette moved
    from dark to paper."""
    fill = fill or "#%02x%02x%02x" % INK
    out = []
    for gx, gy in (pins or PINS):
        out.append(
            f'<circle cx="{cx - pitch + gx * pitch:.2f}" cy="{cy - pitch + gy * pitch:.2f}" '
            f'r="{r:.2f}" fill="{fill}"/>'
        )
    return "".join(out)


def write_svgs():
    RING = "#%02x%02x%02x" % OVERPRINT
    PIN = "#%02x%02x%02x" % INK
    TYPE = "#%02x%02x%02x" % INK

    k = math.sqrt(0.5)
    r, cx, cy = 11.0, 16.0, 16.0
    legs = "".join(
        f'<path d="M{cx + sx * r * k:.2f} {cy + sy * r * k:.2f} '
        f'L{cx + sx * r * 1.62 * k:.2f} {cy + sy * r * 1.62 * k:.2f}"/>'
        for sx, sy in ((-1, 1), (1, -1))
    )

    mark = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32" width="32" height="32" role="img" aria-label="Proof of Hunt">
  <g stroke="{RING}" stroke-width="2" stroke-linecap="round" fill="none">{legs}</g>
  <circle cx="16" cy="16" r="11" fill="none" stroke="{RING}" stroke-width="2"/>
  {pin_svg(16, 16, r * 0.47, 1.05)}
</svg>
'''
    open(f"{OUT}/mark.svg", "w").write(mark)

    # The favicon drops the legs and grows the ring. At 16 pixels a leg is two
    # stray dots that read as a slash through the circle, which is the one thing
    # this mark must never look like.
    fav = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32" width="32" height="32">
  <circle cx="16" cy="16" r="12.4" fill="none" stroke="{RING}" stroke-width="3.4"/>
  {pin_svg(16, 16, 6.4, 2.0, pins=PINS_SMALL)}
</svg>
'''
    open(f"{OUT}/favicon.svg", "w").write(fav)

    lock = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 250 32" width="250" height="32" role="img" aria-label="Proof of Hunt">
  <g stroke="{RING}" stroke-width="2" stroke-linecap="round" fill="none">{legs}</g>
  <circle cx="16" cy="16" r="11" fill="none" stroke="{RING}" stroke-width="2"/>
  {pin_svg(16, 16, r * 0.47, 1.05)}
  <text x="42" y="22.5" font-family="Sofia Sans Extra Condensed, Arial Narrow, sans-serif"
        font-size="23" font-weight="800" letter-spacing="0.3" fill="{TYPE}">PROOF OF HUNT</text>
</svg>
'''
    open(f"{OUT}/logo-lockup.svg", "w").write(lock)


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


def main():
    os.makedirs(OUT, exist_ok=True)
    write_svgs()

    # favicon.ico carries three sizes, each drawn at its own size rather than
    # resampled from one master. Pillow can only do the latter, and it shows:
    # a 16 pixel icon downsampled from 48 turns the pin pattern into grey mush,
    # and the pin pattern is the only thing that distinguishes this mark from
    # any other circle. So the container is written by hand.
    write_ico(f"{OUT}/favicon.ico", [
        mark_image(s, legs=False, bg=PAPER + (255,), pad=0.06).convert("RGBA")
        for s in (16, 32, 48)
    ])

    for s in (32, 180, 512):
        name = {32: "favicon-32.png", 180: "apple-touch-icon.png", 512: "icon-512.png"}[s]
        legs = s >= 180
        bg = PAPER + (255,)
        mark_image(s, legs=legs, bg=bg, pad=0.16 if s >= 180 else 0.06).save(f"{OUT}/{name}")

    make_og(f"{OUT}/og.png")

    for f in sorted(os.listdir(OUT)):
        print(" ", f, os.path.getsize(f"{OUT}/{f}"), "bytes")


if __name__ == "__main__":
    main()
