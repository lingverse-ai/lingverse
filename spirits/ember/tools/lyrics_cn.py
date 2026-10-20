"""中文歌词体检（给 Suno 用之前跑一遍）。依赖：pip install pypinyin（没有也能跑，只是没有押韵/声调/多音字）。
用法：python3 lyrics_cn.py lyrics.txt --bpm 140 [--mode rap|sing] [--style "Suno 风格框原文"] [--json out.json]
逐行检查：
  字数 vs 槽位：唱的歌一行 = 2 小节（0.75–1.5 字/拍）；快说唱（≥110 BPM）一行 = 1 小节（1.25–3.5 字/拍）。
             英文词按音节估。按 v11《未来街区》实测校准：140 BPM 下「Future on the block, 未来就在眼前」
             11 个音节唱了 1.86 秒 ≈ 1 小节 ≈ 2.75 字/拍。--bars 可手动改。
  押韵：行尾字的韵母归入十三辙，同一段相邻行不同辙就提示。
  声调：行尾声调走向；一行里连续 3 个以上第三声，Suno 常唱糊。
  多音字：Suno 可能读错的字，提示按上下文该读什么，建议换同音不歧义的字。
  Suno 格式：括号会被唱成和声；阿拉伯数字要写成汉字；段落标记用英文 [Verse]/[Chorus]；中英混写要在风格里写明。
  AI 套话：一眼 AI 味的词（星辰大海、追逐梦想…），建议换成具体画面。"""
import argparse, json, re, sys

ap = argparse.ArgumentParser(); ap.add_argument("lyrics"); ap.add_argument("--bpm", type=float, default=120)
ap.add_argument("--mode", choices=["rap", "sing"], default=None); ap.add_argument("--style", default="")
ap.add_argument("--bars", type=float, default=None); ap.add_argument("--json")
g = ap.parse_args()
try:
    from pypinyin import pinyin, Style, lazy_pinyin
except ImportError:
    pinyin = None

HAN = re.compile(r"[\u4e00-\u9fff]")
EN = re.compile(r"[A-Za-z']+")
RAPWORDS = ("rap", "trap", "hip hop", "hip-hop", "drill", "说唱", "boom bap", "grime")
mode = g.mode or ("rap" if any(w in g.style.lower() for w in RAPWORDS) else "sing")
lo, hi = (1.25, 3.5) if mode == "rap" else (0.75, 1.5)
if g.bars is None: g.bars = 1 if mode == "rap" and g.bpm >= 110 else 2  # v11 实测：140 BPM 说唱 Suno 一行塞进 1 小节
beats = 4 * g.bars

# 十三辙（简化）：按韵母归类
ZHE = {"发花": "a ia ua", "梭波": "o e uo", "乜斜": "ie ve ue", "一七": "i v er -i", "姑苏": "u", "怀来": "ai uai",
       "灰堆": "ei ui uei", "遥条": "ao iao", "油求": "ou iu iou", "言前": "an ian uan van uan", "人辰": "en in un uen vn",
       "江阳": "ang iang uang", "中东": "eng ing ong iong ueng"}
FIN2ZHE = {f: z for z, fs in ZHE.items() for f in fs.split()}
POLY = set("行长重了得地还调乐着朝处为和发好少都传便差数觉教看只种转弹藏应相背曲血薄削给露尽率干难兴载屏散空当")
CLICHE = ["星辰大海", "追逐梦想", "心中的光", "未来可期", "不负韶华", "破茧成蝶", "逆风飞翔", "灵魂深处", "岁月静好",
          "燃烧青春", "勇往直前", "永不放弃", "梦想的翅膀", "时光的河", "照亮前方", "黑夜里的光", "无尽的远方", "世界的尽头",
          "回忆的碎片", "孤独的城市", "心跳的声音", "温柔了岁月", "奔向远方", "光芒万丈", "热血沸腾", "命运的齿轮", "宿命",
          "繁星点点", "海阔天空", "不忘初心", "心之所向", "一路向前", "璀璨", "绽放", "涅槃"]


def en_syl(w):
    return max(1, len(re.findall(r"[aeiouy]+", w.lower().rstrip("e"))))


def syllables(line):
    return len(HAN.findall(line)) + sum(en_syl(w) for w in EN.findall(line))


def zhe(ch):
    f = pinyin(ch, style=Style.FINALS, strict=False)[0][0] or "-i"
    if f in ("i",) and lazy_pinyin(ch)[0][:2] in ("zh", "ch", "sh") or lazy_pinyin(ch)[0][:1] in ("z", "c", "s", "r") and f == "i":
        f = "-i"
    return FIN2ZHE.get(f, f)


text = open(g.lyrics, encoding="utf-8").read()
issues, rows, section, prev = [], [], None, None
style_l = g.style.lower()
if HAN.search(text) and g.style and not any(k in style_l for k in ("mandarin", "chinese", "c-pop", "cpop", "中文", "国语", "华语")):
    issues.append("风格框没写语言：中文歌加 `mandarin`（中英混写加 `english and mandarin bars`）")
for n, raw in enumerate(text.splitlines(), 1):
    line = raw.strip()
    if not line: continue
    m = re.match(r"^\[(.+)\]$", line)
    if m:
        section, prev = m.group(1), None
        if HAN.search(m.group(1)): issues.append(f"第{n}行 段落标记用英文：[{m.group(1)}] → [Verse]/[Chorus]/[Bridge]/[Hook]")
        continue
    syl = syllables(line); per = syl / beats
    r = {"line": n, "text": line, "syllables": syl, "per_beat": round(per, 2), "fit": "ok"}
    if per > hi: r["fit"] = f"太挤（{syl} 字/{beats:.0f} 拍，{mode} 上限约 {int(hi * beats)}）：删字或拆成两行"
    elif per < lo: r["fit"] = f"太空（{syl} 字，{mode} 下限约 {int(lo * beats)}）：Suno 会拖长音或自己加词"
    if re.search(r"[（(].*?[)）]", line): issues.append(f"第{n}行 有括号：Suno 会把括号里唱成和声/背景人声，不想要就去掉")
    if re.search(r"\d", line): issues.append(f"第{n}行 有阿拉伯数字：写成汉字（10 → 十），否则读法不定")
    if EN.search(line) and HAN.search(line) and g.style and "english" not in style_l:
        issues.append(f"第{n}行 中英混写：风格框加 `english and mandarin bars`")
    for c in CLICHE:
        if c in line: issues.append(f"第{n}行 AI 套话「{c}」：换成具体的人、物、动作")
    hz = HAN.findall(line)
    if pinyin and hz:
        tones = [int(t[-1]) for t in lazy_pinyin("".join(hz), style=Style.TONE3, neutral_tone_with_five=True)]
        r["end_tone"] = tones[-1]
        run = max((len(x) for x in re.findall(r"3{3,}", "".join(map(str, tones)))), default=0)
        if run: issues.append(f"第{n}行 连续 {run} 个第三声，唱快了容易糊，换一两个字")
        r["rhyme"] = zhe(hz[-1]) if not EN.search(line.split()[-1] if line.split() else "") else "（英文结尾）"
        if prev and prev.get("rhyme") and r["rhyme"] != prev["rhyme"] and "英文" not in r["rhyme"] + prev["rhyme"]:
            r["rhyme_note"] = f"和上一行不押（{prev['rhyme']} → {r['rhyme']}）"
        for i, c in enumerate(line):
            if c in POLY:
                reads = pinyin(c, heteronym=True)[0]
                if len(set(reads)) > 1:
                    hanpos = len(HAN.findall(line[:i]))
                    guess = lazy_pinyin("".join(hz), style=Style.TONE)[hanpos]
                    issues.append(f"第{n}行 多音字「{c}」应读 {guess}（可读 {'/'.join(dict.fromkeys(reads))}）：Suno 读错就换同音字")
    rows.append(r); prev = r

print(f"模式 {mode}，{g.bpm:g} BPM，每行 {g.bars:g} 小节 = {beats:.0f} 拍 ≈ {beats * 60 / g.bpm:.2f} 秒；合适字数 {int(lo * beats)}–{int(hi * beats)}")
for r in rows:
    tail = f" 韵:{r.get('rhyme', '-')} 尾声调:{r.get('end_tone', '-')}" + (f" ⚠{r['rhyme_note']}" if r.get("rhyme_note") else "")
    print(f"{r['line']:>3} {r['syllables']:>2}字 {r['per_beat']:.2f}/拍 {'✅' if r['fit'] == 'ok' else '⚠ ' + r['fit']}{tail} | {r['text']}")
if not pinyin: print("（没装 pypinyin：pip install pypinyin，才有押韵/声调/多音字）")
print("\n问题：" + ("无" if not issues else "\n- " + "\n- ".join(dict.fromkeys(issues))))
if g.json: json.dump({"mode": mode, "rows": rows, "issues": list(dict.fromkeys(issues))}, open(g.json, "w"), ensure_ascii=False, indent=1)
