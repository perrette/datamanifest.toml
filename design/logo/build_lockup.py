#!/usr/bin/env python3
"""Generate the README lockup SVGs with the wordmark baked to vector paths.

The wordmark and tagline are converted from Inter (Bold / Medium) to <path>
outlines via fontTools, so the lockup renders identically everywhere with no
font dependency. The TOML brackets are drawn as geometric strokes. The tagline
is justified to exactly the wordmark's advance width (same left/right edges).
Re-run after editing TEXT/colors/layout:

    python3 design/logo/build_lockup.py
"""
import glob
import math
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen

WORDMARK = "datamanifest"
TAGLINE = "ONE MANIFEST · MULTI-LANGUAGE"

# layout
WORD_START = 232      # left edge of the wordmark (and the tagline)
BASE_WORD = 122       # wordmark baseline
BASE_TAG = 156        # tagline baseline (a touch more gap below the wordmark)
ICON_Y = 22           # icon vertical offset
HEIGHT = 196          # canvas height (extra vertical breathing room)
SIZE_WORD = 62
LS_WORD = -1
SIZE_TAG = 22
BRACKET_GAP = 18      # gap between the wordmark and each bracket stem
TAG_MARGIN = 10       # tagline clearance inside each bracket (broader = smaller)
AMBER = "#F0A92B"


def _find(*names):
    for n in names:
        hits = glob.glob(f"/usr/share/fonts/**/{n}", recursive=True)
        if hits:
            return hits[0]
    raise SystemExit(f"font not found: {names}")


BOLD = _find("Inter-Bold.otf", "Inter-Bold.ttf")
MED = _find("Inter-Medium.otf", "Inter-Medium.ttf", "Inter-Regular.otf")


def shape(text, fontpath, size):
    """Return (items, scale): items is a list of (path_d | None, advance_px)."""
    f = TTFont(fontpath)
    gs = f.getGlyphSet()
    cmap = f.getBestCmap()
    s = size / f["head"].unitsPerEm
    items = []
    for ch in text:
        gname = cmap.get(ord(ch))
        if gname is None:
            items.append((None, size * 0.33))
            continue
        g = gs[gname]
        pen = SVGPathPen(gs)
        g.draw(pen)
        items.append((pen.getCommands(), g.width * s))
    return items, s


def width(items, ls):
    """Advance width with `ls` inserted between glyphs only (no trailing)."""
    return sum(a for _, a in items) + ls * (len(items) - 1)


def render(items, s, start, baseline, ls, fill):
    out, x = [], start
    for d, adv in items:
        if d and d.strip():
            out.append(
                f'  <path transform="translate({x:.2f},{baseline:.2f}) '
                f'scale({s:.5f},{-s:.5f})" d="{d}" fill="{fill}"/>'
            )
        x += adv + ls
    return out


ICON = """  <g transform="translate(14,{icon_y}) scale(0.78)">
    <rect x="40" y="52"  width="176" height="46" rx="9" fill="{body}"/>
    <rect x="56" y="70"  width="56" height="5" rx="2.5" fill="{line}"/>
    <rect x="56" y="80"  width="40" height="5" rx="2.5" fill="{line}"/>
    <rect x="40" y="107" width="176" height="46" rx="9" fill="{body}"/>
    <rect x="56" y="125" width="56" height="5" rx="2.5" fill="{line}"/>
    <rect x="56" y="135" width="40" height="5" rx="2.5" fill="{line}"/>
    <rect x="40" y="162" width="176" height="46" rx="9" fill="{body}"/>
    <rect x="56" y="180" width="56" height="5" rx="2.5" fill="{line}"/>
    <rect x="56" y="190" width="40" height="5" rx="2.5" fill="{line}"/>
  </g>"""


def build(path, body, line, word_fill, tag_fill):
    w_items, w_s = shape(WORDMARK, BOLD, SIZE_WORD)
    t_items, t_s = shape(TAGLINE, MED, SIZE_TAG)

    word_w = width(w_items, LS_WORD)
    word_right = WORD_START + word_w
    lb, rb = WORD_START - BRACKET_GAP, word_right + BRACKET_GAP

    # justify the tagline to the bracket span (centered, never beyond the brackets)
    tag_left, tag_right = lb + TAG_MARGIN, rb - TAG_MARGIN
    ls_tag = ((tag_right - tag_left) - width(t_items, 0)) / (len(t_items) - 1)

    word_paths = render(w_items, w_s, WORD_START, BASE_WORD, LS_WORD, word_fill)
    tag_paths = render(t_items, t_s, tag_left, BASE_TAG, ls_tag, tag_fill)

    top, bot = BASE_WORD - 46, BASE_WORD + 8
    brackets = (
        f'  <path d="M{lb+12:.1f} {top} H{lb:.1f} V{bot} H{lb+12:.1f}" fill="none" '
        f'stroke="{AMBER}" stroke-width="7" stroke-linecap="round" stroke-linejoin="round"/>\n'
        f'  <path d="M{rb-12:.1f} {top} H{rb:.1f} V{bot} H{rb-12:.1f}" fill="none" '
        f'stroke="{AMBER}" stroke-width="7" stroke-linecap="round" stroke-linejoin="round"/>'
    )

    vb_w = math.ceil(rb + 26)
    svg = "\n".join([
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {vb_w} {HEIGHT}" role="img" aria-label="datamanifest.toml">',
        ICON.format(icon_y=ICON_Y, body=body, line=line),
        brackets,
        "\n".join(word_paths),
        "\n".join(tag_paths),
        "</svg>",
        "",
    ])
    with open(path, "w") as fh:
        fh.write(svg)
    print(f"wrote {path}: viewBox 0 0 {vb_w} {HEIGHT}; "
          f"wordmark x={WORD_START}..{word_right:.1f}, "
          f"tagline x={tag_left:.1f}..{tag_right:.1f} (ls={ls_tag:.2f}px), "
          f"brackets x={lb:.1f}..{rb:.1f}")


build("design/logo/lockup.svg", "#2f4d7a", "#1c3050", "#2f4d7a", "#7d8aa0")
build("design/logo/lockup-dark.svg", "#ffffff", "#14233d", "#ffffff", "#8fa0bd")
