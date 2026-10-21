"""Shared constants, assets, fonts, and low-level drawing/finish helpers for
FUTURE ON THE BLOCK.  Pure Pillow + numpy; no network, no distortion of the
artist (all scaling is uniform)."""
import os, json, math
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONTS = os.path.join(ROOT, "src", "fonts")
STILLS = os.path.join(ROOT, "stills")

W, H = 1920, 1080
FPS = 24
DUR = 21.0
NFRAMES = int(round(DUR * FPS))  # 504

# ---- palette (brief) ----
CREAM = (244, 240, 230)
INK = (17, 17, 17)
CORAL = (233, 93, 62)

# ---- beatmap ----
with open(os.path.join(ROOT, "beatmap.json")) as f:
    BEAT = json.load(f)
BEATS = BEAT["beats"]
DOWNBEATS = BEAT["downbeats"]
STRONG = BEAT["strong_hits"]
BPM = BEAT["bpm"]

# ---- song amplitude envelope (for waveform shot) ----
_pcm = np.fromfile(os.path.join(ROOT, "src", "song_pcm.f32"), dtype=np.float32)
_SR = 8000
def song_envelope(n_bars, t0, t1):
    """Peak amplitude over n_bars equal time bins between t0..t1 (seconds)."""
    out = []
    for i in range(n_bars):
        a = t0 + (t1 - t0) * i / n_bars
        b = t0 + (t1 - t0) * (i + 1) / n_bars
        s0, s1 = int(a * _SR), int(b * _SR)
        seg = _pcm[max(0, s0):max(1, s1)]
        out.append(float(np.abs(seg).max()) if len(seg) else 0.0)
    out = np.array(out)
    if out.max() > 0:
        out = out / out.max()
    return out

# ---- fonts (cached) ----
_fc = {}
def font(path, size):
    key = (path, size)
    if key not in _fc:
        _fc[key] = ImageFont.truetype(path, size)
    return _fc[key]

ANTON = os.path.join(FONTS, "Anton-Regular.ttf")
ARCHIVO = os.path.join(FONTS, "ArchivoBlack-Regular.ttf")
BEBAS = os.path.join(FONTS, "BebasNeue-Regular.ttf")
SERIF_I = os.path.join(FONTS, "InstrumentSerif-Italic.ttf")
MONO = os.path.join(FONTS, "JetBrainsMono-Regular.ttf")
MONO_B = os.path.join(FONTS, "JetBrainsMono-Bold.ttf")
MONO_M = os.path.join(FONTS, "JetBrainsMono-Medium.ttf")
CJK = "/System/Library/Fonts/Hiragino Sans GB.ttc"
CJK_B = "/System/Library/Fonts/STHeiti Medium.ttc"

def gfont(size): return font(ANTON, size)
def mfont(size, bold=False, med=False):
    return font(MONO_B if bold else (MONO_M if med else MONO), size)
def sfont(size): return font(SERIF_I, size)
def cfont(size, bold=False): return font(CJK_B if bold else CJK, size)

# ---- stills (lazy, cached full-res RGB) ----
_sc = {}
def still(name):
    if name not in _sc:
        _sc[name] = Image.open(os.path.join(STILLS, name + ".jpg")).convert("RGB")
    return _sc[name]

# ================= drawing helpers =================
def ease_out(x): return 1 - (1 - x) ** 3
def ease_in_out(x): return 0.5 - 0.5 * math.cos(math.pi * max(0, min(1, x)))
def clamp01(x): return max(0.0, min(1.0, x))

def text_w(draw, s, fnt, tracking=0):
    if not s: return 0
    w = sum(draw.textlength(ch, font=fnt) for ch in s) + tracking * (len(s) - 1)
    return w

def draw_tracked(draw, xy, s, fnt, fill, tracking=0, anchor="la"):
    """Letter-spaced text. anchor: la/ma/ra for left/center/right, baseline top."""
    x, y = xy
    tw = text_w(draw, s, fnt, tracking)
    if anchor[0] == "m": x -= tw / 2
    elif anchor[0] == "r": x -= tw
    for ch in s:
        draw.text((x, y), ch, font=fnt, fill=fill)
        x += draw.textlength(ch, font=fnt) + tracking
    return tw

def ken_burns(name, t01, z0, z1, focus=(0.5, 0.5)):
    """Uniform scale-up + center-ish crop back to WxH. No distortion."""
    img = still(name)
    z = z0 + (z1 - z0) * ease_in_out(t01)
    nw, nh = int(W * z), int(H * z)
    big = img.resize((nw, nh), Image.LANCZOS)
    fx, fy = focus
    left = int((nw - W) * fx)
    top = int((nh - H) * fy)
    left = max(0, min(nw - W, left)); top = max(0, min(nh - H, top))
    return big.crop((left, top, left + W, top + H))

# ================= film finish =================
# precompute vignette + dot grid once
def _build_vignette():
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    cx, cy = W / 2, H / 2
    d = np.sqrt(((xx - cx) / (W * 0.62)) ** 2 + ((yy - cy) / (H * 0.62)) ** 2)
    v = 1.0 - 0.34 * np.clip(d - 0.55, 0, 1) ** 1.6
    return v[..., None]
_VIGN = _build_vignette()

def _build_dotgrid():
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    step = 54
    for y in range(90, H - 60, step):
        for x in range(90, W - 60, step):
            d.ellipse([x, y, x + 1, y + 1], fill=(244, 240, 230, 26))
    return layer
DOTGRID = _build_dotgrid()

def film_finish(img, frame_idx, grain_amt=7.0, soft=0.5):
    """img: RGB PIL. Returns graded RGB PIL with grain/halation/vignette."""
    if soft > 0:
        img = img.filter(ImageFilter.GaussianBlur(soft))
    arr = np.asarray(img).astype(np.float32)
    # halation: coral glow on bright edges
    lum0 = arr @ np.array([0.299, 0.587, 0.114], np.float32)
    bright = np.clip((lum0 - 200) / 55, 0, 1)
    glow = Image.fromarray((bright * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(14))
    g = np.asarray(glow).astype(np.float32)[..., None] / 255.0
    arr = 255 - (255 - arr) * (1 - 0.22 * g * (np.array(CORAL, np.float32) / 255.0))
    # saturation 0.85
    lum = (arr @ np.array([0.299, 0.587, 0.114], np.float32))[..., None]
    arr = lum + (arr - lum) * 0.85
    # lifted milky blacks + rolled highlights (soft S toward a floor ~17)
    x = arr / 255.0
    x = 0.067 + x * (1 - 0.067)                 # lift floor ~17
    x = x - 0.06 * np.sin(math.pi * np.clip(x, 0, 1)) * (x > 0.75)  # roll highs
    arr = np.clip(x, 0, 1) * 255.0
    # split tone: cool shadows, warm highlights
    sh = np.clip(1 - lum / 160.0, 0, 1)
    hi = np.clip((lum - 150) / 105.0, 0, 1)
    arr[..., 2] += sh[..., 0] * 7.0            # +blue in shadows
    arr[..., 0] += hi[..., 0] * 6.0            # +red in highs
    arr[..., 1] += hi[..., 0] * 2.0
    # vignette
    arr = arr * _VIGN
    # animated luma grain
    rng = np.random.default_rng(1234 + frame_idx)
    grain = rng.standard_normal((H, W, 1)).astype(np.float32) * grain_amt
    arr = arr + grain
    out = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGB")
    return out
