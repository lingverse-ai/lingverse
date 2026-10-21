"""Per-frame subject mattes for the v11 pipeline: fr/<clip>/f_###.jpg -> matte/<clip>/f_###.png
960x540, 8-bit grayscale, full range 0-255 (PNG only; video mattes cap at 235 and let text ghost through).
model: u2net_human_seg (person) | isnet-general-use (pet / object) | any rembg model (birefnet-general ...)."""
import os, sys, time
from rembg import remove, new_session
from PIL import Image
FR, OUT, MODEL = sys.argv[1], sys.argv[2], sys.argv[3]
sess = new_session(MODEL); t0 = time.time(); n = 0
for c in sorted(os.listdir(FR)):
    os.makedirs(os.path.join(OUT, c), exist_ok=True)
    for f in sorted(os.listdir(os.path.join(FR, c))):
        if not f.endswith(".jpg"): continue
        dst = os.path.join(OUT, c, f[:-4] + ".png")
        if os.path.exists(dst): continue
        im = Image.open(os.path.join(FR, c, f)).convert("RGB").resize((960, 540))
        m = remove(im, session=sess, only_mask=True).convert("L")
        lo, hi = m.getextrema()
        if hi > lo and (lo > 0 or hi < 255):   # stretch to full range
            m = m.point(lambda v: max(0, min(255, round((v - lo) * 255 / (hi - lo)))))
        m.save(dst); n += 1
        if n % 60 == 0: print("matte %d  %.1fs" % (n, time.time() - t0), flush=True)
print("mattes: %d new (%s) %.1fs" % (n, MODEL, time.time() - t0))
