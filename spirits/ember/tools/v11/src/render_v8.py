"""FUTURE ON THE BLOCK — v5 (REVISION 5, ~31s). 9 raw clips (no rap/lip-sync),
edited strictly to beatmap.json. Reuses the approved V3 grade / 35mm grain /
HUD / beat-hit FX. Typography is ULTRA-WIDE blocky (Archivo Black), warm cream +
soft peach accent (not V4's condensed Anton / saturated coral).

Usage:
  python3 render_v5.py --frames 0.6,7.1,12.2,16.5,24.2,29.5
  python3 render_v5.py --all
  python3 render_v5.py --cutlist        # print every cut time + snapped beat
"""
import os, sys, math, json, argparse
from functools import lru_cache
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
import common as C
from common import (W, H, FPS, CREAM, INK, mfont, sfont, cfont, ARCHIVO,
                    draw_tracked, ease_out, ease_in_out, clamp01, font)
import render as R
import hud as HUD
import fx as FX
from render_v3 import finish_v3, beat_zoom

ROOT = C.ROOT
PACK = os.path.join(ROOT, "pack_v5")
FR = os.path.join(PACK, "work", "fr")
OUT = os.path.join(ROOT, "out")
FRAMES = os.path.join(PACK, "work", "out_frames")

DUR = 31.058
NF = int(round(DUR * FPS))          # 745
HUD.TRACK_LABEL = "0:31"

# soft peach-orange accent (not saturated coral)
PEACH = (233, 150, 112)

with open(os.path.join(PACK, "beatmap.json")) as f:
    BM = json.load(f)
BEATS = BM["beats"]
DOWNBEATS = BM["downbeats"]
ACCENTS = BM["accent_hits"]
BIG_DROPS = BM["big_drops"]

# ================= clip pipeline =================
CLIP_WINDOW = {           # (min_src, max_src) — v7 character-consistency allowed set ONLY
    "01_close": (0.0, 2.0),
    "03_fence": (0.0, 2.0),
    "04_car_vertigo": (1.0, 5.0),
    "06_crouch_roll": (2.0, 5.0),
    "09_roof_v3": (0.0, 5.0),
    "12_tunnel_crash": (0.0, 2.5),   # v7: tightened (face/glasses morph after 3s)
    "13_brick_rush": (2.0, 5.0),     # NEW (shorts), low rush on wet brick
    "14_garage_rise": (2.0, 3.0),    # NEW (shorts), crane rise + push, headlights
    # REMOVED, never use: 05_alley, 07_lightbeam, 08_fogwalk, 14_garage_track
}

@lru_cache(maxsize=96)
def _load(clip, idx):
    idx = max(0, min(120, idx))
    return Image.open(os.path.join(FR, clip, "f_%03d.jpg" % (idx + 1))).convert("RGB")

def clip_frame(clip, src_t, zoom=1.0, focus=(0.5, 0.5), rot=0.0, bright=1.0):
    lo, hi = CLIP_WINDOW[clip]
    src_t = max(lo, min(hi - 0.04, src_t))
    im = _load(clip, int(round(src_t * 24)))
    if bright != 1.0:
        a = np.asarray(im).astype(np.float32)
        im = Image.fromarray(np.clip(a * bright + (bright - 1) * 18, 0, 255).astype(np.uint8))
    z = max(1.0, zoom)
    if rot != 0: z = max(z, 1.28)
    nw, nh = int(W * z), int(H * z)
    im = im.resize((nw, nh), Image.LANCZOS)
    if rot != 0:
        im = im.rotate(rot, resample=Image.BICUBIC, center=(nw * focus[0], nh * focus[1]))
    left = max(0, min(nw - W, int((nw - W) * focus[0])))
    top = max(0, min(nh - H, int((nh - H) * focus[1])))
    return im.crop((left, top, left + W, top + H))

def canvas(rgb): return rgb.convert("RGBA")

# ================= ultra-wide blocky typography (Archivo Black) =================
def _av(size): return font(ARCHIVO, size)

def giant_v5(word, target_w, color, grain_edge=True):
    f = _av(300)
    lay = R.trim(R.text_layer(word, f, color, tracking=2))
    s = target_w / lay.width
    return lay.resize((max(1, int(lay.width * s)), max(1, int(lay.height * s))), Image.LANCZOS)

def giant_v5_h(word, target_h, color, stroke=0, stroke_fill=None):
    f = _av(300)
    lay = R.trim(R.text_layer(word, f, color, tracking=2, stroke=stroke, stroke_fill=stroke_fill))
    s = target_h / lay.height
    return lay.resize((max(1, int(lay.width * s)), max(1, int(lay.height * s))), Image.LANCZOS)

# word slam schedule (time, text, color).  Spans cuts; one word on screen.
WORDS = [
    (6.998, "FUTURE", CREAM), (8.258, "ON THE", PEACH),
    (12.098, "BLOCK", CREAM), (12.958, "A.I", PEACH),
    (13.818, "IS", CREAM), (14.141, "THE", CREAM), (14.559, "FUTURE", PEACH),
]
def draw_word(cv, t):
    for i, (wt, txt, col) in enumerate(WORDS):
        nxt = WORDS[i + 1][0] if i + 1 < len(WORDS) else 15.418
        hold = min(1.25, nxt - wt)
        if wt <= t < wt + hold:
            sc, al = R.slam(t, wt)
            tw = 1780 if len(txt.replace(".", "")) >= 5 or " " in txt else 980
            R.blit(cv, giant_v5(txt, tw, col + (255,)), W // 2, H // 2, scale=sc, alpha=al)
            return

# ================= CUT LIST (every cut snapped to a beatmap time) =================
# (cut_time, clip, src_start, section)  section in intro/rap/female/dun
CUTS = [
    # --- INTRO 0-6.827 (cuts on downbeats + accent; flash on big drops) ---
    (0.000, "01_close",       0.0, "intro"),
    (1.696, "13_brick_rush",  2.0, "intro"),   # (was 05_alley) wet-brick low rush
    (3.437, "04_car_vertigo", 1.0, "intro"),
    (5.155, "03_fence",       0.0, "intro"),
    (5.991, "06_crouch_roll", 2.0, "intro"),
    # --- RAP 6.827-15.418 (fast 1-2 beats; zoom-punch+shake+RGB-glitch on accents) ---
    (6.827,  "01_close",       1.0, "rap"),
    (7.709,  "04_car_vertigo", 2.5, "rap"),
    (8.545,  "14_garage_rise", 2.0, "rap"),    # (was 05_alley) crane rise + headlights
    (9.427,  "06_crouch_roll", 2.1, "rap"),    # v8 fix1: was 3.0 (roll inverts, headphones gone)
    (10.286, "12_tunnel_crash",0.3, "rap"),    # big drop -> crash
    (11.122, "03_fence",       0.5, "rap"),
    (11.982, "09_roof_v3",     0.5, "rap"),     # (was 05_alley)
    (12.841, "01_close",       0.2, "rap"),
    (13.700, "06_crouch_roll", 2.0, "rap"),    # v8 fix1: was 4.0 (headphones cropped)
    (14.559, "04_car_vertigo", 1.5, "rap"),
    # --- FEMALE 15.418-22.291 (long floating; soft flash on downbeats, no shake) ---
    (15.418, "09_roof_v3",     0.0, "female"),  # (lightbeam removed)
    (17.136, "13_brick_rush",  2.0, "female"),  # (alley removed) moody wet brick
    (18.831, "04_car_vertigo", 1.0, "female"),  # slow dolly
    (20.550, "09_roof_v3",     2.5, "female"),  # diff window, non-adjacent to 15.418
    # --- DUN-DUN 22.291-27.42: moving segments only (12,13,14,04,06), every downbeat +
    #     dun hits, no repeated segment, no static holds (speed-ramp + push) ---
    #     (crouch only on the 0.21s slot so its 2x ramp stays in the headphone-safe 2.0-3.0 window)
    (22.291, "12_tunnel_crash", 0.0, "dun"),    # crash-zoom is the 22.291 hit
    (23.740, "14_garage_rise",  2.0, "dun"),    # short crane-rise hit (1s window)
    (24.009, "13_brick_rush",   2.0, "dun"),    # downbeat / big drop
    (24.845, "12_tunnel_crash", 0.5, "dun"),    # dun hit (diff window from 22.291)
    (25.705, "04_car_vertigo",  1.0, "dun"),    # downbeat
    (27.210, "06_crouch_roll",  2.3, "dun"),    # quick rolled hit -> into end card (headphone-safe)
    # --- END CARD 27.423 -> end ---
    (27.423, "endcard",         0.0, "end"),
]

def active_cut(t):
    cur = CUTS[0]
    for c in CUTS:
        if t >= c[0]: cur = c
        else: break
    return cur

SECTION_LABEL = {"intro": "INTRO", "rap": "THE BLOCK", "female": "ETHER",
                 "dun": "808", "end": "OUTRO"}

# ================= end card (V3 layout) =================
@lru_cache(maxsize=1)
def _endcard_still():
    return Image.open(os.path.join(PACK, "endcard_person.jpg")).convert("RGB").resize(
        (W, H), Image.LANCZOS)

ENDCARD_T = 27.423                                                 # fix6
def render_endcard(t):
    tin = t - ENDCARD_T
    push = 1.02 + 0.045 * ease_in_out(min(1.0, tin / 3.0))         # slow push
    im = _endcard_still()
    nw, nh = int(W * push), int(H * push)
    im = im.resize((nw, nh), Image.LANCZOS)
    # keep person on the LEFT: bias crop left
    left = int((nw - W) * 0.30); top = int((nh - H) * 0.42)
    cv = canvas(im.crop((left, top, left + W, top + H)))
    d = ImageDraw.Draw(cv)
    # big stacked FUTURE / ON THE / BLOCK filling the RIGHT half (BLOCK hollow)
    TH, LEAD = 150, 158
    RX = W - 70; YB = 180
    lines = [("FUTURE", 27.423, False), ("ON THE", 27.841, False), ("BLOCK", 28.259, True)]
    for wline, wt, outline in lines:
        if t < wt: continue
        y = YB + lines.index((wline, wt, outline)) * LEAD
        al = clamp01((t - wt) / 0.14)
        if outline:
            gl = giant_v5_h(wline, TH, (0, 0, 0, 0), stroke=5, stroke_fill=INK + (255,))
        else:
            gl = giant_v5_h(wline, TH, INK + (255,))
        R.blit(cv, gl, RX - gl.width // 2, y + gl.height // 2, scale=1.0, alpha=al, anchor="mm")
    sb = YB + 3 * LEAD
    if tin > 0.95:                      # orange asterisk + thin red line
        ry = sb + 14
        d.line([(RX - 540, ry), (RX - 8, ry)], fill=(196, 60, 44, 255), width=4)
        HUD.coral_star(d, RX - 578, ry, 18)
    if tin > 1.15:
        for k, s in enumerate(["XIAOYE", "FUTURE ON THE BLOCK · TRACK 01"]):
            R.draw_mixed(d, (RX - _mixed_width(d, s, 25), sb + 50 + k * 44), s,
                         size=25, col=INK + (255,))
    # final 0.6s fade
    if t > DUR - 0.6:
        f = clamp01((t - (DUR - 0.6)) / 0.6)
        cv.alpha_composite(Image.new("RGBA", (W, H), (0, 0, 0, int(230 * f))))
    return cv

def _mixed_width(d, s, size):
    fm = mfont(size, med=True); fc = cfont(size); w = 0
    for ch in s:
        w += (fc.getlength(ch) if ord(ch) > 0x2E00 else d.textlength(ch, font=fm)) + 1
    return int(w)

# ================= per-frame compose =================
def next_cut_time(ct):
    for i, c in enumerate(CUTS):
        if c[0] == ct:
            return CUTS[i + 1][0] if i + 1 < len(CUTS) else DUR
    return ct + 1.0

def compose(t):
    ct, clip, src0, sect = active_cut(t)
    if clip == "endcard":
        return render_endcard(t), "OUTRO"
    dt = t - ct
    # v8 fix1: gentler punch-in so the neck headphones are never cropped
    amt = {"intro": 0.06, "rap": 0.08, "female": 0.0, "dun": 0.12}[sect]
    z = beat_zoom(t, ct, amt, dur=0.16 if sect != "dun" else 0.13)
    if sect == "female":
        z = 1.02 + 0.045 * ease_in_out(min(1.0, dt / 1.7))   # gentle ethereal push
    src_t = src0 + dt
    if sect == "dun":
        # v8 fix2: play the clip's OWN camera move, accelerating 1.5-2x into the hit
        dur_shot = max(0.08, next_cut_time(ct) - ct)
        prog = clamp01(dt / dur_shot)
        lo, hi = CLIP_WINDOW[clip]
        span = min(hi - 0.04 - src0, 2.0 * dur_shot)         # window- and 2x-capped
        src_t = src0 + span * (prog ** 1.7)                  # ease-in = ramp into the hit
        z = z + 0.05 * clamp01(dt / 1.0)                     # slight continuous push
    foc = (0.5, 0.52)                                        # v8 fix1: keep lower frame (headphones)
    cv = canvas(clip_frame(clip, src_t, zoom=z, focus=foc))
    # female serif accent on the first floating shot (lightbeam removed in v7)
    if sect == "female" and t < 17.136:
        sl = R.text_layer("soul", sfont(300), PEACH + (210,))
        cv.alpha_composite(sl, (W - 360, H - 300))
    # giant word slams
    draw_word(cv, t)
    return cv, SECTION_LABEL[sect]

def whip(img, amt, horiz=True, n=7):
    """Fake directional motion blur (whip-pan energy)."""
    if amt < 1: return img
    a = np.asarray(img).astype(np.float32)
    acc = np.zeros_like(a)
    for k in range(n):
        sh = int((k - n / 2) * amt)
        acc += np.roll(a, sh, axis=1 if horiz else 0)
    return Image.fromarray((acc / n).clip(0, 255).astype(np.uint8))

def beatfx(img, t, fi, sect, ct=0.0):
    """beat-hit FX matching section intent."""
    if sect == "female":
        img = FX.apply_hits(img, t, fi)                      # gentle (glitch only near hits)
        wf = FX.near(t, DOWNBEATS, 1.6 / FPS)
        if wf > 0.4: img = FX.strobe(img, 0.26 * wf)         # soft flash on downbeats, no shake
        return img
    img = FX.apply_hits(img, t, fi)
    if sect == "intro":
        wf = FX.near(t, BIG_DROPS, 1.8 / FPS)                # flash on heavy bass hits
        if wf > 0.4: img = FX.strobe(img, 0.6 * wf)
    elif sect == "rap":
        # RGB-glitch flash + shake on every accent
        ac = FX.near(t, ACCENTS, 0.06)
        if ac > 0.3:
            img = FX.rgb_split(img, int(7 * ac))
            img = FX.strobe(img, 0.5 * ac)
            rng = np.random.default_rng(fi * 13 + 1)
            dx = int(rng.integers(-6, 7) * ac); dy = int(rng.integers(-5, 6) * ac)
            if dx or dy: img = Image.fromarray(np.roll(np.roll(np.asarray(img), dx, 1), dy, 0))
    elif sect == "dun":
        # hard white flash on each dun accent / drop
        wf = max(FX.near(t, ACCENTS, 2.0 / FPS), FX.near(t, BIG_DROPS, 2.0 / FPS),
                 FX.near(t, DOWNBEATS, 1.6 / FPS))
        if wf > 0.4:
            img = FX.strobe(img, 0.72 * wf)
            img = FX.rgb_split(img, int(6 * wf))
        # v8 fix2: fast push/whip transition at every cut onset (the hit)
        onset = t - ct
        if 0 <= onset < 0.11:
            amt = (1 - onset / 0.11) * 16
            img = whip(img, amt, horiz=(int(ct * 1000) % 2 == 0))
    return img

def render_frame(fi):
    t = fi / FPS
    ct, clip, src0, sect = active_cut(t)
    scn_no = CUTS.index((ct, clip, src0, sect)) + 1
    cv, label = compose(t)
    rgb = cv.convert("RGB")
    if sect != "end":
        rgb = beatfx(rgb, t, fi, sect, ct)
    cv2 = rgb.convert("RGBA")
    HUD.draw_hud(cv2, t, scn_no, label, show_grid=(sect != "end"))
    return finish_v3(cv2.convert("RGB"), fi)

# ================= cutlist report =================
def _snap_label(ct):
    tags = []
    def near(lst): return any(abs(ct - x) < 0.02 for x in lst)
    if near(BIG_DROPS): tags.append("big_drop")
    if near(DOWNBEATS): tags.append("downbeat")
    if near(ACCENTS): tags.append("accent_hit")
    if near(BEATS) and not tags: tags.append("beat")
    # nearest beat value
    nb = min(BEATS + [27.423], key=lambda b: abs(b - ct))
    return ("+".join(tags) if tags else "beat"), nb

def print_cutlist():
    print("CUT LIST — every cut snapped to beatmap.json")
    print("%-5s %-9s %-16s %-7s %-26s" % ("#", "t(s)", "clip", "src", "snapped beat"))
    for i, (ct, clip, src0, sect) in enumerate(CUTS):
        kind, nb = _snap_label(ct)
        nxt = CUTS[i + 1][0] if i + 1 < len(CUTS) else DUR
        print("%-5d %-9.3f %-16s %-7.2f %-26s [%s] dur=%.2fs"
              % (i + 1, ct, clip, src0, "%.3f (%s)" % (nb, kind), sect, nxt - ct))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--frames", type=str, default="")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--cutlist", action="store_true")
    a = ap.parse_args()
    if a.cutlist:
        print_cutlist(); return
    os.makedirs(OUT, exist_ok=True); os.makedirs(FRAMES, exist_ok=True)
    if a.frames:
        for ts in a.frames.split(","):
            fi = int(round(float(ts) * FPS))
            p = os.path.join(OUT, "_v8_%.2f.png" % float(ts))
            render_frame(fi).save(p); print("wrote", p)
    if a.all:
        import time; t0 = time.time()
        for fi in range(NF):
            render_frame(fi).save(os.path.join(FRAMES, "f_%04d.png" % fi))
            if fi % 60 == 0: print("frame %d/%d  %.1fs" % (fi, NF, time.time() - t0))
        print("done %.1fs" % (time.time() - t0))

if __name__ == "__main__":
    main()
