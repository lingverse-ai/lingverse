"""Ember v11 driver: runs the ORIGINAL v11 pipeline (src/render_v11.py, render_v10.py,
common.py untouched) for any project. Only swaps data: shot list, words + timing
(from project.json), beatmap (music-driven), HUD/end-card strings.
Generalised from v8run/src/run_v8.py (approved v8). Executed inside a run root built
by tools/render.py:  <runroot>/src -> v11 code, <runroot>/pack_v5/work/{fr,matte,out_frames}.
Usage: python3 <runroot>/src/driver.py <runroot>/v11cfg.json frames 6.0,10.2 [outdir]
       python3 <runroot>/src/driver.py <runroot>/v11cfg.json all <jobs>
       python3 <runroot>/src/driver.py <runroot>/v11cfg.json qc <outdir>
"""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import render_v11 as V
import render as R
import hud as HUD
from common import draw_tracked, clamp01, ease_in_out
from PIL import Image, ImageDraw

G = json.load(open(sys.argv[1]))
INTRO_END, END_T = G["intro_end"], G["end_t"]
V.CUTS = [(s["in"], s["id"], 0.0) for s in G["shots"]] + [(END_T, "endcard", 0.0)]
V.CLIP_WINDOW = {s["id"]: (0, len(os.listdir(os.path.join(V.FR, s["id"])))/24) for s in G["shots"]}
V.DUR = G["duration"]; V.NF = int(round(V.DUR * V.FPS)); V.ENDCARD_T = END_T
CORALS = ("#F07A5F", "#F07A4A")
def col(c): return V.CORAL if c.upper() in CORALS or c.lower() == "coral" else V.CREAM
words = [(w["t"], w["text"].upper(), col(w["color"]), w.get("style", "solid")) for w in G["words"]]
V.WORDS = [x for x in words if INTRO_END - 1e-3 <= x[0] < END_T]
V._INTRO_WORDS = [(x[0], x[1], ("wsolid", "outline", "wsolid", "orangepanel", "blackpanel", "wsolid")[i % 6])
                  for i, x in enumerate(words) if x[0] < INTRO_END]
V.RAP_LINES = []
def active_word(t):   # = V.active_word minus the v11-only serif "FUTURE" at 3.0-4.273 (never hit in v8)
    if t < INTRO_END: return None
    cur = None
    for i, w in enumerate(V.WORDS):
        if w[0] <= t:
            nxt = V.WORDS[i + 1][0] if i + 1 < len(V.WORDS) else V.ENDCARD_T
            cur = (w[0], nxt, w[1], w[2], w[3])
        else:
            break
    return cur
V.active_word = active_word

TM = G.get("text_map", {})   # hud.py hardcoded strings -> project strings (end-card HUD)
_hud_dt = HUD.draw_tracked
def _dt(d, xy, text, *a, **k): return _hud_dt(d, xy, TM.get(text, text), *a, **k)
HUD.draw_tracked = _dt
V.draw_tracked = _dt   # intro node diagram etc. in render_v11 also go through the project text_map
TERM = G.get("terminal")
def rap_terminal(cv, t):   # = V.rap_terminal with project header + window
    if not TERM or not (TERM["from"] <= t < TERM["to"]): return
    d = ImageDraw.Draw(cv); fm = V.mono(23, True); x0, y0 = 110, 235
    header = [(TERM["lines"][0], V.WHITE, TERM["from"]), (TERM["lines"][1], V.RED, TERM["from"] + 0.373)]
    y = y0
    for (txt, col, lt) in header:
        if t < lt: break
        n = int(clamp01((t - lt) / 0.9) * len(txt)); seg = txt[:n]
        hl = V.RED + (255,) if "[OK]" in txt or "[100%]" in txt else col + (235,)
        draw_tracked(d, (x0, y), seg, fm, hl, 1); y += 38
V.rap_terminal = rap_terminal

# ---- HUD strings / chapters / end card: same v11 code, project strings ----
HC = G["hud"]
def chapter(t):
    cur = HC["chapters"][0][1]
    for ct, lab in HC["chapters"]:
        if t >= ct: cur = lab
    return cur
V.chapter = chapter
def draw_hud(cv, t):   # = V.draw_hud with project title/subtitle
    W, H, mono = V.W, V.H, V.mono
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
    I = 46; wcol = V.WHITE + (220,); gcol = V.GREY + (190,); rcol = V.RED + (255,)
    for (x, y, dx, dy) in [(I, I, 1, 1), (W - I, I, -1, 1), (I, H - I, 1, -1), (W - I, H - I, -1, -1)]:
        d.line([(x, y), (x + dx * 26, y)], fill=(236, 236, 230, 150), width=2)
        d.line([(x, y), (x, y + dy * 26)], fill=(236, 236, 230, 150), width=2)
    draw_tracked(d, (I + 30, I - 6), HC["title"], mono(18, True), wcol, 2)
    draw_tracked(d, (I + 30, I + 18), HC["subtitle"], mono(13), gcol, 2)
    fb = mono(18, True); bx = W - I - 30
    nb = min(V.BEATS, key=lambda b: abs(b - t)); ph = max(0.0, 1 - abs(t - nb) / 0.11)
    bars = 7; bw = 7; gap = 4; eqw = bars * bw + (bars - 1) * gap
    draw_tracked(d, (bx - eqw - 14, I - 6), "%.1f BPM" % V.BPM, fb, wcol, 2, anchor="ra")
    ex = bx - eqw; yb = I + 2
    for i in range(bars):
        lv = (0.3 + 0.7 * ph) if i <= int(ph * bars) else 0.22
        hh = int(18 * lv); c = rcol if (i == int(ph * bars) and ph > 0.3) else (236, 236, 230, 170)
        d.rectangle([ex + i * (bw + gap), yb + (18 - hh), ex + i * (bw + gap) + bw, yb + 18], fill=c)
    draw_tracked(d, (I + 30, H - I - 16), V.tc(t), mono(16), wcol, 1)
    cur = "_" if int(t * 2) % 2 == 0 else " "
    draw_tracked(d, (W - I - 30, H - I - 16), chapter(t) + cur, mono(16, True), wcol, 2, anchor="ra")
    cv.alpha_composite(ov)
V.draw_hud = draw_hud
EC = G["endcard"]
def render_endcard(t):   # = V.render_endcard with project lines
    W, H = V.W, V.H; tin = t - END_T
    push = 1.02 + 0.045 * ease_in_out(min(1.0, tin / 3.0))
    im = V.V8._endcard_still(); nw, nh = int(W * push), int(H * push)
    im = im.resize((nw, nh), Image.LANCZOS)
    left = int((nw - W) * 0.30); top = int((nh - H) * 0.42)
    cv = im.crop((left, top, left + W, top + H)).convert("RGBA"); d = ImageDraw.Draw(cv)
    TH, LEAD = 150, 158; RX = W - 70; YB = 180
    lines = [tuple(l) for l in EC["lines"]]
    for k, (wline, wt, outline) in enumerate(lines):
        if t < wt: continue
        y = YB + k * LEAD; al = clamp01((t - wt) / 0.14)
        gl = V.V8.giant_v5_h(wline, TH, (0, 0, 0, 0), stroke=5, stroke_fill=V.INK + (255,)) if outline \
            else V.V8.giant_v5_h(wline, TH, V.INK + (255,))
        R.blit(cv, gl, RX - gl.width // 2, y + gl.height // 2, scale=1.0, alpha=al, anchor="mm")
    sb = YB + 3 * LEAD
    if tin > 0.95:
        d.line([(RX - 540, sb + 14), (RX - 8, sb + 14)], fill=(196, 60, 44, 255), width=4)
        HUD.coral_star(d, RX - 578, sb + 14, 18)
    if tin > 1.15:
        fm = V.mono(25, True)
        for k, s in enumerate(EC["credits"]):
            draw_tracked(d, (RX, sb + 50 + k * 44), s, fm, V.INK + (255,), 1, anchor="ra")
    if t > V.DUR - 0.6:
        f = clamp01((t - (V.DUR - 0.6)) / 0.6)
        cv.alpha_composite(Image.new("RGBA", (W, H), (0, 0, 0, int(230 * f))))
    return cv
V.render_endcard = render_endcard

def intro_frame(t):   # v11 intro (per-beat big words + panels), project intro length
    cv = Image.new("RGBA", (V.W, V.H), (8, 8, 9, 255)); d = ImageDraw.Draw(cv)
    cur = None
    for w in V._INTRO_WORDS:
        if w[0] <= t: cur = w
    if cur:
        wt, txt, style = cur; dt = t - wt; punch = 1.06 - 0.06 * V.clamp01(dt / (4 / V.FPS))
        lay = V._intro_word(txt, style); sw, sh = int(lay.width * punch), int(lay.height * punch)
        lw = lay.resize((sw, sh), Image.LANCZOS); px, py = V.W // 2 - sw // 2, int(V.H * 0.5) - sh // 2
        if style == "blackpanel": d.rectangle([px - 40, py - 20, px + sw + 40, py + sh + 20], fill=V.WHITE + (255,))
        elif style == "orangepanel": d.rectangle([px - 40, py - 20, px + sw + 40, py + sh + 20], fill=V.ORANGE + (255,))
        cv.alpha_composite(lw, (px, py))
    return cv

PROBE = {}
def render_frame(fi):
    t = fi / V.FPS
    if t < INTRO_END:
        rgb = intro_frame(t).convert("RGB"); rgb = V.beatfx(rgb, t, fi)
        cv2 = rgb.convert("RGBA"); V.draw_hud(cv2, t); return V.finish_v11(cv2.convert("RGB"), fi)
    if t >= END_T:
        cv = V.render_endcard(t); cv2 = cv.convert("RGB").convert("RGBA")
        V.HUD.draw_hud(cv2, t, 13, "OUTRO", show_grid=False); return V.finish_v11(cv2.convert("RGB"), fi)
    ct, clip, src0 = V.active_cut(t); dt = t - ct
    z = V.beat_zoom(t, ct, 0.07, dur=0.16)
    rgb, matte = V.clip_frame(clip, src0 + dt, zoom=z, focus=(0.5, 0.52), want_matte=True)
    bg = rgb.convert("RGBA")
    cv = V.place_word(bg, matte, t)
    PROBE.update(bg=bg, matte=matte, comp=cv, word=V.active_word(t))
    V.rap_terminal(cv, t)
    rgb = V.beatfx(cv.convert("RGB"), t, fi); cv2 = rgb.convert("RGBA"); V.draw_hud(cv2, t)
    return V.finish_v11(cv2.convert("RGB"), fi)

def leak(fi):
    """Text-behind-subject check on frame fi. Returns (leak_fraction, n_core_px).
    Core = matte >= 200, eroded 8 px (subject interior, edges excluded) - so a capped/weak matte
    (e.g. video mattes topping out at 235) still counts as subject and its ghosting is caught. Leak = core px where the composite differs from
    the plain plate by > 6 levels AND moved toward the word colour."""
    PROBE.clear(); render_frame(fi)
    if not PROBE or PROBE["word"] is None or PROBE["matte"] is None: return None
    from PIL import ImageFilter
    m = np.asarray(PROBE["matte"].point(lambda v: 255 if v >= 200 else 0).filter(ImageFilter.MinFilter(17))) > 0
    if m.sum() < 500: return None
    bg = np.asarray(PROBE["bg"].convert("RGB")).astype(int); co = np.asarray(PROBE["comp"].convert("RGB")).astype(int)
    colr = np.array(PROBE["word"][3] if len(PROBE["word"]) > 3 else V.CREAM)
    # leak = subject px pulled toward the word colour (catches full text AND faint ghosting)
    diff = np.abs(co - bg).max(-1) > 6
    toward = np.abs(co - colr).sum(-1) < np.abs(bg - colr).sum(-1) - 12
    bad = m & diff & toward
    return float(bad.sum()) / float(m.sum()), int(m.sum())

def work(rng):
    os.makedirs(V.FRAMES, exist_ok=True)
    for fi in rng:
        p = os.path.join(V.FRAMES, "f_%04d.png" % fi)
        if not os.path.exists(p): render_frame(fi).save(p)

if __name__ == "__main__":
    mode = sys.argv[2]
    if mode == "frames":
        out = sys.argv[4] if len(sys.argv) > 4 else os.path.join(os.path.dirname(sys.argv[1]), "test_frames")
        os.makedirs(out, exist_ok=True)
        for ts in sys.argv[3].split(","):
            p = os.path.join(out, "t_%06.3f.png" % float(ts)); render_frame(int(round(float(ts) * 30))).save(p); print(p)
    elif mode == "qc":
        out = sys.argv[3]; os.makedirs(out, exist_ok=True)
        ts = [float(x) for x in sys.argv[4].split(",")]
        res = []
        for t in ts:
            fi = int(round(t * 30)); r = leak(fi)
            img = render_frame(fi); img.save(os.path.join(out, "q_%06.3f.png" % t))
            res.append({"t": t, "leak": None if r is None else round(r[0], 5), "core_px": None if r is None else r[1]})
            print(json.dumps(res[-1]), flush=True)
        json.dump(res, open(os.path.join(out, "leak.json"), "w"), indent=1)
    else:
        from multiprocessing import Pool
        n = int(sys.argv[3]); fr = list(range(V.NF))
        with Pool(n) as pool: pool.map(work, [fr[i::n] for i in range(n)])
