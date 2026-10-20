"""人像抠像：视频/图片 → 灰度遮罩视频（白=人，黑=背景），给 render.py 做「字压在人身后」。CPU 就能跑。
依赖：pip install "rembg[cpu]"（第一次运行自动下载 u2netp 模型 4.6MB；要更细可用 --model u2net_human_seg 170MB）。
用法：python3 matte.py in.mp4 mask.mp4 [--width 512] [--model u2netp]
      python3 matte.py in.png mask.png"""
import argparse, subprocess, sys, json
import numpy as np


def session(model):
    try:
        from rembg import new_session
    except ImportError:
        sys.exit('MATTE_DEPS_MISSING：先运行 pip install "rembg[cpu]"')
    return new_session(model)


def mask_frame(sess, rgb):
    from rembg import remove
    from PIL import Image
    m = remove(Image.fromarray(rgb), session=sess, only_mask=True, post_process_mask=True)
    return np.asarray(m, dtype=np.uint8)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("src"); ap.add_argument("out")
    ap.add_argument("--width", type=int, default=512, help="推理宽度（越小越快，遮罩会被放大并羽化）")
    ap.add_argument("--model", default="u2netp"); g = ap.parse_args()
    sess = session(g.model)
    if g.src.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
        from PIL import Image
        im = Image.open(g.src).convert("RGB"); W, H = im.size
        m = mask_frame(sess, np.asarray(im.resize((g.width, round(H * g.width / W / 2) * 2))))
        Image.fromarray(m).resize((W, H)).save(g.out); print("OK", g.out); return
    pr = json.loads(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height,r_frame_rate",
                                    "-of", "json", g.src], capture_output=True, text=True).stdout)["streams"][0]
    W, H, fps = pr["width"], pr["height"], pr["r_frame_rate"]
    w = g.width; h = round(H * w / W / 2) * 2
    dec = subprocess.Popen(["ffmpeg", "-v", "error", "-i", g.src, "-vf", f"scale={w}:{h}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                           stdout=subprocess.PIPE)
    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "gray", "-s", f"{w}x{h}", "-r", fps, "-i", "-",
                            "-vf", f"scale={W}:{H}:flags=bicubic,gblur=sigma=1.5", "-pix_fmt", "yuv420p", "-c:v", "libx264", "-crf", "12", g.out],
                           stdin=subprocess.PIPE)
    n = 0
    while True:
        buf = dec.stdout.read(w * h * 3)
        if len(buf) < w * h * 3: break
        enc.stdin.write(mask_frame(sess, np.frombuffer(buf, np.uint8).reshape(h, w, 3)).tobytes()); n += 1
    enc.stdin.close(); enc.wait(); dec.wait()
    print(f"OK {g.out} {n} 帧（推理 {w}x{h}，输出 {W}x{H}）")


if __name__ == "__main__":
    main()
