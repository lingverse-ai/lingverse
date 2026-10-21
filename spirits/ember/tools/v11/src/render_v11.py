"""FUTURE ON THE BLOCK - v11 / REVISION 8 (final, 4K).
Base = v10 (V3 grade, person matte so big words sit BEHIND him, mono HUD,
terminal lyric block, white end card). English only, ALL CAPS, zero non-ASCII.
New: v17 shot list, no-person "MAKE ME A MUSIC VIDEO" intro, music-driven text
motion, marquee on the long shots, glitch on big_drops, skin texture, 30fps,
3840x2160 export.

Usage: python3 render_v11.py --frames 0.9,2.6,3.6,9.0,16.0 | --all | --cues
"""
import os, sys, math, json, argparse, random
from functools import lru_cache
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
import common as C
from common import (W, H, ANTON, SERIF_I, font, draw_tracked, text_w,
                    ease_out, ease_in_out, clamp01)
import render as R
import hud as HUD
import fx as FX
from render_v3 import finish_v3, beat_zoom
from render_v10 import giant, edge_fx            # ultra-bold word renderer (flanking + fx)

ROOT = C.ROOT
PACK = os.path.join(ROOT, "pack_v5")
FR = os.path.join(PACK, "work", "fr")
MATTE = os.path.join(PACK, "work", "matte")
OUT = os.path.join(ROOT, "out")
FRAMES = os.path.join(PACK, "work", "out_frames")

FPS = 30                                           # REVISION8: 30fps
DUR = 31.058
NF = int(round(DUR * FPS))                          # 932

CREAM = (239, 230, 210)      # #EFE6D2
CORAL = (240, 122, 74)       # #F07A4A
ORANGE = (224, 103, 79)      # #E0674F  (intro accent)
WHITE = (236, 236, 230)
GREY = (165, 165, 158)
RED = (214, 52, 44)
INK = (18, 18, 18)
MONO = os.path.join(C.FONTS, "JetBrainsMono-Regular.ttf")
MONO_B = os.path.join(C.FONTS, "JetBrainsMono-Bold.ttf")

with open(os.path.join(PACK, "beatmap.json")) as f:
    BM = json.load(f)
BEATS, DOWNBEATS = BM["beats"], BM["downbeats"]
ACCENTS, BIG_DROPS = BM["accent_hits"], BM["big_drops"]
BPM = BM["bpm"]
RAP = BM["rap_lyrics"]

def mono(sz, bold=False): return font(MONO_B if bold else MONO, sz)
def serif(sz): return font(SERIF_I, sz)

ENDCARD_T = 27.423

# ===== shot list (REVISION8 section 1); each source used once, cuts on downbeats
CUTS = [
    (3.437, "17_train_pass", 0.0),
    (5.155, "18_graffiti_wall", 0.0),
    (6.827, "01_close", 0.0),
    (8.545, "15_platform_back", 0.0),
    (10.286, "12_tunnel_crash", 0.0),
    (11.982, "16_profile", 0.0),
    (13.700, "03_fence", 0.0),
    (15.418, "20_subway_car", 1.0),
    (18.831, "09_roof_v3", 0.0),
    (22.291, "04_car_vertigo", 1.0),
    (24.009, "19_corridor_walk", 0.5),
    (25.705, "06_crouch_roll", 2.0),
    (27.423, "endcard", 0.0),
]
CLIP_WINDOW = {
    "17_train_pass": (0, 5), "18_graffiti_wall": (0, 5), "01_close": (0, 2.0),
    "15_platform_back": (0, 5), "12_tunnel_crash": (0, 2.5), "16_profile": (0, 5),
    "03_fence": (0, 2.0), "20_subway_car": (0, 5), "09_roof_v3": (0, 5),
    "04_car_vertigo": (1, 5), "19_corridor_walk": (0, 5), "06_crouch_roll": (2, 5),
}

def active_cut(t):
    cur = CUTS[0]
    for c in CUTS:
        if t >= c[0]: cur = c
        else: break
    return cur

def _next(ct):
    for i, c in enumerate(CUTS):
        if c[0] == ct: return CUTS[i + 1][0] if i + 1 < len(CUTS) else DUR
    return ct + 1.0

# ================= clip + matte pipeline =================
@lru_cache(maxsize=128)
def _load(clip, idx):
    idx = max(0, min(120, idx))
    return Image.open(os.path.join(FR, clip, "f_%03d.jpg" % (idx + 1))).convert("RGB")

@lru_cache(maxsize=256)
def _matte_raw(clip, idx):
    idx = max(0, min(120, idx))
    p = os.path.join(MATTE, clip, "f_%03d.png" % (idx + 1))
    if not os.path.exists(p): return None
    return Image.open(p).convert("L").resize((W, H), Image.BILINEAR)

@lru_cache(maxsize=128)
def _matte(clip, idx):
    fr = [_matte_raw(clip, i) for i in (idx - 1, idx, idx + 1)]
    fr = [f for f in fr if f is not None]
    if not fr: return Image.new("L", (W, H), 0)
    acc = np.mean([np.asarray(f, np.float32) for f in fr], axis=0)
    return Image.fromarray(acc.clip(0, 255).astype(np.uint8), "L").filter(ImageFilter.GaussianBlur(2))

def _xform(img, zoom, focus, resample):
    z = max(1.0, zoom); nw, nh = int(W * z), int(H * z)
    im = img.resize((nw, nh), resample)
    left = max(0, min(nw - W, int((nw - W) * focus[0])))
    top = max(0, min(nh - H, int((nh - H) * focus[1])))
    return im.crop((left, top, left + W, top + H))

def clip_frame(clip, src_t, zoom=1.0, focus=(0.5, 0.5), want_matte=True):
    lo, hi = CLIP_WINDOW[clip]
    src_t = max(lo, min(hi - 0.04, src_t)); idx = int(round(src_t * 24))
    rgb = _xform(_load(clip, idx), zoom, focus, Image.LANCZOS)
    mat = _xform(_matte(clip, idx), zoom, focus, Image.BILINEAR) if want_matte else None
    return rgb, mat

# ================= word rendering =================
_WC = {}
def word_layer(txt, col, style):
    key = (txt, col, style)
    if key in _WC: return _WC[key]
    if style == "serif":
        lay = R.trim(R.text_layer(txt, serif(300), col + (255,), tracking=2))
        s = min(1500 / lay.width, 470 / lay.height)
        lay = lay.resize((int(lay.width * s), int(lay.height * s)), Image.LANCZOS)
        lay = edge_fx(lay)
    elif style == "waveform":
        from render_v10 import song_env
        lay = giant(txt, col, "waveform", wave_env=song_env(len(txt) * 7, 9.427, 10.286))
    else:
        lay = giant(txt, col, style)
    _WC[key] = lay
    return lay

@lru_cache(maxsize=8)
def marquee_layer(txt, col):
    """A wide repeated strip for horizontal scrolling behind the person."""
    unit = giant(txt, col, "solid")
    s = 360 / unit.height
    unit = unit.resize((int(unit.width * s), int(unit.height * s)), Image.LANCZOS)
    reps = int(W * 2 / unit.width) + 2
    strip = Image.new("RGBA", (unit.width * reps, unit.height), (0, 0, 0, 0))
    for i in range(reps):
        strip.alpha_composite(unit, (i * unit.width, 0))
    return strip

# word schedule: (enter_t, TEXT, color, style) -- shown until next enter_t
WORDS = [
    (4.273, "BLOCK", CREAM, "solid"),
    (5.155, "ON THE", CORAL, "solid"),
    (5.991, "BLOCK", CREAM, "solid"),
    (6.827, "A.I", CORAL, "solid"),
    (7.709, "FUTURE", CREAM, "solid"),
    (8.545, "ON THE", CORAL, "solid"),
    (9.427, "BLOCK", (22, 22, 20), "waveform"),
    (10.286, "IS", CREAM, "solid"),
    (11.122, "THE", CREAM, "outline"),
    (11.982, "FUTURE", CORAL, "solid"),
    (12.841, "ON THE BLOCK", CREAM, "solid"),
    (13.700, "FUTURE", CREAM, "solid"),
    (14.559, "STREET", CREAM, "solid"),
    (15.418, "FUTURE ON THE BLOCK  ", CREAM, "marquee"),
    (18.831, "ON THE BLOCK  ", CORAL, "marquee"),
    (22.291, "DUN", CREAM, "solid"),
    (23.150, "DUN", CREAM, "outline"),
    (24.009, "ON", CORAL, "solid"),
    (24.845, "THE", CREAM, "outline"),
    (25.705, "BLOCK", CREAM, "solid"),
    (26.564, "BLOCK", CREAM, "outline"),
]

def active_word(t):
    cur = None
    for i, w in enumerate(WORDS):
        if w[0] <= t:
            nxt = WORDS[i + 1][0] if i + 1 < len(WORDS) else ENDCARD_T
            cur = (w[0], nxt, w[1], w[2], w[3])
        else:
            break
    # serif FUTURE over the ASCII resolve, held into shot 1
    if 3.0 <= t < 4.273:
        return (3.0, 4.273, "FUTURE", CREAM, "serif")
    return cur

def place_word(bg, matte, t):
    aw = active_word(t)
    if aw is None: return bg
    wt, wend, txt, col, style = aw
    out = bg.copy()
    dt = t - wt
    if style == "marquee":
        strip = marquee_layer(txt, col)
        off = int((dt * 120) % (strip.width // 2))       # slow horizontal scroll
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        layer.alpha_composite(strip, (-off, int(H * 0.52 - strip.height / 2)))
        out.alpha_composite(layer)
    else:
        lay = word_layer(txt, col, style)
        punch = 1.05 - 0.05 * clamp01(dt / (4 / FPS))     # 105%->100% over 4 frames
        drift = int(18 * ease_out(clamp01(dt / 1.2)))      # slow horizontal drift
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        from render_v10 import blit_center
        blit_center(layer, lay, W / 2 + drift, H * 0.52, scale=punch)
        out.alpha_composite(layer)
    if matte is not None:
        person = bg.copy(); person.putalpha(matte)
        out.alpha_composite(person)
    return out

# ================= HUD (v10 OSD) =================
def tc(t):
    f = int(round(t * FPS)); return "[00:00:%02d:%02d]" % (f // FPS, f % FPS)

def chapter(t):
    if t < 3.437: return "00 / INTRO"
    if t < 6.827: return "01 / FUTURE"
    if t < 10.286: return "02 / THE BARS"
    if t < 15.418: return "03 / BLOCK"
    if t < 22.291: return "04 / THE HOOK"
    if t < ENDCARD_T: return "05 / DUN"
    return "06 / XIAOYE"

def draw_hud(cv, t):
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
    I = 46; wcol = WHITE + (220,); gcol = GREY + (190,); rcol = RED + (255,)
    for (x, y, dx, dy) in [(I, I, 1, 1), (W - I, I, -1, 1), (I, H - I, 1, -1), (W - I, H - I, -1, -1)]:
        d.line([(x, y), (x + dx * 26, y)], fill=(236, 236, 230, 150), width=2)
        d.line([(x, y), (x, y + dy * 26)], fill=(236, 236, 230, 150), width=2)
    draw_tracked(d, (I + 30, I - 6), "> FUTURE ON THE BLOCK", mono(18, True), wcol, 2)
    draw_tracked(d, (I + 30, I + 18), "XIAOYE / TRACK 01 / 0:31", mono(13), gcol, 2)
    fb = mono(18, True); bx = W - I - 30
    nb = min(BEATS, key=lambda b: abs(b - t)); ph = max(0.0, 1 - abs(t - nb) / 0.11)
    bars = 7; bw = 7; gap = 4; eqw = bars * bw + (bars - 1) * gap
    draw_tracked(d, (bx - eqw - 14, I - 6), "%.1f BPM" % BPM, fb, wcol, 2, anchor="ra")
    ex = bx - eqw; yb = I + 2
    for i in range(bars):
        lv = (0.3 + 0.7 * ph) if i <= int(ph * bars) else 0.22
        hh = int(18 * lv); c = rcol if (i == int(ph * bars) and ph > 0.3) else (236, 236, 230, 170)
        d.rectangle([ex + i * (bw + gap), yb + (18 - hh), ex + i * (bw + gap) + bw, yb + 18], fill=c)
    draw_tracked(d, (I + 30, H - I - 16), tc(t), mono(16), wcol, 1)
    cur = "_" if int(t * 2) % 2 == 0 else " "
    draw_tracked(d, (W - I - 30, H - I - 16), chapter(t) + cur, mono(16, True), wcol, 2, anchor="ra")
    cv.alpha_composite(ov)

# ================= rap terminal (English only, char-by-char) =================
RAP_LINES = [(l["t"], l["text"].upper()) for l in RAP
             if all(ord(ch) < 0x2E00 for ch in l["text"])]   # drop the two CJK lines

def rap_terminal(cv, t):
    if not (6.827 <= t < 15.0): return
    d = ImageDraw.Draw(cv); fm = mono(23, True); x0, y0 = 110, 235
    header = [("> TRACK 01 // XIAOYE // LIVE FROM THE BLOCK", WHITE, 6.827),
              ("> MIC CHECK ... [OK]", RED, 7.2)]
    lines = header + [("> " + tx, WHITE, lt) for (lt, tx) in RAP_LINES]
    y = y0
    for (txt, col, lt) in lines:
        if t < lt: break
        n = int(clamp01((t - lt) / 0.9) * len(txt)); seg = txt[:n]
        hl = RED + (255,) if "[OK]" in txt or "[100%]" in txt else col + (235,)
        draw_tracked(d, (x0, y), seg, fm, hl, 1); y += 38

# ================= INTRO 0-3.437 (no person) =================
_INTRO_WORDS = [(0.0, "MAKE", "wsolid"), (0.86, "ME", "outline"),
                (1.301, "A", "blackpanel"), (1.696, "MUSIC", "orangepanel"),
                (2.137, "VIDEO", "wsolid")]

@lru_cache(maxsize=16)
def _intro_word(txt, style):
    if style == "outline":
        lay = giant(txt, WHITE, "outline")
    else:
        lay = giant(txt, WHITE if style != "blackpanel" else INK, "solid")
    return lay

@lru_cache(maxsize=1)
def _thumbs():
    names = ["17_train_pass", "01_close", "16_profile", "09_roof_v3", "12_tunnel_crash", "06_crouch_roll"]
    out = []
    for nm in names:
        out.append(_load(nm, 20).resize((150, 84)))
    return out

def _ascii_frame(rgb, cols=150):
    small = rgb.resize((cols, int(cols * H / W / 2)))
    a = np.asarray(small.convert("L")).astype(np.int32)
    chars = " .:-=+*#%@"
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    fm = mono(13, True); cw = W / cols; ch = H / a.shape[0]
    for yy in range(a.shape[0]):
        row = "".join(chars[min(9, a[yy, xx] * 10 // 256)] for xx in range(a.shape[1]))
        col = ORANGE + (235,) if yy % 7 == 3 else (150, 170, 150, 220)
        d.text((0, int(yy * ch)), row, font=fm, fill=col, spacing=0)
    return lay

def intro_frame(t):
    cv = Image.new("RGBA", (W, H), (8, 8, 9, 255))
    d = ImageDraw.Draw(cv)
    if t < 2.137:
        # giant words one per beat, alternating fill styles, black bg
        cur = _INTRO_WORDS[0]
        for i, w in enumerate(_INTRO_WORDS):
            if w[0] <= t: cur = w
        wt, txt, style = cur
        dt = t - wt; punch = 1.06 - 0.06 * clamp01(dt / (4 / FPS))
        lay = _intro_word(txt, style)
        sw, sh = int(lay.width * punch), int(lay.height * punch)
        lw = lay.resize((sw, sh), Image.LANCZOS)
        px, py = W // 2 - sw // 2, int(H * 0.5) - sh // 2
        if style == "blackpanel":
            d.rectangle([px - 40, py - 20, px + sw + 40, py + sh + 20], fill=WHITE + (255,))
        elif style == "orangepanel":
            d.rectangle([px - 40, py - 20, px + sw + 40, py + sh + 20], fill=ORANGE + (255,))
        cv.alpha_composite(lw, (px, py))
    elif t < 2.75:
        # node diagram: GROK -> OPUS, thumbnails popping on hi-hats, orange star
        cy = int(H * 0.5)
        d.ellipse([W * 0.30 - 26, cy - 26, W * 0.30 + 26, cy + 26], outline=WHITE + (255,), width=3)
        d.line([(W * 0.30 + 26, cy), (W * 0.42, cy)], fill=WHITE + (180,), width=2)
        d.rectangle([W * 0.42, cy - 22, W * 0.42 + 44, cy + 22], outline=WHITE + (255,), width=3)
        draw_tracked(d, (W * 0.30, cy + 48), "XIAOYE", mono(20, True), WHITE + (255,), 2, anchor="ma")
        draw_tracked(d, (W * 0.42 + 22, cy + 48), "FUTURE", mono(20, True), WHITE + (255,), 2, anchor="ma")
        thumbs = _thumbs(); nshow = int(clamp01((t - 2.137) / 0.6) * len(thumbs))
        for i in range(nshow):
            cv.alpha_composite(Image.new("RGBA", (154, 88), ORANGE + (255,)),
                               (int(W * 0.22 + i * 165), int(H * 0.26)))
            cv.alpha_composite(thumbs[i].convert("RGBA"), (int(W * 0.22 + i * 165) + 2, int(H * 0.26) + 2))
        ang = (t - 2.137) * 6
        _star(d, int(W * 0.66), cy, 34, ang)
        draw_tracked(d, (int(W * 0.66), cy + 60), "BLOCK", mono(20, True), ORANGE + (255,), 2, anchor="ma")
    else:
        # scattered chars -> ASCII of shot1 resolving into footage; serif FUTURE behind
        prog = clamp01((t - 2.75) / (3.437 - 2.75))
        rgb, matte = clip_frame("17_train_pass", 0.0, zoom=1.04, want_matte=True)
        base = Image.new("RGBA", (W, H), (8, 8, 9, 255))
        base.alpha_composite(Image.blend(Image.new("RGBA", (W, H), (8, 8, 9, 255)),
                                         rgb.convert("RGBA"), prog))
        # serif FUTURE behind
        fl = word_layer("FUTURE", CREAM, "serif")
        from render_v10 import blit_center
        tl = Image.new("RGBA", (W, H), (0, 0, 0, 0)); blit_center(tl, fl, W / 2, H * 0.52)
        base.alpha_composite(tl)
        if matte is not None and prog > 0.25:
            person = rgb.convert("RGBA"); pa = matte.point(lambda p: int(p * clamp01((prog - 0.25) / 0.5)))
            person.putalpha(pa); base.alpha_composite(person)
        ascii_lay = _ascii_frame(rgb)
        aa = ascii_lay.split()[3].point(lambda p: int(p * (1 - prog)))
        ascii_lay.putalpha(aa); base.alpha_composite(ascii_lay)
        cv = base
    # intro terminal bar typing
    phrase = "make me a music video"
    n = int(clamp01(t / 2.3) * len(phrase)); typed = phrase[:n]
    curc = "_" if int(t * 2) % 2 == 0 else " "
    bw, bh = 560, 46; bx, by = W // 2 - bw // 2, H - 150
    d = ImageDraw.Draw(cv)
    d.rounded_rectangle([bx, by, bx + bw, by + bh], radius=6, fill=(14, 14, 16, 220),
                        outline=(236, 236, 230, 130))
    draw_tracked(d, (bx + 20, by + 12), (typed + curc).upper(), mono(20, True), WHITE + (255,), 1)
    d.ellipse([bx + bw - 40, by + 8, bx + bw - 8, by + bh - 8], fill=ORANGE + (255,))
    return cv

def _star(d, cx, cy, r, ang):
    pts = []
    for i in range(16):
        a = math.radians(ang) + math.pi * i / 8 - math.pi / 2
        rr = r if i % 2 == 0 else r * 0.42
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    d.polygon(pts, fill=ORANGE + (255,))

# ================= end card (v10 ASCII) =================
import render_v8 as V8
def render_endcard(t):
    tin = t - ENDCARD_T
    push = 1.02 + 0.045 * ease_in_out(min(1.0, tin / 3.0))
    im = V8._endcard_still(); nw, nh = int(W * push), int(H * push)
    im = im.resize((nw, nh), Image.LANCZOS)
    left = int((nw - W) * 0.30); top = int((nh - H) * 0.42)
    cv = im.crop((left, top, left + W, top + H)).convert("RGBA"); d = ImageDraw.Draw(cv)
    TH, LEAD = 150, 158; RX = W - 70; YB = 180
    lines = [("FUTURE", 27.423, False), ("ON THE", 27.841, False), ("BLOCK", 28.259, True)]
    for wline, wt, outline in lines:
        if t < wt: continue
        y = YB + lines.index((wline, wt, outline)) * LEAD; al = clamp01((t - wt) / 0.14)
        gl = V8.giant_v5_h(wline, TH, (0, 0, 0, 0), stroke=5, stroke_fill=INK + (255,)) if outline \
            else V8.giant_v5_h(wline, TH, INK + (255,))
        R.blit(cv, gl, RX - gl.width // 2, y + gl.height // 2, scale=1.0, alpha=al, anchor="mm")
    sb = YB + 3 * LEAD
    if tin > 0.95:
        d.line([(RX - 540, sb + 14), (RX - 8, sb + 14)], fill=(196, 60, 44, 255), width=4)
        HUD.coral_star(d, RX - 578, sb + 14, 18)
    if tin > 1.15:
        fm = mono(25, True)
        for k, s in enumerate(["XIAOYE", "FUTURE ON THE BLOCK / TRACK 01"]):
            draw_tracked(d, (RX, sb + 50 + k * 44), s, fm, INK + (255,), 1, anchor="ra")
    if t > DUR - 0.6:
        f = clamp01((t - (DUR - 0.6)) / 0.6)
        cv.alpha_composite(Image.new("RGBA", (W, H), (0, 0, 0, int(230 * f))))
    return cv

# ================= beat FX + skin texture =================
def beatfx(img, t, fi):
    img = FX.apply_hits(img, t, fi)
    for wt in [w[0] for w in WORDS] + [w[0] for w in _INTRO_WORDS]:
        if 0 <= t - wt < 2.0 / FPS:
            img = FX.strobe(img, 0.5); break
    # glitch slice / RGB split for ~2 frames on big_drops
    if FX.near(t, BIG_DROPS, 2.0 / FPS) > 0.4:
        wf = FX.near(t, BIG_DROPS, 2.0 / FPS)
        img = FX.rgb_split(img, int(7 * wf)); img = FX.slice_displace(img, int(9 * wf), fi * 5 + 1)
    elif FX.near(t, ACCENTS, 0.05) > 0.3:
        img = FX.rgb_split(img, int(5 * FX.near(t, ACCENTS, 0.05)))
    return img

def finish_v11(img, fi):
    # skin/image texture: light unsharp (texture) + chroma noise, then V3 grade+grain
    a = np.asarray(img).astype(np.float32)
    blur = np.asarray(img.filter(ImageFilter.GaussianBlur(1.2))).astype(np.float32)
    a = a + (a - blur) * 0.32                              # unsharp texture (no smoothing)
    rng = np.random.default_rng(7000 + fi)
    a[..., 0] += rng.standard_normal((H, W)).astype(np.float32) * 1.8   # chroma noise
    a[..., 2] += rng.standard_normal((H, W)).astype(np.float32) * 1.8
    img = Image.fromarray(a.clip(0, 255).astype(np.uint8), "RGB")
    return finish_v3(img, fi, grain=7)                     # 35mm grain strength ~7 + halation

# ================= per-frame =================
def render_frame(fi):
    t = fi / FPS
    if t < 3.437:
        cv = intro_frame(t); rgb = cv.convert("RGB")
        rgb = beatfx(rgb, t, fi); cv2 = rgb.convert("RGBA"); draw_hud(cv2, t)
        return finish_v11(cv2.convert("RGB"), fi)
    if t >= ENDCARD_T:
        cv = render_endcard(t); rgb = cv.convert("RGB")
        cv2 = rgb.convert("RGBA"); HUD.draw_hud(cv2, t, 13, "OUTRO", show_grid=False)
        return finish_v11(cv2.convert("RGB"), fi)
    ct, clip, src0 = active_cut(t); dt = t - ct
    z = beat_zoom(t, ct, 0.07, dur=0.16)
    rgb, matte = clip_frame(clip, src0 + dt, zoom=z, focus=(0.5, 0.52), want_matte=True)
    bg = rgb.convert("RGBA")
    cv = place_word(bg, matte, t)
    rap_terminal(cv, t)
    rgb = cv.convert("RGB"); rgb = beatfx(rgb, t, fi)
    cv2 = rgb.convert("RGBA"); draw_hud(cv2, t)
    return finish_v11(cv2.convert("RGB"), fi)

# ================= cues =================
def print_cues():
    print("v11 TEXT-CUE TABLE (one word swaps on beats; all BEHIND person)")
    print("%-8s %-22s %s" % ("t(s)", "text", "style/color"))
    print("0.000-2.137  MAKE/ME/A/MUSIC/VIDEO  intro, no person (alt white/outline/panels)")
    print("2.137-2.75   GROK->OPUS node diagram + thumbnails + orange star")
    print("2.75-3.437   ASCII-of-shot1 resolves to footage; serif FUTURE behind")
    for i, w in enumerate(WORDS):
        nxt = WORDS[i + 1][0] if i + 1 < len(WORDS) else ENDCARD_T
        print("%.3f-%.3f  %-22s %s / %s" % (w[0], nxt, w[1], w[3], w[2]))
    print("27.423-end   END CARD  FUTURE/ON THE/BLOCK (outline) + XIAOYE / TRACK 01")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--frames", default=""); ap.add_argument("--all", action="store_true")
    ap.add_argument("--cues", action="store_true"); a = ap.parse_args()
    if a.cues: print_cues(); return
    os.makedirs(OUT, exist_ok=True); os.makedirs(FRAMES, exist_ok=True)
    if a.frames:
        for ts in a.frames.split(","):
            fi = int(round(float(ts) * FPS)); p = os.path.join(OUT, "_v11_%.2f.png" % float(ts))
            render_frame(fi).save(p); print("wrote", p)
    if a.all:
        import time; t0 = time.time()
        for fi in range(NF):
            render_frame(fi).save(os.path.join(FRAMES, "f_%04d.png" % fi))
            if fi % 60 == 0: print("frame %d/%d  %.1fs" % (fi, NF, time.time() - t0))
        print("done %.1fs" % (time.time() - t0))

if __name__ == "__main__":
    main()
