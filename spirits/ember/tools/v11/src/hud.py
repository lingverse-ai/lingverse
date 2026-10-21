"""Persistent HUD: corner brackets, frame ticks, mono labels, BPM equalizer,
timecode, scene counter, dot grid, optional crosshair."""
import math
from PIL import Image, ImageDraw
from common import (W, H, CREAM, INK, CORAL, BEATS, mfont, draw_tracked, DOTGRID)

INSET = 46
CREAM_A = (244, 240, 230)
TRACK_LABEL = "0:22"   # overridden per render (v5 sets "0:31")

def _bracket(d, x, y, dx, dy, L=30, wdt=2, col=(244, 240, 230, 150)):
    d.line([(x, y), (x + dx * L, y)], fill=col, width=wdt)
    d.line([(x, y), (x, y + dy * L)], fill=col, width=wdt)

def tc(t):
    f = int(round(t * 24))
    ss = f // 24
    ff = f % 24
    return "00:00:%02d:%02d" % (ss, ff)

def draw_hud(base, t, scene_no, scene_name, show_grid=True, crosshair=None,
             dim=False):
    """base: RGB PIL (modified via paste of an RGBA overlay)."""
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    a = 120 if dim else 165
    col = (244, 240, 230, a)
    coral = (233, 93, 62, 255)

    if show_grid:
        ov.alpha_composite(DOTGRID)

    # corner brackets
    _bracket(d, INSET, INSET, 1, 1, col=col)
    _bracket(d, W - INSET, INSET, -1, 1, col=col)
    _bracket(d, INSET, H - INSET, 1, -1, col=col)
    _bracket(d, W - INSET, H - INSET, -1, -1, col=col)

    # top-left labels
    f1 = mfont(17, bold=True); f2 = mfont(12)
    draw_tracked(d, (INSET + 34, INSET - 6), "FUTURE ON THE BLOCK", f1, col, tracking=3)
    draw_tracked(d, (INSET + 34, INSET + 18), "XIAOYE · TRACK 01 · " + TRACK_LABEL, f2,
                 (244, 240, 230, a - 55), tracking=2)

    # top-right BPM + equalizer (pulses on beats)
    fb = mfont(17, bold=True)
    bpm = "143.6 BPM"
    bx = W - INSET - 34
    # equalizer squares to the right of text
    sq = 13; gap = 7; nsq = 4
    eq_w = nsq * sq + (nsq - 1) * gap
    txt_w = draw_tracked(d, (bx - eq_w - 14, INSET - 6), bpm, fb, col,
                         tracking=3, anchor="ra")
    # phase of nearest beat
    nb = min(BEATS, key=lambda b: abs(b - t))
    phase = max(0.0, 1 - abs(t - nb) / 0.12)
    ex = bx - eq_w
    for i in range(nsq):
        lit = (i == (int(t / 0.418) % nsq))
        if lit and phase > 0.2:
            c = (233, 93, 62, 255)
        else:
            base_a = 70 + int(60 * (i / nsq))
            c = (244, 240, 230, base_a)
        hpad = int((sq) * (0.25 + 0.75 * (phase if lit else 0.4)))
        yb = INSET - 6
        d.rectangle([ex + i * (sq + gap), yb + (sq - hpad),
                     ex + i * (sq + gap) + sq, yb + sq], fill=c)

    # bottom-left timecode
    ft = mfont(16)
    draw_tracked(d, (INSET + 34, H - INSET - 16), tc(t), ft, col, tracking=2)

    # bottom-right scene counter
    fs = mfont(16)
    label = "%02d / %s" % (scene_no, scene_name)
    draw_tracked(d, (W - INSET - 34, H - INSET - 16), label, fs, col,
                 tracking=3, anchor="ra")

    # optional circular crosshair marker
    if crosshair:
        cxp, cyp = crosshair
        r = 16
        d.ellipse([cxp - r, cyp - r, cxp + r, cyp + r], outline=coral, width=2)
        d.line([(cxp - r - 8, cyp), (cxp - r, cyp)], fill=coral, width=2)
        d.line([(cxp + r, cyp), (cxp + r + 8, cyp)], fill=coral, width=2)
        d.line([(cxp, cyp - r - 8), (cxp, cyp - r)], fill=coral, width=2)

    base.paste(ov, (0, 0), ov)
    return base

def coral_star(d, cx, cy, r, col=(233, 93, 62, 255)):
    """8-point coral star marker."""
    pts = []
    for i in range(16):
        ang = math.pi * i / 8 - math.pi / 2
        rr = r if i % 2 == 0 else r * 0.42
        pts.append((cx + rr * math.cos(ang), cy + rr * math.sin(ang)))
    d.polygon(pts, fill=col)
