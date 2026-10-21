"""FUTURE ON THE BLOCK — frame renderer.
Usage:
  python3 render.py --frames 0.6,7.5,13.5,19.5   # render single frames to out/_f_*.png
  python3 render.py --all                          # render all frames to frames/
"""
import os, sys, math, argparse
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import common as C
from common import (W, H, FPS, CREAM, INK, CORAL, BEATS, DOWNBEATS, STRONG,
                    gfont, mfont, sfont, cfont, draw_tracked, text_w,
                    ken_burns, still, ease_out, ease_in_out, clamp01,
                    film_finish, song_envelope, ANTON, ARCHIVO)
import hud as HUD
import fx as FX

OUT = os.path.join(C.ROOT, "out")
FRAMES = os.path.join(C.ROOT, "frames")

# ---------------- text layer helpers ----------------
def text_layer(text, fnt, fill, tracking=0, stroke=0, stroke_fill=None):
    tmp = Image.new("RGBA", (10, 10))
    d = ImageDraw.Draw(tmp)
    tw = int(text_w(d, text, fnt, tracking)) + stroke * 2 + 8
    asc, desc = fnt.getmetrics()
    th = asc + desc + stroke * 2 + 8
    lay = Image.new("RGBA", (tw, th), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    x = stroke + 4
    for ch in text:
        d.text((x, stroke + 2), ch, font=fnt, fill=fill,
               stroke_width=stroke, stroke_fill=stroke_fill)
        x += d.textlength(ch, font=fnt) + tracking
    return lay

def trim(layer):
    bb = layer.split()[3].getbbox()
    return layer.crop(bb) if bb else layer

def giant_layer(word, target_w, color, tracking=6, stroke=0, stroke_fill=None):
    """Anton word scaled so its width ~= target_w (trimmed to glyph bbox)."""
    f = gfont(320)
    lay = trim(text_layer(word, f, color, tracking=tracking, stroke=stroke,
                          stroke_fill=stroke_fill))
    s = target_w / lay.width
    return lay.resize((max(1, int(lay.width * s)), max(1, int(lay.height * s))),
                      Image.LANCZOS)

def giant_layer_h(word, target_h, color, tracking=4, stroke=0, stroke_fill=None):
    """Anton word scaled so its glyph height ~= target_h (trimmed)."""
    f = gfont(320)
    lay = trim(text_layer(word, f, color, tracking=tracking, stroke=stroke,
                          stroke_fill=stroke_fill))
    s = target_h / lay.height
    return lay.resize((max(1, int(lay.width * s)), max(1, int(lay.height * s))),
                      Image.LANCZOS)

def blit(canvas, layer, cx, cy, scale=1.0, alpha=1.0, anchor="mm"):
    if scale != 1.0:
        layer = layer.resize((max(1, int(layer.width * scale)),
                              max(1, int(layer.height * scale))), Image.LANCZOS)
    if alpha < 1.0:
        a = layer.split()[3].point(lambda p: int(p * alpha))
        layer = layer.copy(); layer.putalpha(a)
    x = cx - layer.width // 2 if anchor[0] == "m" else (
        cx if anchor[0] == "l" else cx - layer.width)
    y = cy - layer.height // 2 if anchor[1] == "m" else (
        cy if anchor[1] == "t" else cy - layer.height)
    canvas.alpha_composite(layer, (int(x), int(y)))

def dashed_line(d, p0, p1, col, dash=12, gap=8, width=2):
    x0, y0 = p0; x1, y1 = p1
    L = math.hypot(x1 - x0, y1 - y0)
    if L == 0: return
    ux, uy = (x1 - x0) / L, (y1 - y0) / L
    n = int(L // (dash + gap)) + 1
    for i in range(n):
        a = i * (dash + gap)
        b = min(a + dash, L)
        d.line([(x0 + ux * a, y0 + uy * a), (x0 + ux * b, y0 + uy * b)],
               fill=col, width=width)

def callout(d, tip, label, side="right", color=(233, 93, 62, 255)):
    """Dashed callout: small coral dot at tip, elbow line, mono label."""
    tx, ty = tip
    L = 120
    ex = tx + (L if side == "right" else -L)
    ey = ty - 60
    d.ellipse([tx - 4, ty - 4, tx + 4, ty + 4], fill=color)
    dashed_line(d, (tx, ty), (ex, ey), color, width=2)
    dashed_line(d, (ex, ey), (ex + (40 if side == "right" else -40), ey), color, width=2)
    f = mfont(16, bold=True)
    anchor = "la" if side == "right" else "ra"
    lx = ex + (48 if side == "right" else -48)
    draw_tracked(d, (lx, ey - 10), label, f, (244, 240, 230, 255),
                 tracking=2, anchor=anchor)

def base_canvas(rgb):
    return rgb.convert("RGBA")

# slam animation params for a word appearing at shot start
def slam(t, start, pulse_at=None):
    dt = t - start
    scale = 1.0 + 0.22 * (1 - ease_out(clamp01(dt / 0.12)))
    alpha = clamp01(dt / 0.05)
    if pulse_at is not None:
        pd = t - pulse_at
        scale *= 1 + 0.06 * math.exp(-(pd / 0.05) ** 2)
    return scale, alpha

# ==================================================================
# SHOTS
# ==================================================================
def shot1(t):  # 0.000-1.718  FUTURE
    cv = base_canvas(ken_burns("01_face", (t - 0.0) / 1.718, 1.05, 1.12, (0.5, 0.42)))
    sc, al = slam(t, 0.0, pulse_at=0.627)
    g = giant_layer("FUTURE", 1760, CREAM + (255,), tracking=4)
    blit(cv, g, W // 2, H // 2 - 10, scale=sc, alpha=al)
    # mono slate bar typing (street, not an AI prompt)
    d = ImageDraw.Draw(cv)
    phrase = "xiaoye · live from the block"
    nchar = int(clamp01((t - 0.15) / 1.1) * len(phrase))
    typed = phrase[:nchar]
    cursor = "_" if int(t * 2) % 2 == 0 else " "
    bw, bh = 560, 46
    bx, by = W // 2 - bw // 2, H - 150
    d.rounded_rectangle([bx, by, bx + bw, by + bh], radius=6,
                        fill=(17, 17, 17, 210), outline=(244, 240, 230, 120))
    draw_tracked(d, (bx + 20, by + 12), typed + cursor, mfont(20), (244, 240, 230, 255), 1)
    d.ellipse([bx + bw - 40, by + 8, bx + bw - 8, by + bh - 8], fill=CORAL + (255,))
    d.line([(bx + bw - 30, by + bh // 2), (bx + bw - 18, by + bh // 2)], fill=CREAM + (255,), width=2)
    d.line([(bx + bw - 22, by + bh // 2 - 5), (bx + bw - 18, by + bh // 2)], fill=CREAM + (255,), width=2)
    d.line([(bx + bw - 22, by + bh // 2 + 5), (bx + bw - 18, by + bh // 2)], fill=CREAM + (255,), width=2)
    return cv

def shot2(t):  # 1.718-3.413  ON THE (coral) + outline scroll + glasses callout
    cv = base_canvas(ken_burns("02_sideeye", (t - 1.718) / 1.695, 1.05, 1.11, (0.42, 0.4)))
    d = ImageDraw.Draw(cv)
    # scrolling outline ghost text behind
    scroll = int((t - 1.718) * 150)
    otext = "FUTURE ON THE BLOCK — "
    ol = text_layer(otext * 3, gfont(150), (0, 0, 0, 0), tracking=2,
                    stroke=2, stroke_fill=(244, 240, 230, 60))
    off = -(scroll % (ol.width // 3))
    cv.alpha_composite(ol, (off, 300))
    sc, al = slam(t, 1.718, pulse_at=2.972)
    g = giant_layer("ON THE", 1500, CORAL + (255,), tracking=4)
    blit(cv, g, W // 2, H // 2, scale=sc, alpha=al)
    callout(d, (int(W * 0.30), int(H * 0.30)), "GLASSES · BLACK FRAME", side="left")
    return cv

def shot3(t):  # 3.413-5.131  BLOCK + typewriter lyric (street)
    cv = base_canvas(ken_burns("13_rap_street", (t - 3.413) / 1.718, 1.05, 1.12, (0.5, 0.4)))
    sc, al = slam(t, 3.413)
    g = giant_layer("BLOCK", 1680, CREAM + (255,), tracking=2)
    blit(cv, g, W // 2, H // 2 - 20, scale=sc, alpha=al)
    d = ImageDraw.Draw(cv)
    line = "FUTURE ON THE BLOCK · WE DON'T EVER STOP"
    nchar = int(clamp01((t - 3.6) / 1.1) * len(line))
    typed = line[:nchar]
    fc = mfont(30, bold=True)
    tx = W // 2
    bar_y = H - 176
    tw = text_w(d, typed, fc, 2)
    d.rectangle([tx - tw // 2 - 20, bar_y - 10, tx + tw // 2 + 20, bar_y + 52],
                fill=(17, 17, 17, 180))
    d.rectangle([tx - tw // 2 - 20, bar_y - 10, tx - tw // 2 - 15, bar_y + 52],
                fill=CORAL + (255,))
    draw_tracked(d, (tx, bar_y + 6), typed, fc, (244, 240, 230, 255), 2, anchor="ma")
    return cv

def _crush_watch(img):
    """Crush shadows + heavier grain so the darker hand/skin mismatch is hidden."""
    a = np.asarray(img).astype(np.float32)
    a = np.clip((a - 34) * 1.28, 0, 255)          # lift black point, add contrast
    rng = np.random.default_rng(777)
    a = a + rng.standard_normal(a.shape[:2])[..., None].astype(np.float32) * 17.0
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))

def shot4(t):  # 5.131-6.850  hero base; watch only as quick crushed flashes
    # watch flex flashes (<=0.5s each) on the brief's hit marks 5.758 & 6.2
    for ft in (5.758, 6.2):
        if ft <= t < ft + 0.30:
            w = ken_burns("04_watch", (t - ft) / 0.30, 1.08, 1.13, (0.5, 0.5))
            cv = base_canvas(_crush_watch(w))
            d = ImageDraw.Draw(cv)
            callout(d, (int(W * 0.42), int(H * 0.52)), "AP ROYAL OAK · ICED", side="right")
            callout(d, (int(W * 0.30), int(H * 0.30)), "CUBAN LINK · 14K", side="left")
            HUD.coral_star(d, int(W * 0.42), int(H * 0.52), 26)
            return cv
    # base: confident hero, no watch
    cv = base_canvas(ken_burns("00_hero", (t - 5.131) / 1.719, 1.05, 1.12, (0.45, 0.4)))
    d = ImageDraw.Draw(cv)
    draw_tracked(d, (150, H - 150), "ICED OUT · XIAOYE", mfont(22, bold=True),
                 (244, 240, 230, 255), 2)
    return cv

def shot5(t):  # 6.850-8.568  terminal prompt + serif 'soul' cropped right
    cv = base_canvas(ken_burns("03_mic", (t - 6.85) / 1.718, 1.05, 1.11, (0.5, 0.4)))
    # dim the photo for terminal readability
    ov = Image.new("RGBA", (W, H), (10, 10, 12, 150))
    cv.alpha_composite(ov)
    d = ImageDraw.Draw(cv)
    lines = [
        "> track 01 // xiaoye // live from the block",
        "> mic check ... [ok]",
        "they said 机器抢饭碗,",
        "i said 机器是我兵",
        "不靠公司 不靠钱,",
        "靠的是脑子够狠",
        "future on the block,",
        "未来就在眼前",
        "> bars loaded ... [100%]",
    ]
    coral_tokens = {"[ok]", "[100%]", "机器是我兵", "block,", "future"}
    base_col = (236, 236, 230, 235)
    scroll = int((t - 6.85) * 42)
    y0 = 240 - scroll
    for i, ln in enumerate(lines):
        y = y0 + i * 42
        if not (-42 < y < H):
            continue
        if any(ord(c) > 0x2E00 for c in ln):  # CJK line -> per-char fallback
            col = CORAL + (255,) if ln in coral_tokens else base_col
            draw_mixed(d, (150, y), ln, size=27, col=col)
        else:
            x = 150
            fm = mfont(27, med=True)
            for tok in ln.split(" "):
                col = CORAL + (255,) if tok.lower() in coral_tokens else base_col
                d.text((x, y), tok, font=fm, fill=col)
                x += d.textlength(tok + " ", font=fm)
    # serif accent 'flow' cropped off right edge
    sl = text_layer("flow", sfont(380), CORAL + (255,))
    cv.alpha_composite(sl, (W - 300, H - 360))
    return cv

def shot6(t):  # 8.568-10.286  STREET word card + 1f inserts
    # 1-frame inserts on strong hits
    inserts = {8.754: "01_face", 8.986: "13_rap_street", 9.822: "00_hero"}
    for ht, nm in inserts.items():
        if abs(t - ht) < 0.55 / FPS:
            return base_canvas(ken_burns(nm, 0.3, 1.08, 1.08, (0.5, 0.4)))
    cv = base_canvas(ken_burns("11_studio", (t - 8.568) / 1.718, 1.05, 1.10, (0.5, 0.42)))
    sc, al = slam(t, 8.568)
    g = giant_layer("STREET", 1600, CREAM + (255,), tracking=4)
    blit(cv, g, int(W * 0.42), int(H * 0.34), scale=sc, alpha=al, anchor="mm")
    d = ImageDraw.Draw(cv)
    draw_tracked(d, (150, H - 150), "XIAOYE · FUTURE ON THE BLOCK", mfont(22, bold=True),
                 (244, 240, 230, 255), 2)
    return cv

def shot7(t):  # 10.286-12.005  MIC coral + mask neon signs
    cv = base_canvas(ken_burns("12_walk", (t - 10.286) / 1.719, 1.04, 1.10, (0.5, 0.45)))
    # blur the garbled neon shop signs: upper-left & upper-right regions
    for (x0, y0, x1, y1) in [(120, 120, 560, 420), (1360, 120, 1800, 420)]:
        region = cv.crop((x0, y0, x1, y1)).filter(ImageFilter.GaussianBlur(16))
        cv.paste(region, (x0, y0))
    sc, al = slam(t, 10.286)
    g = giant_layer("MIC", 1120, CORAL + (255,), tracking=4)
    blit(cv, g, W // 2, int(H * 0.5), scale=sc, alpha=al)
    d = ImageDraw.Draw(cv)
    draw_tracked(d, (150, H - 150), "XIAOYE · TRACK 01", mfont(22, bold=True),
                 (244, 240, 230, 255), 2)
    return cv

def shot8(t):  # 12.005-12.864  BLOCK + waveform
    cv = base_canvas(ken_burns("14_fence", (t - 12.005) / 0.859, 1.05, 1.09, (0.5, 0.4)))
    sc, al = slam(t, 12.005)
    g = giant_layer("BLOCK", 1180, INK + (255,), tracking=4)
    blit(cv, g, int(W * 0.34), int(H * 0.42), scale=sc, alpha=al)
    d = ImageDraw.Draw(cv)
    nb = 90
    env = song_envelope(nb, t - 0.02, t + 0.10)
    env2 = song_envelope(nb, 12.005, 12.864)
    env = 0.5 * env + 0.5 * env2
    base_y = int(H * 0.82)
    bw = (W - 300) / nb
    for i, v in enumerate(env):
        x = 150 + i * bw
        h = int(6 + v * 150)
        d.rectangle([x, base_y - h, x + bw * 0.6, base_y + h], fill=CORAL + (255,))
    return cv

def shot9(t):  # 12.864-15.441 HOOK2 AI IS THE FUTURE one per beat
    cv = base_canvas(ken_burns("08_rooftop", (t - 12.864) / 2.577, 1.06, 1.14, (0.5, 0.35)))
    words = [("AI", 12.864, CORAL), ("IS", 13.282, CREAM), ("THE", 13.723, CREAM),
             ("FUTURE", 14.141, CORAL)]
    cur = None
    for i, (w, st, col) in enumerate(words):
        nxt = words[i + 1][1] if i + 1 < len(words) else 15.441
        if st <= t < nxt:
            cur = (w, st, col); break
    if cur is None and t >= 14.141:
        cur = ("FUTURE", 14.141, CORAL)
    if cur:
        w, st, col = cur
        sc, al = slam(t, st)
        tw = 900 if len(w) <= 3 else 1760
        g = giant_layer(w, tw, col + (255,), tracking=4)
        blit(cv, g, W // 2, H // 2, scale=sc, alpha=al)
    return cv

def shot10(t):  # 15.441-17.136 montage one still per beat + ON THE BLOCK
    seq = [(15.441, "00_hero"), (15.882, "01_face"), (16.3, "13_rap_street"),
           (16.718, "03_mic"), (17.0, "00_hero")]
    nm = seq[0][1]
    for st, n in seq:
        if t >= st: nm = n
    cv = base_canvas(ken_burns(nm, 0.4, 1.08, 1.12, (0.5, 0.4)))
    g = giant_layer("ON THE BLOCK", 1780, CREAM + (255,), tracking=3)
    blit(cv, g, W // 2, int(H * 0.5), scale=1.0, alpha=1.0)
    return cv

def shot11(t):  # 17.136-21.010  00_hero -> 10_title final card
    if t < 18.854:
        cv = base_canvas(ken_burns("00_hero", (t - 17.136) / 1.718, 1.05, 1.12, (0.45, 0.4)))
        d = ImageDraw.Draw(cv)
        # clean hero bridge: lower-third mono lyric, no giant word
        lyric = "Future on the block · 未来就在眼前"
        bw = 760; bx = W // 2 - bw // 2; by = H - 164
        d.rectangle([bx, by, bx + bw, by + 52], fill=(17, 17, 17, 170))
        d.rectangle([bx, by, bx + 5, by + 52], fill=CORAL + (255,))
        draw_mixed(d, (bx + 22, by + 14), lyric, size=24, col=(244, 240, 230, 255))
        return cv
    # final title card over cream (10_title already a cream backdrop)
    photo = ken_burns("10_title", (t - 18.854) / 2.156, 1.04, 1.08, (0.62, 0.42))
    cream = Image.new("RGB", (W, H), CREAM)
    mask = Image.new("L", (W, H), 0)
    md = ImageDraw.Draw(mask)
    md.rectangle([0, 0, int(W * 0.55), H], fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(80))
    comp = Image.composite(cream, photo, mask)
    cv = base_canvas(comp)
    d = ImageDraw.Draw(cv)
    tin = t - 18.854
    # stacked FUTURE / ON THE / BLOCK building in — height-based, tight leading
    TH = 150; LEAD = 150; X0 = 120; YB = 210
    lines = [("FUTURE", 18.854), ("ON THE", 19.12), ("BLOCK", 19.40)]
    for i, (wline, st) in enumerate(lines):
        if t < st: continue
        dt = t - st
        y = YB + i * LEAD
        if dt < 0.20:  # glitch-mask entry: photo fills the letters
            maskL = giant_layer_h(wline, TH, (255, 255, 255, 255), tracking=2).split()[3]
            crop = photo.crop((X0, y, X0 + maskL.width, y + maskL.height)).convert("RGBA")
            crop.putalpha(maskL)
            jit = int(7 * (1 - dt / 0.20))
            cv.alpha_composite(crop, (X0 + (jit if i % 2 else -jit), y))
        else:
            gl = giant_layer_h(wline, TH, INK + (255,), tracking=2)
            cv.alpha_composite(gl, (X0, y))
    stack_bottom = YB + 3 * LEAD
    # underline rule + coral star
    if tin > 0.62:
        ry = stack_bottom + 18
        d.line([(X0 + 6, ry), (X0 + 700, ry)], fill=INK + (255,), width=5)
        HUD.coral_star(d, X0 + 742, ry, 18)
    # typewriter mono subtitle lines
    if tin > 0.85:
        sub = [
            "XIAOYE",
            "FUTURE ON THE BLOCK · TRACK 01",
            "143.6 BPM · live from the block, brooklyn",
        ]
        fy = stack_bottom + 56
        allchars = sum(len(s) for s in sub)
        nchar = int(clamp01((tin - 0.85) / 1.0) * allchars)
        used = 0
        for s in sub:
            seg = s[:max(0, nchar - used)]
            draw_mixed(d, (X0 + 6, fy), seg, size=25, col=INK + (255,))
            used += len(s); fy += 44
            if used >= nchar and nchar < allchars:
                break
    # dashed coral line + star pointing to his glasses (right side)
    if tin > 1.0:
        tipx, tipy = int(W * 0.80), int(H * 0.40)
        dashed_line(d, (X0 + 742, stack_bottom + 18), (tipx, tipy), CORAL + (230,), width=2)
        HUD.coral_star(d, tipx, tipy, 13)
    # final fade to black last 0.3s
    if t > 20.7:
        fade = clamp01((t - 20.7) / 0.3)
        cv.alpha_composite(Image.new("RGBA", (W, H), (0, 0, 0, int(255 * fade))))
    return cv

def draw_mixed(d, xy, seg, size=26, col=INK + (255,)):
    """Draw a string mixing mono (latin) + CJK, falling back per character."""
    x, y = xy
    fm = mfont(size, med=True); fc = cfont(size)
    for ch in seg:
        if ord(ch) > 0x2E00:
            d.text((x, y - 2), ch, font=fc, fill=col)
            x += fc.getlength(ch) + 1
        else:
            d.text((x, y), ch, font=fm, fill=col)
            x += d.textlength(ch, font=fm) + 1

# scene metadata per shot
SHOTS = [
    (0.0, 1.718, shot1, 1, "FUTURE"),
    (1.718, 3.413, shot2, 2, "ON THE"),
    (3.413, 5.131, shot3, 3, "BLOCK"),
    (5.131, 6.85, shot4, 4, "ICED"),
    (6.85, 8.568, shot5, 5, "THE FLOW"),
    (8.568, 10.286, shot6, 6, "STREET"),
    (10.286, 12.005, shot7, 7, "MIC"),
    (12.005, 12.864, shot8, 8, "BLOCK"),
    (12.864, 15.441, shot9, 9, "THE FUTURE"),
    (15.441, 17.136, shot10, 10, "MONTAGE"),
    (17.136, 21.01, shot11, 11, "OUTRO"),
]

def render_frame(frame_idx):
    t = frame_idx / FPS
    for (s, e, fn, no, name) in SHOTS:
        if s <= t < e or (e >= 21.0 and t >= s):
            cv = fn(t)
            scene_no, scene_name = no, name
            break
    rgb = cv.convert("RGB")
    rgb = FX.apply_hits(rgb, t, frame_idx)
    # HUD under finish
    cv2 = rgb.convert("RGBA")
    crosshair = None
    HUD.draw_hud(cv2, t, scene_no, scene_name, show_grid=True, crosshair=crosshair)
    rgb = cv2.convert("RGB")
    out = film_finish(rgb, frame_idx)
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--frames", type=str, default="")
    ap.add_argument("--all", action="store_true")
    args = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(FRAMES, exist_ok=True)
    if args.frames:
        for i, ts in enumerate(args.frames.split(",")):
            fi = int(round(float(ts) * FPS))
            img = render_frame(fi)
            p = os.path.join(OUT, "_f_%.2f.png" % float(ts))
            img.save(p)
            print("wrote", p)
    if args.all:
        import time
        t0 = time.time()
        for fi in range(C.NFRAMES):
            img = render_frame(fi)
            img.save(os.path.join(FRAMES, "f_%04d.png" % fi))
            if fi % 48 == 0:
                print("frame %d/%d  %.1fs" % (fi, C.NFRAMES, time.time() - t0))
        print("done all in %.1fs" % (time.time() - t0))

if __name__ == "__main__":
    main()
