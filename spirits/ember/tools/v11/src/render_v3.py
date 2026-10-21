"""FUTURE ON THE BLOCK — v3 (REVISION 3). Live clips (v3/clips), new song,
new beatmap. Reuses the v1 type/HUD/FX helpers; adds a clip-frame pipeline,
zoom-punch / rotation / white-flash transitions, and an older-school film
finish. Pure Pillow + numpy + ffmpeg.

Usage:
  python3 render_v3.py --frames 0.6,4.0,9.2,20.6
  python3 render_v3.py --all
"""
import os, sys, math, json, argparse
from functools import lru_cache
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
import common as C
from common import (W, H, FPS, CREAM, INK, CORAL, mfont, sfont, cfont,
                    draw_tracked, text_w, ease_out, ease_in_out, clamp01)
import render as R          # reuse giant_layer, blit, callout, slam, draw_mixed, ...
import hud as HUD
import fx as FX

ROOT = C.ROOT
FR = os.path.join(ROOT, "v3a", "fr")
OUT = os.path.join(ROOT, "out")
FRAMES = os.path.join(ROOT, "v3a", "out_frames")

DUR = 21.6
NF = 520                                   # ~21.67s; -shortest clamps to 21.6 audio

with open(os.path.join(ROOT, "v3", "beatmap_v3.json")) as f:
    BM = json.load(f)
DOWNBEATS = BM["downbeats"]
BEATS = BM["beats"]
STRONG = BM["strong_hits"]

# ---- new-song amplitude envelope (waveform) ----
_pcm = np.fromfile(os.path.join(ROOT, "src", "song_v3_pcm.f32"), dtype=np.float32)
_SR = 8000
def envelope(n, t0, t1):
    out = []
    for i in range(n):
        a = t0 + (t1 - t0) * i / n; b = t0 + (t1 - t0) * (i + 1) / n
        seg = _pcm[max(0, int(a * _SR)):max(1, int(b * _SR))]
        out.append(float(np.abs(seg).max()) if len(seg) else 0.0)
    out = np.array(out)
    return out / out.max() if out.max() > 0 else out

# ================= clip frame pipeline =================
@lru_cache(maxsize=128)
def _load(clip, idx):
    idx = max(0, min(120, idx))
    return Image.open(os.path.join(FR, clip, "f_%03d.jpg" % (idx + 1))).convert("RGB")

def clip_frame(clip, src_t, zoom=1.0, focus=(0.5, 0.5), rot=0.0,
               bright=1.0, mask_koda=False):
    im = _load(clip, int(round(src_t * 24)))
    if bright != 1.0:
        a = np.asarray(im).astype(np.float32)
        a = np.clip(a * bright + (bright - 1) * 18, 0, 255)   # lift + gain
        im = Image.fromarray(a.astype(np.uint8))
    if mask_koda:
        im = _cover_koda(im)
    z = max(1.0, zoom)
    if rot != 0: z = max(z, 1.26)
    nw, nh = int(W * z), int(H * z)
    im = im.resize((nw, nh), Image.LANCZOS)
    if rot != 0:
        im = im.rotate(rot, resample=Image.BICUBIC, center=(nw * focus[0], nh * focus[1]))
    fx, fy = focus
    left = max(0, min(nw - W, int((nw - W) * fx)))
    top = max(0, min(nh - H, int((nh - H) * fy)))
    return im.crop((left, top, left + W, top + H))

def _cover_koda(im):
    """Paint over the orange KODA logo on the fire-barrel (v3c_07) with a dark
    charred patch (cylindrical shading + grain) that reads as bare barrel.
    Region is generous to cover the logo across the barrel's slight drift."""
    x0, y0, x1, y1 = int(W * 0.595), int(H * 0.655), int(W * 0.755), int(H * 0.95)
    w, h = x1 - x0, y1 - y0
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    shade = 1.0 - 0.40 * np.abs((xx - w / 2) / (w / 2)) ** 1.3        # curvature
    shade *= 1.0 - 0.18 * (yy / h)                                    # darker low
    patch = np.array([36, 28, 24], np.float32)[None, None, :] * shade[..., None]
    rng = np.random.default_rng(7)
    patch = patch + rng.standard_normal((h, w, 1)).astype(np.float32) * 6.0
    blended = Image.fromarray(np.clip(patch, 0, 255).astype(np.uint8)).filter(
        ImageFilter.GaussianBlur(1.2))
    im.paste(blended, (x0, y0))
    return im

def canvas(rgb): return rgb.convert("RGBA")

def beat_zoom(t, dstart, amt=0.12, dur=0.16):
    """zoom-punch that settles after a cut."""
    dt = t - dstart
    if dt < 0: return 1.0
    return 1.0 + amt * (1 - ease_out(clamp01(dt / dur)))

# ================= old-school film finish (v3) =================
def _vign():
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    d = np.sqrt(((xx - W / 2) / (W * 0.60)) ** 2 + ((yy - H / 2) / (H * 0.60)) ** 2)
    return (1.0 - 0.42 * np.clip(d - 0.5, 0, 1) ** 1.5)[..., None]
_V = _vign()

def finish_v3(img, fi, grain=9.0):
    img = img.filter(ImageFilter.GaussianBlur(0.5))
    a = np.asarray(img).astype(np.float32)
    # halation (coral) on brights
    lum0 = a @ np.array([0.299, 0.587, 0.114], np.float32)
    glow = Image.fromarray((np.clip((lum0 - 205) / 50, 0, 1) * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(16))
    g = np.asarray(glow).astype(np.float32)[..., None] / 255.0
    a = 255 - (255 - a) * (1 - 0.24 * g * (np.array(CORAL, np.float32) / 255.0))
    # desaturate (old-school, muted)
    lum = (a @ np.array([0.299, 0.587, 0.114], np.float32))[..., None]
    a = lum + (a - lum) * 0.76
    # faded curve: lift blacks ~RGB22, gently roll highs
    x = a / 255.0
    x = 0.086 + x * (1 - 0.086)
    x = x - 0.07 * np.sin(math.pi * np.clip(x, 0, 1)) * (x > 0.72)
    a = np.clip(x, 0, 1) * 255.0
    # warm amber highlights / teal shadows
    sh = np.clip(1 - lum / 150.0, 0, 1)
    hi = np.clip((lum - 140) / 115.0, 0, 1)
    a[..., 0] += hi[..., 0] * 10.0 + sh[..., 0] * 2.0     # warm highs
    a[..., 1] += hi[..., 0] * 4.0 + sh[..., 0] * 3.0      # teal shadow (G)
    a[..., 2] += sh[..., 0] * 8.0 - hi[..., 0] * 5.0      # teal shadow (B) / less blue in highs
    # overall amber wash
    a[..., 0] += 3.0; a[..., 2] -= 3.0
    # vignette
    a = a * _V
    # gate flicker (projector wobble in brightness)
    rng = np.random.default_rng(1000 + fi)
    a = a * (1.0 + (rng.standard_normal() * 0.012))
    # grain
    a = a + rng.standard_normal((H, W, 1)).astype(np.float32) * grain
    out = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), "RGB")
    # gate weave: 1px vertical jitter
    dy = int(rng.integers(-1, 2))
    if dy: out = Image.fromarray(np.roll(np.asarray(out), dy, axis=0))
    return out

# ================= segments =================
def s1(t):   # 0.000-1.718  street opener, FUTURE
    z = beat_zoom(t, 0.0, 0.10)
    cv = canvas(clip_frame("v3c_01", t, zoom=z, focus=(0.5, 0.52)))
    sc, al = R.slam(t, 0.0, pulse_at=0.418)
    R.blit(cv, R.giant_layer("FUTURE", 1760, CREAM + (255,), tracking=4),
           W // 2, H // 2 - 10, scale=sc, alpha=al)
    d = ImageDraw.Draw(cv)
    phrase = "xiaoye · live from the block"
    n = int(clamp01((t - 0.15) / 1.0) * len(phrase)); typed = phrase[:n]
    cur = "_" if int(t * 2) % 2 == 0 else " "
    bw, bh = 560, 46; bx, by = W // 2 - bw // 2, H - 150
    d.rounded_rectangle([bx, by, bx + bw, by + bh], radius=6,
                        fill=(17, 17, 17, 205), outline=(244, 240, 230, 120))
    draw_tracked(d, (bx + 20, by + 12), typed + cur, mfont(20), CREAM + (255,), 1)
    d.ellipse([bx + bw - 40, by + 8, bx + bw - 8, by + bh - 8], fill=CORAL + (255,))
    return cv

def s2(t):   # 1.718-3.459  fisheye rap, ON THE (coral)
    z = beat_zoom(t, 1.718, 0.13)
    cv = canvas(clip_frame("v3c_02", t - 1.718, zoom=z, focus=(0.5, 0.45)))
    sc, al = R.slam(t, 1.718, pulse_at=2.577)
    R.blit(cv, R.giant_layer("ON THE", 1480, CORAL + (255,), tracking=4),
           W // 2, int(H * 0.62), scale=sc, alpha=al)
    R.callout(ImageDraw.Draw(cv), (int(W * 0.40), int(H * 0.26)),
              "GLASSES · BLACK FRAME", side="left")
    return cv

def s3(t):   # 3.459-5.155  fire barrel (KODA masked), BLOCK
    z = beat_zoom(t, 3.459, 0.11)
    cv = canvas(clip_frame("v3c_07", t - 3.459, zoom=z, focus=(0.42, 0.5), mask_koda=True))
    sc, al = R.slam(t, 3.459)
    R.blit(cv, R.giant_layer("BLOCK", 1560, CREAM + (255,), tracking=2),
           int(W * 0.44), int(H * 0.42), scale=sc, alpha=al)
    return cv

def s4(t):   # 5.155-6.873  crouch rap graffiti, terminal lyrics
    cv = canvas(clip_frame("v3c_08", t - 5.155, zoom=beat_zoom(t, 5.155, 0.08),
                           focus=(0.5, 0.45)))
    cv.alpha_composite(Image.new("RGBA", (W, H), (8, 9, 11, 120)))
    d = ImageDraw.Draw(cv)
    lines = ["> xiaoye // track 01 // live from the block",
             "A.I IS THE FUTURE", "FUTURE ON THE BLOCK",
             "WE DON'T EVER STOP", "> 143.6 BPM // brooklyn"]
    coral = {"A.I", "FUTURE", "BLOCK", "[ok]"}
    scroll = int((t - 5.155) * 40); y0 = 250 - scroll
    fm = mfont(27, med=True)
    for i, ln in enumerate(lines):
        y = y0 + i * 44
        if not (-44 < y < H): continue
        x = 150
        for tok in ln.split(" "):
            col = CORAL + (255,) if tok in coral else (236, 236, 230, 235)
            d.text((x, y), tok, font=fm, fill=col); x += d.textlength(tok + " ", font=fm)
    return cv

def s5(t):   # 6.873-8.591  muscle car backlight, waveform
    z = beat_zoom(t, 6.873, 0.10)
    cv = canvas(clip_frame("v3c_03", t - 6.873, zoom=z, focus=(0.5, 0.5)))
    d = ImageDraw.Draw(cv)
    nb = 92; env = 0.5 * envelope(nb, t - 0.02, t + 0.10) + 0.5 * envelope(nb, 6.873, 8.591)
    by = int(H * 0.84); bw = (W - 300) / nb
    for i, v in enumerate(env):
        x = 150 + i * bw; h = int(5 + v * 130)
        d.rectangle([x, by - h, x + bw * 0.6, by + h], fill=CORAL + (255,))
    draw_tracked(d, (150, H - 150), "XIAOYE · TRACK 01", mfont(22, bold=True), CREAM + (255,), 2)
    return cv

def s6(t):   # 8.591-10.309  FEMALE VOCAL — ethereal light (brightened), slow
    push = 1.02 + 0.05 * ease_in_out((t - 8.591) / 1.718)
    cv = canvas(clip_frame("v3c_10", t - 8.591, zoom=push, focus=(0.5, 0.42), bright=1.9))
    # elegant serif accent, faint
    sl = R.text_layer("soul", sfont(300), CORAL + (220,))
    cv.alpha_composite(sl, (W - 360, H - 300))
    return cv

def s7(t):   # 10.309-12.004  subway tunnel, montage build
    z = beat_zoom(t, 10.309, 0.14)
    cv = canvas(clip_frame("v3c_06", t - 10.309, zoom=z, focus=(0.5, 0.5)))
    draw_tracked(ImageDraw.Draw(cv), (150, H - 150), "FUTURE ON THE BLOCK",
                 mfont(22, bold=True), CREAM + (255,), 2)
    return cv

def s8(t):   # 12.004-13.723  foggy street slow push (pre-hook)
    push = 1.03 + 0.05 * ease_in_out((t - 12.004) / 1.718)
    cv = canvas(clip_frame("v3c_04", (t - 12.004) * 0.6, zoom=push, focus=(0.5, 0.46)))
    return cv

def s9(t):   # 13.723-15.464  rooftop, A.I IS THE FUTURE one-per-beat
    z = beat_zoom(t, 13.723, 0.10)
    cv = canvas(clip_frame("v3c_05", t - 13.723, zoom=z, focus=(0.5, 0.42)))
    words = [("A.I", 13.723, CORAL), ("IS", 14.164, CREAM),
             ("THE", 14.605, CREAM), ("FUTURE", 15.046, CORAL)]
    cur = words[0]
    for i, w in enumerate(words):
        nxt = words[i + 1][1] if i + 1 < len(words) else 15.464
        if w[1] <= t < nxt: cur = w; break
        if t >= words[-1][1]: cur = words[-1]
    word, st, col = cur
    sc, al = R.slam(t, st)
    tw = 820 if len(word) <= 3 else 1740
    R.blit(cv, R.giant_layer(word, tw, col + (255,), tracking=4), W // 2, H // 2, scale=sc, alpha=al)
    return cv

def s10(t):  # 15.464-17.182  FAST MONTAGE: one clip per beat, rot + flash
    seq = [(15.464, "v3c_02"), (15.882, "v3c_08"), (16.323, "v3c_09"),
           (16.741, "v3c_01"), (17.0, "v3c_06")]
    nm, st = seq[0]
    for s, n in seq:
        if t >= s: nm, st = n, s
    rot = (6 if seq.index((st, nm)) % 2 == 0 else -6) * (1 - clamp01((t - st) / 0.30))
    z = beat_zoom(t, st, 0.16, dur=0.18)
    src = (st - 15.0) + (t - st)
    cv = canvas(clip_frame(nm, max(0.2, src), zoom=z, focus=(0.5, 0.46), rot=rot))
    R.blit(cv, R.giant_layer("ON THE BLOCK", 1780, CREAM + (255,), tracking=3),
           W // 2, int(H * 0.5), scale=1.0, alpha=1.0)
    return cv

def s11(t):  # 17.182-18.878  booth punch-in, FUTURE finale
    z = beat_zoom(t, 17.182, 0.18, dur=0.20)
    cv = canvas(clip_frame("v3c_09", t - 17.182, zoom=z, focus=(0.5, 0.44)))
    sc, al = R.slam(t, 17.182, pulse_at=18.018)
    R.blit(cv, R.giant_layer("FUTURE", 1760, CORAL + (255,), tracking=4),
           W // 2, int(H * 0.5), scale=sc, alpha=al)
    return cv

def s12(t):  # 18.878-21.6  END CARD (cream): person LEFT, type RIGHT
    cv = canvas(clip_frame("v3c_11", min(4.0, (t - 18.878) * 0.4 + 0.6), zoom=1.03,
                           focus=(0.32, 0.45)))
    d = ImageDraw.Draw(cv)
    tin = t - 18.878
    # right-side stacked FUTURE / ON THE / BLOCK (BLOCK outline)
    TH, LEAD = 140, 150
    RX = W - 90                      # right edge anchor
    YB = 170
    lines = [("FUTURE", 18.878, False), ("ON THE", 19.15, False), ("BLOCK", 19.42, True)]
    for i, (wline, st, outline) in enumerate(lines):
        if t < st: continue
        y = YB + i * LEAD
        if outline:
            gl = R.giant_layer_h(wline, TH, (0, 0, 0, 0), tracking=2,
                                 stroke=4, stroke_fill=INK + (255,))
        else:
            gl = R.giant_layer_h(wline, TH, INK + (255,), tracking=2)
        cv.alpha_composite(gl, (RX - gl.width, y))
    stack_bottom = YB + 3 * LEAD
    if tin > 0.55:
        ry = stack_bottom + 16
        d.line([(RX - 560, ry), (RX - 6, ry)], fill=INK + (255,), width=5)
        HUD.coral_star(d, RX - 598, ry, 17)
    if tin > 0.8:
        sub = ["XIAOYE", "FUTURE ON THE BLOCK · TRACK 01"]
        fy = stack_bottom + 54
        for s in sub:
            R.draw_mixed(d, (RX - _mixed_width(d, s, 25), fy), s, size=25, col=INK + (255,))
            fy += 44
    return cv

def _mixed_width(d, s, size):
    fm = mfont(size, med=True); fc = cfont(size); w = 0
    for ch in s:
        w += (fc.getlength(ch) if ord(ch) > 0x2E00 else d.textlength(ch, font=fm)) + 1
    return int(w)

SEGMENTS = [
    (0.0, 1.718, s1, 1, "FUTURE"), (1.718, 3.459, s2, 2, "ON THE"),
    (3.459, 5.155, s3, 3, "BLOCK"), (5.155, 6.873, s4, 4, "VERSE"),
    (6.873, 8.591, s5, 5, "THE FLOW"), (8.591, 10.309, s6, 6, "ETHER"),
    (10.309, 12.004, s7, 7, "TUNNEL"), (12.004, 13.723, s8, 8, "FOG"),
    (13.723, 15.464, s9, 9, "THE FUTURE"), (15.464, 17.182, s10, 10, "MONTAGE"),
    (17.182, 18.878, s11, 11, "BOOTH"), (18.878, 22.0, s12, 12, "OUTRO"),
]

def transitions(img, t, fi):
    """white-flash on downbeats + strong-hit glitch/strobe (reused)."""
    img = FX.apply_hits(img, t, fi)
    wf = FX.near(t, DOWNBEATS, 1.6 / FPS)
    if wf > 0.4:
        img = FX.strobe(img, 0.55 * wf, coral=False)
    return img

def render_frame(fi):
    t = fi / FPS
    for (s, e, fn, no, name) in SEGMENTS:
        if s <= t < e:
            cv = fn(t); scn_no, scn_nm = no, name; break
    else:
        cv = s12(min(t, 21.59)); scn_no, scn_nm = 12, "OUTRO"
    rgb = cv.convert("RGB")
    end_card = t >= 18.878
    if not end_card:
        rgb = transitions(rgb, t, fi)
    cv2 = rgb.convert("RGBA")
    HUD.draw_hud(cv2, t, scn_no, scn_nm, show_grid=not end_card)
    return finish_v3(cv2.convert("RGB"), fi)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--frames", type=str, default="")
    ap.add_argument("--all", action="store_true")
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True); os.makedirs(FRAMES, exist_ok=True)
    if a.frames:
        for ts in a.frames.split(","):
            fi = int(round(float(ts) * FPS))
            p = os.path.join(OUT, "_v3_%.2f.png" % float(ts))
            render_frame(fi).save(p); print("wrote", p)
    if a.all:
        import time; t0 = time.time()
        for fi in range(NF):
            render_frame(fi).save(os.path.join(FRAMES, "f_%04d.png" % fi))
            if fi % 48 == 0: print("frame %d/%d  %.1fs" % (fi, NF, time.time() - t0))
        print("done %.1fs" % (time.time() - t0))

if __name__ == "__main__":
    main()
