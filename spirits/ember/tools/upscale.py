"""放大到 4K：有 Real-ESRGAN（realesrgan-ncnn-vulkan）就用它，没有就 ffmpeg lanczos + 轻锐化（随时可用）。
用法：python3 upscale.py in.mp4 out_4k.mp4 [--size 3840x2160] [--force-ffmpeg]"""
import argparse, shutil, subprocess, tempfile, os

ap = argparse.ArgumentParser(); ap.add_argument("src"); ap.add_argument("out")
ap.add_argument("--size", default="3840x2160"); ap.add_argument("--force-ffmpeg", action="store_true"); g = ap.parse_args()
W, H = g.size.split("x"); esr = shutil.which("realesrgan-ncnn-vulkan")
enc = ["-c:v", "libx264", "-preset", "slow", "-b:v", "60M", "-maxrate", "60M", "-bufsize", "120M", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "320k", "-movflags", "+faststart"]
if esr and not g.force_ffmpeg:  # 逐帧超分（慢，GPU/Vulkan 才实用）
    t = tempfile.mkdtemp(prefix="ember-esr-"); a, b = os.path.join(t, "a"), os.path.join(t, "b"); os.makedirs(a); os.makedirs(b)
    subprocess.run(["ffmpeg", "-v", "error", "-i", g.src, os.path.join(a, "%06d.png")], check=True)
    subprocess.run([esr, "-i", a, "-o", b, "-n", "realesr-animevideov3", "-s", "2"], check=True)
    fps = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=r_frame_rate", "-of", "csv=p=0", g.src],
                         capture_output=True, text=True).stdout.strip()
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-framerate", fps, "-i", os.path.join(b, "%06d.png"), "-i", g.src, "-map", "0:v", "-map", "1:a?",
                    "-vf", f"scale={W}:{H}:flags=lanczos", *enc, g.out], check=True); shutil.rmtree(t); how = "Real-ESRGAN"
else:
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", g.src, "-vf", f"scale={W}:{H}:flags=lanczos,unsharp=5:5:0.6:5:5:0.0", *enc, g.out], check=True)
    how = "ffmpeg lanczos + unsharp"
print(f"OK {g.out} {g.size}（{how}）")
