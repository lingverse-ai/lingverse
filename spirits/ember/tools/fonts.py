"""找一款粗重字重、带中文的字体（只用开源许可字体）。找不到就下载 Noto Sans SC（OFL）的可变字体。
用法：python3 fonts.py  → 打印字体路径"""
import os, subprocess, sys, urllib.request
from pathlib import Path

CANDIDATES = ["Source Han Sans SC:style=Heavy", "Source Han Sans CN:style=Heavy", "Noto Sans CJK SC:style=Black",
              "Noto Sans SC:style=Black", "Source Han Sans SC:style=Bold", "Noto Sans CJK SC:style=Bold"]
CACHE = Path(os.environ.get("EMBER_HOME", "/workspace/ember")) / "fonts"
NOTO_STATIC = "https://github.com/notofonts/noto-cjk/raw/main/Sans/OTF/SimplifiedChinese/NotoSansCJKsc-Black.otf"


def find_font():
    for name in CANDIDATES:
        r = subprocess.run(["fc-match", "-f", "%{file}|%{style}", name], capture_output=True, text=True)
        path, _, style = r.stdout.partition("|")
        want = name.split("=")[1]
        if path and want.lower() in style.lower() and Path(path).exists():
            return path
    for p in CACHE.glob("*.otf"):
        return str(p)
    CACHE.mkdir(parents=True, exist_ok=True)
    dst = CACHE / "NotoSansCJKsc-Black.otf"
    urllib.request.urlretrieve(NOTO_STATIC, dst)  # SIL OFL 1.1
    return str(dst)


if __name__ == "__main__":
    print(find_font())
