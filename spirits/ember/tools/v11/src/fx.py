"""Hit/transition effects: RGB channel split, horizontal slice displacement,
strobe flash.  Operate on RGB PIL images."""
import numpy as np
from PIL import Image
from common import W, H, STRONG, DOWNBEATS, CORAL, FPS

def near(t, events, win):
    """Return strongest (0..1) proximity to any event within win seconds."""
    best = 0.0
    for e in events:
        d = abs(t - e)
        if d < win:
            best = max(best, 1 - d / win)
    return best

def rgb_split(img, px):
    if px <= 0: return img
    a = np.asarray(img)
    r = np.roll(a[..., 0], -px, axis=1)
    g = a[..., 1]
    b = np.roll(a[..., 2], px, axis=1)
    return Image.fromarray(np.dstack([r, g, b]))

def slice_displace(img, amp, seed, nbands=14):
    if amp <= 0: return img
    a = np.asarray(img).copy()
    rng = np.random.default_rng(seed)
    edges = np.sort(rng.integers(0, H, nbands * 2))
    for i in range(0, len(edges) - 1, 2):
        y0, y1 = edges[i], edges[i + 1]
        if y1 <= y0: continue
        sh = int(rng.integers(-amp, amp + 1))
        a[y0:y1] = np.roll(a[y0:y1], sh, axis=1)
    return Image.fromarray(a)

def strobe(img, amt, coral=False):
    """Blend toward white (or coral) by amt (0..1)."""
    if amt <= 0: return img
    a = np.asarray(img).astype(np.float32)
    tgt = np.array(CORAL, np.float32) if coral else np.array([245, 245, 245], np.float32)
    a = a * (1 - amt) + tgt * amt
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))

def apply_hits(img, t, frame_idx, extra_glitch=0.0):
    """Generic per-frame hit treatment driven by strong_hits + downbeats."""
    s = near(t, STRONG, 0.055)
    db = near(t, DOWNBEATS, 0.045)
    g = max(s, db * 0.7, extra_glitch)
    if g > 0.05:
        img = rgb_split(img, int(round(6 * g)))
        if g > 0.4:
            img = slice_displace(img, int(6 * g), frame_idx * 7 + 3,
                                 nbands=int(6 + 10 * g))
    # 1-2 frame strobe exactly on strong hits
    sv = near(t, STRONG, 0.9 / FPS)
    if sv > 0.5:
        img = strobe(img, 0.5 * sv, coral=(frame_idx % 2 == 0))
    return img
