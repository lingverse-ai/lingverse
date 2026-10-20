"""生成流萤自带的调色 LUT（.cube，17³），纯数学公式，灵境以 CC0 1.0 发布。
用法：python3 make_luts.py ../luts"""
import sys
from pathlib import Path
import numpy as np

N = 17


def sat(c, s):
    l = (c * [0.2126, 0.7152, 0.0722]).sum(-1, keepdims=True); return l + (c - l) * s


def lift_gamma_gain(c, lift=0.0, gamma=1.0, gain=1.0):
    return np.clip((c * gain + lift * (1 - c)), 0, 1) ** (1 / gamma)


def split(c, shadow, high, amt=0.08):  # 暗部/亮部分别染色
    l = (c * [0.2126, 0.7152, 0.0722]).sum(-1, keepdims=True)
    return c + (1 - l) ** 2 * (np.array(shadow) - 0.5) * amt * 2 + l ** 2 * (np.array(high) - 0.5) * amt * 2


def s_curve(c, k=0.15):  # S 形对比
    return np.clip(c + k * (c - 0.5) * (1 - abs(2 * c - 1)), 0, 1)


LOOKS = {  # 名称: (说明, 变换)
    "v11-street": ("v11 同款：压暗部、暖亮部青暗部、略降饱和", lambda c: sat(split(s_curve(lift_gamma_gain(c, -0.03, 0.95)), [0.40, 0.55, 0.58], [0.62, 0.52, 0.42]), 0.85)),
    "cyber-neon": ("赛博街头：品红亮部、青暗部、高饱和", lambda c: sat(split(s_curve(c, 0.25), [0.35, 0.55, 0.70], [0.70, 0.40, 0.65], 0.12), 1.25)),
    "guofeng-ink": ("国风：暖纸色、玉青暗部、低饱和、柔对比", lambda c: sat(split(lift_gamma_gain(c, 0.04, 1.02, 0.97), [0.42, 0.58, 0.52], [0.62, 0.56, 0.44]), 0.70)),
    "retro-film": ("复古胶片：抬黑、暖黄、轻褪色", lambda c: sat(split(lift_gamma_gain(c, 0.07, 1.0, 0.94), [0.48, 0.50, 0.55], [0.66, 0.56, 0.40], 0.10), 0.80)),
    "anime-bright": ("动漫：提亮、高饱和、偏冷天空", lambda c: sat(split(lift_gamma_gain(c, 0.02, 1.12), [0.45, 0.52, 0.62], [0.55, 0.53, 0.48]), 1.30)),
    "voxel-pop": ("方块世界：鲜艳、强对比、暖金亮部", lambda c: sat(split(s_curve(c, 0.2), [0.45, 0.50, 0.62], [0.65, 0.55, 0.38]), 1.35)),
}


def write(path, f, title):
    g = np.linspace(0, 1, N)
    b, gg, r = np.meshgrid(g, g, g, indexing="ij")  # .cube：红变化最快
    c = np.clip(f(np.stack([r, gg, b], -1).reshape(-1, 3)), 0, 1)
    lines = [f'TITLE "{title}"', "# Lingverse Ember LUT, CC0 1.0 (public domain dedication)", f"LUT_3D_SIZE {N}"]
    lines += [f"{x:.5f} {y:.5f} {z:.5f}" for x, y, z in c]
    Path(path).write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "luts"); out.mkdir(parents=True, exist_ok=True)
    for name, (desc, f) in LOOKS.items():
        write(out / f"{name}.cube", f, name); print(name, "—", desc)
