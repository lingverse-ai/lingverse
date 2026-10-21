"""FUTURE ON THE BLOCK - v9. Same edit as v8 (clips/cuts/timing/song/beatmap/
white end card) + a full typography & HUD pass:
 - ultra-bold condensed Anton giant words (cream #EFE6D2 / coral #F07A4A),
   solid fill, grain on top, 1px RGB-split + halation on edges.
 - DEPTH: words sit BEHIND the person via a per-frame rembg matte (head/body
   occlude the text; text never covers the face).
 - word motion: hard cut in on a beat, 1-2 frame white flash, slow 2-4%
   scale-up while held, hard cut out (no per-letter wiggle).
 - new OSD-style monospace HUD (corners + 0-3s loader), section terminals.
 - end card identical to v8.

Usage: python3 render_v9.py --frames 0.5,7.1,9.2,16.0,23.8 | --all | --cues
"""
import os, sys, math, json, argparse
from functools import lru_cache
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
import common as C
from common import (W, H, FPS, mfont, cfont, ANTON, font, draw_tracked, text_w,
                    ease_out, ease_in_out, clamp01)
import render as R
import hud as HUD
import fx as FX
from render_v3 import finish_v3, beat_zoom
import render_v8 as V8                      # for the v8-identical end card

ROOT = C.ROOT
PACK = os.path.join(ROOT, "pack_v5")
FR = os.path.join(PACK, "work", "fr")
MATTE = os.path.join(PACK, "work", "matte")
OUT = os.path.join(ROOT, "out")
FRAMES = os.path.join(PACK, "work", "out_frames")

DUR = 31.058
NF = int(round(DUR * FPS))

# palette (v9 spec)
CREAM = (239, 230, 210)      # #EFE6D2
CORAL = (240, 122, 74)       # #F07A4A
WHITE = (236, 236, 230)
GREY = (165, 165, 158)
RED = (214, 52, 44)
INK = (18, 18, 18)
MONO = os.path.join(C.FONTS, "JetBrainsMono-Regular.ttf")
MONO_B = os.path.join(C.FONTS, "JetBrainsMono-Bold.ttf")
CJK_B = "/System/Library/Fonts/STHeiti Medium.ttc"

with open(os.path.join(PACK, "beatmap.json")) as f:
    BM = json.load(f)
BEATS, DOWNBEATS = BM["beats"], BM["downbeats"]
ACCENTS, BIG_DROPS = BM["accent_hits"], BM["big_drops"]
BPM = BM["bpm"]

CLIP_WINDOW = V8.CLIP_WINDOW
CUTS = V8.CUTS
ENDCARD_T = 27.423

def mono(sz, bold=False): return font(MONO_B if bold else MONO, sz)
def cjk(sz): return font(CJK_B, sz)

# ================= clip frame + matte pipeline =================
@lru_cache(maxsize=128)
def _load(clip, idx):
    idx = max(0, min(120, idx))
    return Image.open(os.path.join(FR, clip, "f_%03d.jpg" % (idx + 1))).convert("RGB")

@lru_cache(maxsize=256)
def _matte_raw(clip, idx):
    idx = max(0, min(120, idx))
    p = os.path.join(MATTE, clip, "f_%03d.png" % (idx + 1))
    if not os.path.exists(p):
        return None
    return Image.open(p).convert("L").resize((W, H), Image.BILINEAR)

@lru_cache(maxsize=128)
def _matte(clip, idx):
    """Temporal-smoothed (idx-1,idx,idx+1) person matte with ~2px feather."""
    frames = [_matte_raw(clip, i) for i in (idx - 1, idx, idx + 1)]
    frames = [f for f in frames if f is not None]
    if not frames:
        return Image.new("L", (W, H), 0)
    acc = np.mean([np.asarray(f, np.float32) for f in frames], axis=0)
    m = Image.fromarray(acc.clip(0, 255).astype(np.uint8), "L")
    return m.filter(ImageFilter.GaussianBlur(2))

def _xform(img, zoom, focus, rot, resample):
    z = max(1.0, zoom)
    if rot != 0: z = max(z, 1.28)
    nw, nh = int(W * z), int(H * z)
    im = img.resize((nw, nh), resample)
    if rot != 0:
        im = im.rotate(rot, resample=Image.BICUBIC, center=(nw * focus[0], nh * focus[1]))
    left = max(0, min(nw - W, int((nw - W) * focus[0])))
    top = max(0, min(nh - H, int((nh - H) * focus[1])))
    return im.crop((left, top, left + W, top + H))

def clip_frame(clip, src_t, zoom=1.0, focus=(0.5, 0.52), rot=0.0, want_matte=False):
    lo, hi = CLIP_WINDOW[clip]
    src_t = max(lo, min(hi - 0.04, src_t))
    idx = int(round(src_t * 24))
    rgb = _xform(_load(clip, idx), zoom, focus, rot, Image.LANCZOS)
    if not want_matte:
        return rgb, None
    mat = _xform(_matte(clip, idx), zoom, focus, rot, Image.BILINEAR)
    return rgb, mat

# ================= ultra-bold condensed typography (Anton) =================
def _anton(sz): return font(ANTON, sz)

def _text_rgba(text, fnt, color, tracking=2, stroke=0, stroke_fill=None, cjk_font=False):
    tmp = Image.new("RGBA", (10, 10)); d = ImageDraw.Draw(tmp)
    tw = int(text_w(d, text, fnt, tracking)) + stroke * 2 + 10
    asc, desc = fnt.getmetrics(); th = asc + desc + stroke * 2 + 10
    lay = Image.new("RGBA", (tw, th), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    x = stroke + 5
    for ch in text:
        d.text((x, stroke + 3), ch, font=fnt, fill=color,
               stroke_width=stroke, stroke_fill=stroke_fill)
        x += d.textlength(ch, font=fnt) + tracking
    bb = lay.split()[3].getbbox()
    return lay.crop(bb) if bb else lay

def edge_fx(layer):
    """1px RGB split + soft coral halation on the text edges."""
    a = np.asarray(layer).astype(np.float32)
    rgb, al = a[..., :3], a[..., 3:4]
    r = np.roll(rgb[..., 0], -1, axis=1); b = np.roll(rgb[..., 2], 1, axis=1)
    rgb2 = np.dstack([r, rgb[..., 1], b])
    out = np.dstack([rgb2, al[..., 0]]).astype(np.uint8)
    lay = Image.fromarray(out, "RGBA")
    glow = lay.filter(ImageFilter.GaussianBlur(6))
    g = np.asarray(glow).astype(np.float32)
    g[..., 0] = np.maximum(g[..., 0], 180); g[..., 1] *= 0.6; g[..., 2] *= 0.35
    g[..., 3] = (np.asarray(glow)[..., 3].astype(np.float32) * 0.5)
    glow = Image.fromarray(g.clip(0, 255).astype(np.uint8), "RGBA")
    base = Image.new("RGBA", lay.size, (0, 0, 0, 0))
    base.alpha_composite(glow); base.alpha_composite(lay)
    return base

def giant(text, color, style="solid", wave_env=None):
    """Return an RGBA layer (tight) for a giant word, filling ~frame width.
    Short words (<=3 chars) get wide letter-spacing so their letters flank the
    person instead of hiding entirely behind him when composited behind."""
    base_sz = 300
    fnt = _anton(base_sz)
    nchars = len(text.replace(" ", ""))
    trk = 460 if nchars <= 3 else 2
    if style == "outline":
        lay = _text_rgba(text, fnt, (0, 0, 0, 0), tracking=trk, stroke=6,
                         stroke_fill=color + (255,))
    else:
        lay = _text_rgba(text, fnt, color + (255,), tracking=trk)
    sw = 1820 / lay.width; sh = 480 / lay.height; s = min(sw, sh)
    lay = lay.resize((max(1, int(lay.width * s)), max(1, int(lay.height * s))), Image.LANCZOS)
    if style == "waveform" and wave_env is not None:
        lay = _apply_waveform(lay, color, wave_env)
    return edge_fx(lay)

def _apply_waveform(black_layer, coral_unused, env):
    """black_layer: letters in near-black. Punch an orange waveform through them."""
    lw, lh = black_layer.size
    letter_mask = black_layer.split()[3]
    wave = Image.new("RGBA", (lw, lh), (0, 0, 0, 0)); d = ImageDraw.Draw(wave)
    n = len(env); bw = lw / n; midy = lh / 2
    for i, v in enumerate(env):
        x = i * bw; h = (0.1 + 0.9 * v) * lh * 0.5
        d.rectangle([x, midy - h, x + bw * 0.7, midy + h], fill=CORAL + (255,))
    wa = np.asarray(wave).astype(np.float32)
    lm = np.asarray(letter_mask).astype(np.float32) / 255.0
    wa[..., 3] = wa[..., 3] * lm                      # clip waveform to the letters
    out = black_layer.copy()
    out.alpha_composite(Image.fromarray(wa.clip(0, 255).astype(np.uint8), "RGBA"))
    return out

def blit_center(cv, layer, cx, cy, scale=1.0, alpha=1.0):
    if scale != 1.0:
        layer = layer.resize((max(1, int(layer.width * scale)),
                              max(1, int(layer.height * scale))), Image.LANCZOS)
    if alpha < 1.0:
        a = layer.split()[3].point(lambda p: int(p * alpha)); layer = layer.copy(); layer.putalpha(a)
    cv.alpha_composite(layer, (int(cx - layer.width / 2), int(cy - layer.height / 2)))

# ================= word schedule =================
# ONE big word per CUT/shot (fix3: never held across two cuts; hard out at next
# cut). Keyed by cut time -> (TEXT, color, place, style). All ASCII uppercase.
WORD_BY_CUT = {
    0.000: ("FUTURE", CREAM, "front", "solid"),
    1.696: ("ON THE", CORAL, "behind", "solid"),
    3.437: ("BLOCK", CREAM, "behind", "solid"),
    # 5.155 / 5.991: callout shot, no big word
    # 6.827: terminal lyric block, no big word
    7.709: ("STREET", CREAM, "behind", "solid"),
    8.545: ("MIC", CORAL, "behind", "solid"),
    9.427: ("BLOCK", (22, 22, 20), "behind", "waveform"),
    10.286: ("IS", CREAM, "behind", "solid"),
    11.982: ("FUTURE", CORAL, "behind", "solid"),
    12.841: ("ON THE BLOCK", CREAM, "behind", "solid"),
    13.700: ("FUTURE", CREAM, "behind", "solid"),
    15.418: ("FUTURE", CREAM, "behind", "solid"),
    17.136: ("THE BLOCK", CORAL, "behind", "solid"),
    18.831: ("XIAOYE", CREAM, "behind", "solid"),
    20.550: ("TRACK 01", CREAM, "behind", "solid"),
    22.291: ("DUN", CREAM, "behind", "solid"),
    23.740: ("DUN", CREAM, "behind", "outline"),
    24.009: ("ON", CORAL, "behind", "solid"),
    24.845: ("THE", CREAM, "behind", "outline"),
    25.705: ("BLOCK", CREAM, "behind", "solid"),
}
_WORD_CACHE = {}
def active_word(t):
    """Return (cut_time, shot_end, TEXT, col, place, style) for the current shot."""
    ct, clip, src0, sect = active_cut(t)
    if ct not in WORD_BY_CUT:
        return None
    txt, col, place, style = WORD_BY_CUT[ct]
    return (ct, _next(ct), txt, col, place, style)

def word_layer(txt, col, style):
    key = (txt, col, style)
    if key not in _WORD_CACHE:
        if style == "waveform":
            env = song_env(len(txt) * 7, 9.427, 10.286)
            _WORD_CACHE[key] = giant(txt, col, "waveform", wave_env=env)
        else:
            _WORD_CACHE[key] = giant(txt, col, style)
    return _WORD_CACHE[key]

# song envelope for waveform-through-text + female bottom bar
_pcm = np.fromfile(os.path.join(ROOT, "src", "song_v3_pcm.f32"), dtype=np.float32)
def song_env(n, t0, t1):
    out = []
    for i in range(n):
        a = t0 + (t1 - t0) * i / n; b = t0 + (t1 - t0) * (i + 1) / n
        seg = _pcm[max(0, int(a * 8000)):max(1, int(b * 8000))]
        out.append(float(np.abs(seg).max()) if len(seg) else 0.0)
    out = np.array(out); return out / out.max() if out.max() > 0 else out

# ================= depth composite =================
def place_word(bg, matte, t):
    """background -> big text -> person matte on top. bg is the CLEAN plate
    (no text). Returns a new composited RGBA layer (fix2: person sampled from
    the clean bg, so the text truly sits behind him)."""
    aw = active_word(t)
    if aw is None:
        return bg
    wt, shot_end, txt, col, place, style = aw
    dur = max(0.2, shot_end - wt)
    prog = clamp01((t - wt) / dur)
    scale = 1.0 + 0.035 * prog                    # slow ~3.5% scale-up while held
    lay = word_layer(txt, col, style)
    cy = H * 0.52 if place == "behind" else H * 0.60   # front word sits lower (off the face)
    out = bg.copy()
    txt_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    blit_center(txt_layer, lay, W / 2, cy, scale=scale)
    out.alpha_composite(txt_layer)                # background -> big text
    if place == "behind" and matte is not None:
        person = bg.copy(); person.putalpha(matte)   # ORIGINAL person (no text)
        out.alpha_composite(person)               # -> person on top (text behind)
    return out

# ================= HUD (OSD monospace) =================
def tc(t):
    f = int(round(t * 24)); return "[00:00:%02d:%02d]" % (f // 24, f % 24)

def chapter(t):
    if t < 1.696: return "01 / FUTURE"
    if t < 3.437: return "02 / ON THE"
    if t < 6.827: return "03 / BLOCK"
    if t < 22.291: return "04 / THE BARS"
    if t < ENDCARD_T: return "05 / DUN"
    return "06 / XIAOYE"

def draw_hud(cv, t):
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
    INSET = 46; wcol = WHITE + (220,); gcol = GREY + (190,); rcol = RED + (255,)
    # corner ticks
    for (x, y, dx, dy) in [(INSET, INSET, 1, 1), (W - INSET, INSET, -1, 1),
                           (INSET, H - INSET, 1, -1), (W - INSET, H - INSET, -1, -1)]:
        d.line([(x, y), (x + dx * 26, y)], fill=(236, 236, 230, 150), width=2)
        d.line([(x, y), (x, y + dy * 26)], fill=(236, 236, 230, 150), width=2)
    # top-left
    draw_tracked(d, (INSET + 30, INSET - 6), "> FUTURE ON THE BLOCK", mono(18, True), wcol, 2)
    draw_tracked(d, (INSET + 30, INSET + 18), "XIAOYE / TRACK 01 / 0:31", mono(13), gcol, 2)
    # top-right BPM + level bar pulsing on beats
    fb = mono(18, True); bx = W - INSET - 30
    nb = min(BEATS, key=lambda b: abs(b - t)); ph = max(0.0, 1 - abs(t - nb) / 0.11)
    bars = 7; bw = 7; gap = 4; eqw = bars * bw + (bars - 1) * gap
    draw_tracked(d, (bx - eqw - 14, INSET - 6), "%.1f BPM" % BPM, fb, wcol, 2, anchor="ra")
    ex = bx - eqw; yb = INSET + 2
    for i in range(bars):
        lv = (0.3 + 0.7 * ph) if i <= int(ph * bars) else 0.22
        hh = int(18 * lv); c = rcol if (i == int(ph * bars) and ph > 0.3) else (236, 236, 230, 170)
        d.rectangle([ex + i * (bw + gap), yb + (18 - hh), ex + i * (bw + gap) + bw, yb + 18], fill=c)
    # bottom-left timecode
    draw_tracked(d, (INSET + 30, H - INSET - 16), tc(t), mono(16), wcol, 1)
    # bottom-right chapter index with blinking underscore
    cur = "_" if int(t * 2) % 2 == 0 else " "
    draw_tracked(d, (W - INSET - 30, H - INSET - 16), chapter(t) + cur, mono(16, True),
                 wcol, 2, anchor="ra")
    # 0-3s bottom-center: xiaoye loader box
    if t < 3.0:
        bw2, bh2 = 300, 40; bx2 = W // 2 - bw2 // 2; by2 = H - 150
        d.rectangle([bx2, by2, bx2 + bw2, by2 + bh2], outline=(236, 236, 230, 150), width=2)
        draw_tracked(d, (bx2 + 14, by2 + 11), "XIAOYE", mono(16, True), wcol, 2)
        lx0, lx1 = bx2 + 110, bx2 + bw2 - 16; ly = by2 + bh2 // 2
        d.line([(lx0, ly), (lx1, ly)], fill=(236, 236, 230, 90), width=3)
        p = clamp01(t / 3.0); dotx = lx0 + (lx1 - lx0) * p
        d.line([(lx0, ly), (dotx, ly)], fill=rcol, width=3)
        d.ellipse([dotx - 5, ly - 5, dotx + 5, ly + 5], fill=rcol)
    cv.alpha_composite(ov)

# ================= section terminals + callouts =================
def rap_terminal(cv, t):
    if not (6.827 <= t < 8.40):
        return
    d = ImageDraw.Draw(cv)
    lines = [("> TRACK 01 // XIAOYE // LIVE FROM THE BLOCK", WHITE),
             ("> MIC CHECK ... ", WHITE, "[OK]", RED),
             ("A.I IS THE FUTURE", GREY),
             ("FUTURE ON THE BLOCK", WHITE),
             ("> BARS LOADED ... ", WHITE, "[100%]", RED)]
    allc = sum(len(l[0]) + (len(l[2]) if len(l) > 2 else 0) for l in lines)
    nchar = int(clamp01((t - 6.827) / 1.2) * allc)
    fm = mono(24, True); x0, y0 = 120, 250; used = 0
    for i, ln in enumerate(lines):
        y = y0 + i * 40; base, bc = ln[0], ln[1]
        seg = base[:max(0, nchar - used)]
        draw_tracked(d, (x0, y), seg, fm, bc + (240,), 1)
        used += len(base)
        if len(ln) > 2 and nchar - used > -len(ln[2]):
            hl = ln[2][:max(0, nchar - used)]
            draw_tracked(d, (x0 + text_w(d, base, fm, 1), y), hl, fm, ln[3] + (255,), 1)
            used += len(ln[2])

def female_subtitle(cv, t):
    if not (15.418 <= t < 22.291):
        return
    d = ImageDraw.Draw(cv)
    fm = mono(26, True)
    txt = "FUTURE ON THE BLOCK "                          # English-only, uppercase
    tw = text_w(d, txt, fm, 1); cur_w = 20
    total = tw + cur_w
    x = W / 2 - total / 2; y = H - 128
    d.rectangle([x - 20, y - 10, x + total + 20, y + 40], fill=(16, 16, 18, 165))
    draw_tracked(d, (x, y), txt, fm, WHITE + (255,), 1)
    if int(t * 2) % 2 == 0:                               # blinking red block cursor
        d.rectangle([x + tw, y - 2, x + tw + 20, y + 28], fill=RED + (255,))

def _dotted(d, p0, p1, col, dash=6, gap=6, width=2):
    x0, y0 = p0; x1, y1 = p1; L = math.hypot(x1 - x0, y1 - y0)
    if L == 0: return
    ux, uy = (x1 - x0) / L, (y1 - y0) / L; n = int(L // (dash + gap)) + 1
    for i in range(n):
        a = i * (dash + gap); b = min(a + dash, L)
        d.line([(x0 + ux * a, y0 + uy * a), (x0 + ux * b, y0 + uy * b)], fill=col, width=width)

def intro_callouts(cv, t):
    # one shot with tracking callouts on chain & headphones (03_fence region)
    if not (5.20 <= t < 6.80):
        return
    d = ImageDraw.Draw(cv); r = RED + (255,)
    for (anchor, label, lx, ly) in [((int(W * 0.50), int(H * 0.64)), "CUBAN LINK 14K", int(W * 0.66), int(H * 0.78)),
                                     ((int(W * 0.43), int(H * 0.54)), "OVER-EAR / NO LOGO", int(W * 0.14), int(H * 0.34))]:
        ax, ay = anchor
        d.rectangle([ax - 5, ay - 5, ax + 5, ay + 5], outline=r, width=2)   # small square at detail
        _dotted(d, (ax, ay), (lx, ly), r, width=2)
        anc = "la" if lx > ax else "ra"
        tx = lx + (10 if lx > ax else -10)
        draw_tracked(d, (tx, ly - 8), label, mono(16, True), WHITE + (255,), 1, anchor=anc)

# ================= beat FX =================
def section_of(t):
    if t < 6.827: return "intro"
    if t < 15.418: return "rap"
    if t < 22.291: return "female"
    if t < ENDCARD_T: return "dun"
    return "end"

def beatfx(img, t, fi, sect):
    img = FX.apply_hits(img, t, fi)
    # word-entry white flash (1-2 frames) as each new word hard-cuts in
    for wt in WORD_BY_CUT:
        if 0 <= t - wt < 1.6 / FPS:
            img = FX.strobe(img, 0.5); break
    if sect == "intro":
        if FX.near(t, BIG_DROPS, 1.8 / FPS) > 0.4: img = FX.strobe(img, 0.55 * FX.near(t, BIG_DROPS, 1.8 / FPS))
    elif sect == "rap":
        ac = FX.near(t, ACCENTS, 0.06)
        if ac > 0.3:
            img = FX.rgb_split(img, int(6 * ac)); img = FX.strobe(img, 0.45 * ac)
    elif sect == "female":
        if FX.near(t, DOWNBEATS, 1.6 / FPS) > 0.4: img = FX.strobe(img, 0.24 * FX.near(t, DOWNBEATS, 1.6 / FPS))
    elif sect == "dun":
        wf = max(FX.near(t, ACCENTS, 2.0 / FPS), FX.near(t, DOWNBEATS, 1.6 / FPS))
        if wf > 0.4: img = FX.strobe(img, 0.72 * wf); img = FX.rgb_split(img, int(6 * wf))
    return img

# ================= per-frame =================
def active_cut(t):
    cur = CUTS[0]
    for c in CUTS:
        if t >= c[0]: cur = c
        else: break
    return cur

def render_endcard_v10(t):
    """v8 end-card layout (person left; stacked FUTURE/ON THE/BLOCK with BLOCK
    hollow; orange asterisk + red line) but English-only ASCII small text."""
    tin = t - ENDCARD_T
    push = 1.02 + 0.045 * ease_in_out(min(1.0, tin / 3.0))
    im = V8._endcard_still()
    nw, nh = int(W * push), int(H * push); im = im.resize((nw, nh), Image.LANCZOS)
    left = int((nw - W) * 0.30); top = int((nh - H) * 0.42)
    cv = im.crop((left, top, left + W, top + H)).convert("RGBA")
    d = ImageDraw.Draw(cv)
    TH, LEAD = 150, 158; RX = W - 70; YB = 180
    lines = [("FUTURE", 27.423, False), ("ON THE", 27.841, False), ("BLOCK", 28.259, True)]
    for wline, wt, outline in lines:
        if t < wt: continue
        y = YB + lines.index((wline, wt, outline)) * LEAD; al = clamp01((t - wt) / 0.14)
        if outline:
            gl = V8.giant_v5_h(wline, TH, (0, 0, 0, 0), stroke=5, stroke_fill=INK + (255,))
        else:
            gl = V8.giant_v5_h(wline, TH, INK + (255,))
        R.blit(cv, gl, RX - gl.width // 2, y + gl.height // 2, scale=1.0, alpha=al, anchor="mm")
    sb = YB + 3 * LEAD
    if tin > 0.95:
        ry = sb + 14
        d.line([(RX - 540, ry), (RX - 8, ry)], fill=(196, 60, 44, 255), width=4)
        HUD.coral_star(d, RX - 578, ry, 18)
    if tin > 1.15:
        fm = mono(25, True)
        for k, s in enumerate(["XIAOYE", "FUTURE ON THE BLOCK / TRACK 01"]):
            draw_tracked(d, (RX, sb + 50 + k * 44), s, fm, INK + (255,), 1, anchor="ra")
    if t > DUR - 0.6:
        f = clamp01((t - (DUR - 0.6)) / 0.6)
        cv.alpha_composite(Image.new("RGBA", (W, H), (0, 0, 0, int(230 * f))))
    return cv

def render_frame(fi):
    t = fi / FPS
    if t >= ENDCARD_T:                                   # end card: v8 layout, ASCII text
        cv = render_endcard_v10(t); rgb = cv.convert("RGB")
        cv2 = rgb.convert("RGBA"); HUD.draw_hud(cv2, t, 11, "OUTRO", show_grid=False)
        return finish_v3(cv2.convert("RGB"), fi)
    ct, clip, src0, sect = active_cut(t); dt = t - ct
    amt = {"intro": 0.06, "rap": 0.08, "female": 0.0, "dun": 0.12}[sect]
    z = beat_zoom(t, ct, amt, dur=0.16 if sect != "dun" else 0.13)
    src_t = src0 + dt
    if sect == "female":
        z = 1.02 + 0.045 * ease_in_out(min(1.0, dt / 1.7))
    elif sect == "dun":
        dur_shot = max(0.08, _next(ct) - ct); prog = clamp01(dt / dur_shot)
        lo, hi = CLIP_WINDOW[clip]; span = min(hi - 0.04 - src0, 2.0 * dur_shot)
        src_t = src0 + span * (prog ** 1.7); z = z + 0.05 * clamp01(dt / 1.0)
    aw = active_word(t)
    need_matte = (aw is not None and aw[4] == "behind")
    rgb, matte = clip_frame(clip, src_t, zoom=z, focus=(0.5, 0.52), want_matte=need_matte)
    bg = rgb.convert("RGBA")
    cv = place_word(bg, matte, t)                        # bg -> text -> person (behind)
    rap_terminal(cv, t); female_subtitle(cv, t); intro_callouts(cv, t)
    rgb = cv.convert("RGB")
    rgb = beatfx(rgb, t, fi, sect)
    cv2 = rgb.convert("RGBA")
    draw_hud(cv2, t)
    return finish_v3(cv2.convert("RGB"), fi)

def _next(ct):
    for i, c in enumerate(CUTS):
        if c[0] == ct: return CUTS[i + 1][0] if i + 1 < len(CUTS) else DUR
    return ct + 1.0

# ================= cues table =================
def print_cues():
    print("TEXT-CUE TABLE  (time, text, layer, color)  -- one word per shot")
    print("%-16s %-14s %-8s %s" % ("shot(s)", "text", "layer", "color"))
    hexmap = {str(CREAM): "cream #EFE6D2", str(CORAL): "coral #F07A4A",
              "(22, 22, 20)": "black+orange wave"}
    for ct in sorted(WORD_BY_CUT):
        txt, col, place, style = WORD_BY_CUT[ct]
        c = hexmap.get(str(col), str(col))
        extra = " [outline]" if style == "outline" else (" [waveform]" if style == "waveform" else "")
        print("%-16s %-14s %-8s %s%s" % ("%.3f-%.3f" % (ct, _next(ct)), txt, place, c, extra))
    print("--- HUD / terminals / subtitles (overlays, always FRONT) ---")
    print("6.827-8.40   rap terminal block (mono, white + red [OK]/[100%])")
    print("15.418-22.29 female subtitle 'FUTURE ON THE BLOCK [red block cursor]'")
    print("5.20-6.80    callouts CUBAN LINK 14K / OVER-EAR / NO LOGO (red dotted)")
    print("0-3.0        XIAOYE loader box + moving red dot (bottom-center)")
    print("27.423-end   end card: FUTURE/ON THE/BLOCK (BLOCK outline) + XIAOYE /")
    print("             FUTURE ON THE BLOCK / TRACK 01")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--frames", type=str, default=""); ap.add_argument("--all", action="store_true")
    ap.add_argument("--cues", action="store_true")
    a = ap.parse_args()
    if a.cues: print_cues(); return
    os.makedirs(OUT, exist_ok=True); os.makedirs(FRAMES, exist_ok=True)
    if a.frames:
        for ts in a.frames.split(","):
            fi = int(round(float(ts) * FPS)); p = os.path.join(OUT, "_v10_%.2f.png" % float(ts))
            render_frame(fi).save(p); print("wrote", p)
    if a.all:
        import time; t0 = time.time()
        for fi in range(NF):
            render_frame(fi).save(os.path.join(FRAMES, "f_%04d.png" % fi))
            if fi % 60 == 0: print("frame %d/%d  %.1fs" % (fi, NF, time.time() - t0))
        print("done %.1fs" % (time.time() - t0))

if __name__ == "__main__":
    main()
