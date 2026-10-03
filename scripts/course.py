"""
The course. One definition, two renderers.

The map on the landing page and the map on the social card have to be the same
course, or the brand is showing two different races. So the geometry lives here
and both renderers read it.

Why this reads as a map and not as a line chart
-----------------------------------------------
Orienteering maps are not a designer's invention. They are a printing standard,
ISOM, maintained by the IOF, and it assigns every colour a fixed job: blue is
water, yellow is open land, green is vegetation that slows you down, brown is
landform, black is rock and man-made, purple is the course overprinted on top of
all of it. Following that assignment is what makes the picture read as a map at
a glance. Inventing a palette is what makes it read as decoration.

The one consequence two earlier drafts of this file got wrong: on a real map the
terrain is not a faint texture behind the course. Yellow open land is a solid,
loud fill covering large areas and it is the first thing the eye lands on. A map
drawn as dark smudges under a bright line is not a restrained map, it is a
broken one.

Also load-bearing:

  1. Legs stop at the edge of a control circle, never crossing it, so the runner
     can still read the circle and the ground inside it.
  2. The course does not cross itself.
  3. Control numbers sit outside the circle, on the bisector of the two legs, so
     a number never lands on a line. They are purple because they belong to the
     overprint, not to the terrain.
  4. Magnetic north lines run the full height at fixed spacing. Every
     orienteering map has them, the runner aligns a compass to them, and they
     give the sheet its characteristic ruled texture.
  5. Contours nest. Concentric closed curves are a hill; parallel waves are
     wallpaper.

The state language is the game's own: the part of the course already run is a
solid line, the part not yet reached is dashed.
"""

import math
import re

FIELD = (520, 380)

# ---------------------------------------------------------------------------
# ISOM colours
#
# The specification gives CMYK for offset printing. Converting that to screen
# RGB by formula overshoots badly on the subtractive mixes - green 50:0:91:0
# computes to a fluorescent #80ff17 that no press has ever produced - so each
# value below takes its hue from the spec and its level from what the ink
# actually looks like on paper.
#
#   brown   18:55:100:20    contours, landform
#   yellow   0:27:79:0      open land
#   blue   100:18:0:0       water
#   green   50:0:91:0       vegetation, slow to run
#   purple  18:100:0:0      the course, overprinted last
# ---------------------------------------------------------------------------

COLOURS = {
    "paper":       "#ffffff",
    "yellow":      "#ffc42e",
    "yellow_soft": "#ffe08f",
    "green":       "#12a04c",
    "green_mid":   "#63bd75",
    "green_soft":  "#abdaa8",
    "blue":        "#0092d4",
    "blue_soft":   "#8fd3f0",
    "brown":       "#a4622a",
    "black":       "#17170f",
    "purple":      "#d5006d",
}

# ---------------------------------------------------------------------------
# Controls. Verified not to self-cross.
# ---------------------------------------------------------------------------

START = (58, 300)
CONTROLS = [
    (74, 230), (130, 176), (100, 106), (174, 74), (252, 106), (234, 178),
    (302, 214), (384, 174), (452, 116), (462, 216), (392, 278),
]
FINISH = (300, 318)

R_CTRL = 13.0
R_START = 15.0
R_FINISH = 17.0
R_FINISH_IN = 11.0

NORTH_SPACING = 42


def nodes():
    pts = [START] + CONTROLS + [FINISH]
    radii = [R_START] + [R_CTRL] * len(CONTROLS) + [R_FINISH]
    return pts, radii


def legs():
    """Legs, each shortened at both ends by the radius of the symbol it meets."""
    pts, radii = nodes()
    out = []
    for i in range(len(pts) - 1):
        (x0, y0), (x1, y1) = pts[i], pts[i + 1]
        dx, dy = x1 - x0, y1 - y0
        L = math.hypot(dx, dy) or 1.0
        ux, uy = dx / L, dy / L
        a, b = radii[i] + 2.5, radii[i + 1] + 2.5
        out.append((x0 + ux * a, y0 + uy * a, x1 - ux * b, y1 - uy * b))
    return out


def label_positions(offset=25.0):
    """
    Control numbers, placed outward along the bisector of the two legs so a
    number never sits on a line. This is what a course setter does by eye; here
    it is one normalisation.
    """
    pts, _ = nodes()
    out = []
    for i in range(1, len(pts) - 1):
        c = pts[i]
        vs = []
        for nb in (pts[i - 1], pts[i + 1]):
            dx, dy = nb[0] - c[0], nb[1] - c[1]
            L = math.hypot(dx, dy) or 1.0
            vs.append((dx / L, dy / L))
        bx, by = -(vs[0][0] + vs[1][0]), -(vs[0][1] + vs[1][1])
        L = math.hypot(bx, by)
        if L < 0.05:
            bx, by = -vs[0][1], vs[0][0]
            L = 1.0
        out.append((c[0] + bx / L * offset, c[1] + by / L * offset))
    return out


# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# Shape generation
#
# Terrain outlines are generated rather than hand-drawn, because hand-drawn
# polygons come out as regular hexagons and hand-drawn curves come out as
# ellipses, and real ground is neither. Each shape is a ring of points whose
# radius wobbles by a seeded pseudo-random amount, then smoothed through
# Catmull-Rom so the outline curves like a vegetation boundary instead of
# faceting like a crystal.
#
# The generator is deterministic: the same seed always produces the same
# outline, so the map on the page and the map on the social card are identical
# and a rebuild never silently redraws the terrain.
# ---------------------------------------------------------------------------


def _rand(seed):
    """A small deterministic sequence. Not cryptography, just repeatable noise."""
    x = (seed * 1103515245 + 12345) & 0x7FFFFFFF
    while True:
        x = (x * 1103515245 + 12345) & 0x7FFFFFFF
        yield (x >> 12) / 524288.0 - 1.0        # roughly -1..1


def blob(cx, cy, rx, ry, seed, n=15, jitter=0.26, squash=0.0):
    """
    A closed, irregular, smoothly curving outline.

    `jitter` is how far each radius may wander from the nominal, `squash` tilts
    the shape so a run of them does not all sit square to the page.
    """
    rnd = _rand(seed)
    pts = []
    for i in range(n):
        a = 2 * math.pi * i / n
        k = 1.0 + next(rnd) * jitter
        x = math.cos(a) * rx * k
        y = math.sin(a) * ry * k
        if squash:
            x, y = (x * math.cos(squash) - y * math.sin(squash),
                    x * math.sin(squash) + y * math.cos(squash))
        pts.append((cx + x, cy + y))
    return _smooth_closed(pts)


def _smooth_closed(pts, tension=0.5):
    """Catmull-Rom through every point, emitted as cubic beziers."""
    n = len(pts)
    d = [f"M{pts[0][0]:.1f} {pts[0][1]:.1f}"]
    for i in range(n):
        p0, p1 = pts[(i - 1) % n], pts[i]
        p2, p3 = pts[(i + 1) % n], pts[(i + 2) % n]
        c1 = (p1[0] + (p2[0] - p0[0]) / 6 * tension,
              p1[1] + (p2[1] - p0[1]) / 6 * tension)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6 * tension,
              p2[1] - (p3[1] - p1[1]) / 6 * tension)
        d.append(f"C{c1[0]:.1f} {c1[1]:.1f} {c2[0]:.1f} {c2[1]:.1f} "
                 f"{p2[0]:.1f} {p2[1]:.1f}")
    return " ".join(d) + " Z"


def ring_set(cx, cy, rx, ry, seed, levels=3, step=0.68, squash=0.0):
    """
    Nested contour rings sharing one outline shape.

    Contours on a hill are near-copies of each other at decreasing size, which
    is exactly what reusing the seed gives. Independently random rings would
    read as scribbles.
    """
    return [blob(cx, cy, rx * step ** i, ry * step ** i, seed,
                 n=13, jitter=0.16, squash=squash)
            for i in range(levels)]


def wander(x0, y0, x1, y1, seed, n=7, amp=16.0):
    """An open, meandering line: streams and tracks do not run straight."""
    rnd = _rand(seed)
    dx, dy = x1 - x0, y1 - y0
    L = math.hypot(dx, dy) or 1.0
    nx, ny = -dy / L, dx / L
    pts = []
    for i in range(n + 1):
        t = i / n
        off = 0.0 if i in (0, n) else next(rnd) * amp
        pts.append((x0 + dx * t + nx * off, y0 + dy * t + ny * off))
    d = [f"M{pts[0][0]:.1f} {pts[0][1]:.1f}"]
    for i in range(len(pts) - 1):
        p0 = pts[max(i - 1, 0)]
        p1, p2 = pts[i], pts[i + 1]
        p3 = pts[min(i + 2, len(pts) - 1)]
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
        d.append(f"C{c1[0]:.1f} {c1[1]:.1f} {c2[0]:.1f} {c2[1]:.1f} "
                 f"{p2[0]:.1f} {p2[1]:.1f}")
    return " ".join(d)


# ---------------------------------------------------------------------------
# Relief
#
# The thing that makes a real orienteering map look technical rather than
# illustrated is contour density. A printed sheet carries brown contour lines
# across its entire surface, dozens of them, thin, nested, flowing around every
# landform. A map with three rings on it and some blobs is a picture of a map.
#
# So the ground is modelled rather than drawn: a height field built from a few
# smooth bumps and hollows, sampled on a grid, with iso-lines extracted by
# marching squares. Nesting, spacing and the way lines crowd on steep ground
# then all come out on their own, because they are consequences of the surface
# rather than decisions about the drawing.
#
# Every fifth line is an index contour and prints heavier, exactly as on paper.
# ---------------------------------------------------------------------------

# (cx, cy, radius x, radius y, height). Negative height is a hollow.
RELIEF = [
    (438,  58, 132,  92,  62),      # the north east hill
    (118, 148, 118,  96,  40),      # north west knoll
    (300, 112,  96,  66,  30),      # shoulder above the open ground
    (250, 300, 210, 118, -46),      # the valley the stream runs down
    (470, 244,  92,  74,  26),      # spur in the south east
    ( 60, 330, 110,  80, -22),      # re-entrant in the south west
]


def height(x, y):
    h = 0.0
    for cx, cy, rx, ry, amp in RELIEF:
        dx, dy = (x - cx) / rx, (y - cy) / ry
        h += amp * math.exp(-(dx * dx + dy * dy) * 1.6)
    h += (FIELD[1] - y) * 0.035          # gentle regional slope
    return h


def _iso_segments(level, nx=104, ny=76):
    """Marching squares over the height field at one level."""
    W, H = FIELD
    sx, sy = W / nx, H / ny
    segs = []

    def at(i, j):
        return height(i * sx, j * sy)

    def interp(p, q, hp, hq):
        t = 0.5 if hp == hq else (level - hp) / (hq - hp)
        return (p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t)

    for j in range(ny):
        for i in range(nx):
            p = [(i * sx, j * sy), ((i + 1) * sx, j * sy),
                 ((i + 1) * sx, (j + 1) * sy), (i * sx, (j + 1) * sy)]
            hv = [at(i, j), at(i + 1, j), at(i + 1, j + 1), at(i, j + 1)]
            idx = sum((1 << k) for k in range(4) if hv[k] > level)
            if idx in (0, 15):
                continue
            e = {}
            for k in range(4):
                a, b = k, (k + 1) % 4
                if (hv[a] > level) != (hv[b] > level):
                    e[k] = interp(p[a], p[b], hv[a], hv[b])
            pts = list(e.values())
            if len(pts) == 2:
                segs.append((pts[0], pts[1]))
            elif len(pts) == 4:                     # saddle, join the short way
                segs.append((pts[0], pts[1]))
                segs.append((pts[2], pts[3]))
    return segs


def _chain(segs, tol=0.9):
    """Join marching-squares segments into polylines so they draw smoothly."""
    key = lambda p: (round(p[0] / tol), round(p[1] / tol))
    ends = {}
    for a, b in segs:
        ends.setdefault(key(a), []).append((a, b))
        ends.setdefault(key(b), []).append((b, a))
    used, lines = set(), []
    for a, b in segs:
        if (key(a), key(b)) in used or (key(b), key(a)) in used:
            continue
        line = [a, b]
        used.add((key(a), key(b)))
        for direction in (0, 1):
            while True:
                tip = line[-1] if direction == 0 else line[0]
                nxt = None
                for p, q in ends.get(key(tip), []):
                    if (key(p), key(q)) in used or (key(q), key(p)) in used:
                        continue
                    nxt = (p, q)
                    break
                if not nxt:
                    break
                used.add((key(nxt[0]), key(nxt[1])))
                if direction == 0:
                    line.append(nxt[1])
                else:
                    line.insert(0, nxt[1])
            line.reverse()
        if len(line) > 3:
            lines.append(line)
    return lines


def contour_paths(interval=7.0):
    """
    Every contour on the sheet, as (svg path, is_index_contour).

    Index contours are every fifth line and print heavier, which is what lets a
    runner count height at a glance.
    """
    lo = min(height(x, y) for x in range(0, FIELD[0] + 1, 20)
             for y in range(0, FIELD[1] + 1, 20))
    hi = max(height(x, y) for x in range(0, FIELD[0] + 1, 20)
             for y in range(0, FIELD[1] + 1, 20))
    out = []
    n = 0
    lvl = math.ceil(lo / interval) * interval
    while lvl < hi:
        for line in _chain(_iso_segments(lvl)):
            d = f"M{line[0][0]:.1f} {line[0][1]:.1f} " + " ".join(
                f"L{x:.1f} {y:.1f}" for x, y in line[1:])
            out.append((d, n % 5 == 0))
        lvl += interval
        n += 1
    return out


# ---------------------------------------------------------------------------
# Point features
#
# A real sheet is covered in small symbols: boulders, knolls, pits, crags. They
# are what gives the map detail at the scale below the contours, and their
# absence is most of what makes a drawn map look like a toy. Placed on a fixed
# lattice with seeded scatter, then culled wherever they would collide with a
# control circle or sit outside the paper.
# ---------------------------------------------------------------------------

def point_features(seed=7, spacing=37, clear=20.0):
    rnd = _rand(seed)
    ctrl = [START] + CONTROLS + [FINISH]
    kinds = ("boulder", "knoll", "pit", "crag", "boulder", "knoll")
    out, k = [], 0
    for gy in range(spacing // 2, FIELD[1], spacing):
        for gx in range(spacing // 2, FIELD[0], spacing):
            k += 1
            x = gx + next(rnd) * spacing * 0.42
            y = gy + next(rnd) * spacing * 0.42
            if next(rnd) < -0.42:                 # leave gaps, not a grid
                continue
            if not (10 < x < FIELD[0] - 10 and 10 < y < FIELD[1] - 10):
                continue
            if any(math.hypot(x - cx, y - cy) < clear for cx, cy in ctrl):
                continue
            out.append((kinds[k % len(kinds)], x, y))
    return out


# Terrain.
#
# Open land and vegetation are the loud layers, but they are deliberately kept
# smaller and more numerous than a first draft would make them. Few large
# rounded shapes read as illustration; many smaller irregular ones read as
# ground. White is runnable forest, the default state, which is why most of the
# sheet stays white.

OPEN_LAND = [
    blob(150, 244, 52, 26, seed=11, n=17, jitter=.34, squash=-0.15),
    blob(214, 236, 30, 17, seed=19, n=15, jitter=.36, squash=0.10),
    blob(324, 100, 40, 25, seed=27, n=17, jitter=.32, squash=0.20),
    blob(486, 300, 34, 22, seed=31, n=15, jitter=.34),
]
ROUGH_OPEN = [
    blob(150, 132, 42, 25, seed=41, n=17, jitter=.34, squash=0.10),
    blob(444, 250, 44, 26, seed=53, n=17, jitter=.32, squash=-0.16),
    blob(96, 236, 26, 16, seed=59, n=13, jitter=.36),
]
VEGETATION = [
    ("green_soft", blob(206, 314, 40, 25, seed=67, n=19, jitter=.36)),
    ("green_mid",  blob(206, 314, 22, 14, seed=67, n=15, jitter=.30)),
    ("green_soft", blob(494, 150, 26, 24, seed=83, n=17, jitter=.34)),
    ("green_soft", blob(58, 76, 34, 22, seed=89, n=17, jitter=.36, squash=0.2)),
    ("green_mid",  blob(352, 44, 24, 15, seed=103, n=15, jitter=.32)),
    ("green_soft", blob(268, 176, 20, 13, seed=109, n=13, jitter=.34)),
]

# Water and the track are routed so neither runs through a control circle. The
# seeds were chosen by search rather than by eye: every candidate was flattened
# to points and scored on its closest approach to any control, and these clear
# every one by more than 30px. A stream through a control circle is not a
# stylistic problem, it is an unreadable map.
STREAM = wander(0, 264, 520, 338, seed=100, n=8, amp=22)   # clears by 32.9px
PATH = wander(0, 290, 520, 242, seed=116, n=8, amp=20)     # clears by 31.7px
# A second, smaller track and a ride, so the network reads as a network.
PATH_MINOR = [
    wander(196, 268, 226, 44, seed=181, n=6, amp=17),    # branch running north
    wander(346, 240, 470, 320, seed=182, n=5, amp=14),   # spur to the south east
]
MARSH_T = (0.68, 0.74, 0.80)


def _flatten(d, per=12):
    """Flatten an svg path of M and C commands into points."""
    toks = re.findall(r"[MC]|-?\d+\.?\d*", d)
    pts, cur, i = [], None, 0
    while i < len(toks):
        if toks[i] == "M":
            cur = (float(toks[i + 1]), float(toks[i + 2])); pts.append(cur); i += 3
        elif toks[i] == "C":
            c1 = (float(toks[i + 1]), float(toks[i + 2]))
            c2 = (float(toks[i + 3]), float(toks[i + 4]))
            e = (float(toks[i + 5]), float(toks[i + 6]))
            for k in range(1, per + 1):
                t = k / per; u = 1 - t
                pts.append((u**3*cur[0] + 3*u*u*t*c1[0] + 3*u*t*t*c2[0] + t**3*e[0],
                            u**3*cur[1] + 3*u*u*t*c1[1] + 3*u*t*t*c2[1] + t**3*e[1]))
            cur = e; i += 7
        else:
            i += 1
    return pts


def marsh_points():
    """Marsh symbols placed on the stream, not floating beside it."""
    pts = _flatten(STREAM)
    return [pts[int(t * (len(pts) - 1))] for t in MARSH_T]


# ---------------------------------------------------------------------------
# SVG
# ---------------------------------------------------------------------------

def svg(cleared=1, locked_opacity=".55", north=True, paper=True, interactive=False):
    """
    Emit the course as SVG markup.

    Two modes. By default the state is baked: `cleared` legs and rings draw
    solid, the rest dashed, which is what the social card and any static export
    need. With `interactive=True` nothing is baked. Every leg is drawn twice, a
    dashed ghost underneath and a solid tracer on top, and every element carries
    a data index so the page can advance the course as the reader scrolls. The
    tracer uses pathLength="1", so one CSS transition on stroke-dashoffset draws
    it regardless of how long the leg actually is.

    `locked_opacity` is exposed because the same dashed purple needs a different
    level depending on what it sits on. `paper` draws the white sheet; turn it
    off to composite onto another ground.
    """
    C = COLOURS
    W, H = FIELD
    labels = label_positions()
    p = []

    p.append(
        f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" role="img" '
        f'aria-label="An orienteering map. A start triangle, eleven numbered '
        f'controls and a double-circle finish joined in order by a purple course '
        f'line, over contours, open land, vegetation and a watercourse.">'
    )
    if paper:
        p.append(f'<rect width="{W}" height="{H}" fill="{C["paper"]}"/>')

    p.append('<g class="terrain">')
    for d in ROUGH_OPEN:
        p.append(f'<path d="{d}" fill="{C["yellow_soft"]}"/>')
    for d in OPEN_LAND:
        p.append(f'<path d="{d}" fill="{C["yellow"]}"/>')
    for key, d in VEGETATION:
        p.append(f'<path d="{d}" fill="{C[key]}"/>')
    for d, is_index in contour_paths():
        p.append(f'<path d="{d}" fill="none" stroke="{C["brown"]}" '
                 f'stroke-width="{0.95 if is_index else 0.55}" '
                 f'stroke-linejoin="round" stroke-linecap="round" '
                 f'opacity="{0.95 if is_index else 0.8}"/>')
    p.append(f'<path d="{STREAM}" fill="none" stroke="{C["blue"]}" '
             f'stroke-width="1.7" stroke-linecap="round"/>')
    for x, y in marsh_points():
        p.append(f'<path d="M{x:.0f} {y:.0f} l11 -2" stroke="{C["blue_soft"]}" '
                 f'stroke-width="1.7" stroke-linecap="round"/>')
    p.append(f'<path d="{PATH}" fill="none" stroke="{C["black"]}" '
             f'stroke-width="1.1" stroke-dasharray="7 4" opacity=".82"/>')
    for d in PATH_MINOR:
        p.append(f'<path d="{d}" fill="none" stroke="{C["black"]}" '
                 f'stroke-width="0.8" stroke-dasharray="4 4" opacity=".55"/>')
    for kind, x, y in point_features():
        if kind == "boulder":
            p.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="1.5" '
                     f'fill="{C["black"]}" opacity=".85"/>')
        elif kind == "knoll":
            p.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="1.6" '
                     f'fill="{C["brown"]}"/>')
        elif kind == "pit":
            p.append(f'<path d="M{x-2.4:.1f} {y-2:.1f} L{x+2.4:.1f} {y-2:.1f} '
                     f'L{x:.1f} {y+2.4:.1f} Z" fill="none" '
                     f'stroke="{C["brown"]}" stroke-width="0.8"/>')
        else:
            p.append(f'<path d="M{x-3:.1f} {y+1.6:.1f} L{x-1:.1f} {y-1.8:.1f} '
                     f'L{x+2.6:.1f} {y-0.6:.1f}" fill="none" '
                     f'stroke="{C["black"]}" stroke-width="1.1" '
                     f'stroke-linejoin="round"/>')
    if north:
        for x in range(NORTH_SPACING, W, NORTH_SPACING):
            p.append(f'<path d="M{x} 0 V{H}" stroke="{C["blue"]}" '
                     f'stroke-width=".7" opacity=".38"/>')
    p.append('</g>')

    lg = legs()

    if interactive:
        # Ghost first: the whole course, dashed, always visible. A runner can
        # see where the course goes before they have been there; what they have
        # not done yet is simply not inked in.
        p.append('<g class="ghost">')
        for x0, y0, x1, y1 in lg:
            p.append(f'<path d="M{x0:.1f} {y0:.1f} L{x1:.1f} {y1:.1f}" fill="none" '
                     f'stroke="{C["purple"]}" stroke-width="2.1" '
                     f'stroke-dasharray="8 6" stroke-linecap="round" '
                     f'stroke-opacity="{locked_opacity}"/>')
        p.append('</g>')

        # Tracer: the part already run, inked solid. pathLength="1" means one
        # transition value draws any leg, whatever its real length.
        p.append('<g class="tracer">')
        for i, (x0, y0, x1, y1) in enumerate(lg):
            p.append(f'<path class="leg" data-leg="{i}" pathLength="1" '
                     f'd="M{x0:.1f} {y0:.1f} L{x1:.1f} {y1:.1f}" fill="none" '
                     f'stroke="{C["purple"]}" stroke-width="2.1" '
                     f'stroke-linecap="round"/>')
        p.append('</g>')
    else:
        p.append('<g class="course-legs">')
        for i, (x0, y0, x1, y1) in enumerate(lg):
            run = i < cleared
            dash = "" if run else ' stroke-dasharray="8 6"'
            op = "1" if run else locked_opacity
            p.append(
                f'<path class="{"leg-run" if run else "leg-ahead"}" '
                f'd="M{x0:.1f} {y0:.1f} L{x1:.1f} {y1:.1f}" fill="none" '
                f'stroke="{C["purple"]}" stroke-width="2.1"{dash} '
                f'stroke-linecap="round" stroke-opacity="{op}"/>'
            )
        p.append('</g>')

    p.append('<g class="controls">')
    sx, sy = START
    ang = math.atan2(CONTROLS[0][1] - sy, CONTROLS[0][0] - sx)
    tri = " ".join(
        f"{sx + R_START * math.cos(ang + k):.1f},{sy + R_START * math.sin(ang + k):.1f}"
        for k in (0, 2.24, -2.24)
    )
    p.append(f'<polygon points="{tri}" fill="none" stroke="{C["purple"]}" '
             f'stroke-width="2.1" stroke-linejoin="round"/>')

    for i, (cx, cy) in enumerate(CONTROLS):
        lx, ly = labels[i]
        if interactive:
            p.append(f'<circle class="ctrl" data-ctrl="{i}" cx="{cx}" cy="{cy}" '
                     f'r="{R_CTRL}" fill="none" stroke="{C["purple"]}" '
                     f'stroke-width="2.1" stroke-dasharray="5 4" '
                     f'stroke-opacity="{locked_opacity}"/>')
            p.append(f'<text class="ctrl-n" data-ctrl="{i}" x="{lx:.1f}" '
                     f'y="{ly:.1f}" text-anchor="middle" '
                     f'dominant-baseline="central" fill="{C["purple"]}" '
                     f'fill-opacity="{locked_opacity}">{i + 1}</text>')
        else:
            on = i < cleared
            dash = "" if on else ' stroke-dasharray="5 4"'
            op = "1" if on else locked_opacity
            p.append(f'<circle cx="{cx}" cy="{cy}" r="{R_CTRL}" fill="none" '
                     f'stroke="{C["purple"]}" stroke-width="2.1"{dash} '
                     f'stroke-opacity="{op}"/>')
            p.append(f'<text class="ctrl-n" x="{lx:.1f}" y="{ly:.1f}" '
                     f'text-anchor="middle" dominant-baseline="central" '
                     f'fill="{C["purple"]}" fill-opacity="{op}">{i + 1}</text>')

    fx, fy = FINISH
    fin_cls = ' class="ctrl" data-ctrl="11"' if interactive else ""
    for r in (R_FINISH_IN, R_FINISH):
        p.append(f'<circle{fin_cls} cx="{fx}" cy="{fy}" r="{r}" fill="none" '
                 f'stroke="{C["purple"]}" stroke-width="2.1" '
                 f'stroke-dasharray="5 4" stroke-opacity="{locked_opacity}"/>')
    p.append('</g>')
    p.append('</svg>')
    return "\n  ".join(p)
