# Suno 提示词与音乐来源

## 1. 给主人的 Suno 卡片（复制给主人）
```
【Suno 操作卡】
1. suno.com → Create → 切到 Advanced / Custom
2. Style（粘贴）：{STYLE}
3. Lyrics（粘贴）：见下
4. Title：{TITLE}
5. 生成 2～4 条，挑副歌最抓耳的一条 → ⋯ → Download（Pro/Premier 选 WAV）→ 发给我
⚠ 商用：免费档 = 个人非商用（终身 7 次试用下载）。要商用必须 Pro/Premier、订阅期内生成并下载；升级不追溯。
```

## 2. Style 提示词模板（≤200 字符，英文，逗号分隔，按「流派, 2～3 个乐器/音色, 情绪, BPM, 人声, 结构提示」）
| 方向 | Style |
|---|---|
| 霓虹街头说唱 | `dark trap hip hop, heavy 808 bass, glitchy synth stabs, gritty, cinematic, 140 bpm, confident male rap, hype chorus chant` |
| 日出 house | `uplifting melodic house, four on the floor, warm piano chords, bright plucks, euphoric, 122 bpm, airy female vocal, big singalong hook` |
| lofi 胶片 | `lofi hip hop, dusty drums, mellow rhodes, vinyl crackle, nostalgic, 88 bpm, soft spoken vocal, short catchy hook` |
| 方块像素 | `chiptune electro pop, 8-bit arpeggios, punchy kick, playful, 128 bpm, bright female vocal, chant hook` |
| 国风电子 | `chinese electronic, guzheng plucks, deep sub bass, epic drums, 100 bpm, powerful mandarin vocal, anthem hook` |
要点：
- **一定写 BPM**：beatmap 用 `--bpm` 校准，避免半速/倍速。
- 写 `chant` / `hook` 让副歌有可以念的口号（开场纯字幕段好用）。
- 不写真实歌手名、乐队名（平台会拒，也有侵权风险），用风格词描述。

## 3. 歌词模板（30 秒 MV）
```
[Intro]
{一句口号，可念，4～6 个词，例：MAKE ME A MUSIC VIDEO}

[Hook]
{一句话}，{押韵短句}
{第 2 行}
{第 3 行}
{一句话 重复}

[Verse]
{4 行，讲主角干了什么、用了什么工具、什么改变}

[Hook]
（同上）

[Outro]
{一句话 的短版}
```
「打点试听」重拍复核（在剪点附近听 8 秒，咔哒落在重拍上才对）：
```bash
T0=12 python3 - <<'PY'   # T0 = 从第几秒开始听
import os
import json,subprocess
b=json.load(open('full_beatmap.json')); t0=float(os.environ['T0']); D=[d-t0 for d in b['downbeats'] if t0<=d<t0+8]
expr='+'.join(f"0.6*sin(2*PI*1500*t)*between(t,{d:.3f},{d+0.03:.3f})" for d in D) or '0'
subprocess.run(['ffmpeg','-y','-v','error','-ss',str(t0),'-t','8','-i','full.wav','-f','lavfi','-t','8','-i',f"aevalsrc='{expr}':s=48000",
 '-filter_complex','[0][1]amix=inputs=2:normalize=0','click_check.wav'],check=True)
PY
```

## 4. 剪歌规则（v11 实测）
- 每一刀都在重拍上（两边都是小节第一拍），30ms 等功率交叉淡化（`acrossfade c1=qsin c2=qsin`）。
- 结构：铺垫/念白（2～4 小节，给纯字幕开场）→ 副歌/说唱 → 第二个情绪抬升（女声高音、合唱）→ 重拍结尾 → 0.6s 淡出。
- 不要从人声中间切；先跑整首 beatmap，再挑段。
- 剪完一定再跑一次 beatmap（时间都变了）。

## 5. 免版权音乐来源（主人不用 Suno 时）
| 来源 | 许可 | 能不能商用 | 要不要署名 | 注意 |
|---|---|---|---|---|
| 流萤自带 `music/` 3 首 | CC0 1.0（灵境自己合成） | 能 | 不用 | 随仓库分发 |
| Pixabay Music | Pixabay Content License | 能 | 不用 | 不能把音乐单独再分发；YouTube 偶有版权声明误报，留好下载页链接 |
| Incompetech（Kevin MacLeod） | CC BY 4.0 | 能 | **要**：`"曲名" Kevin MacLeod (incompetech.com) Licensed under Creative Commons: By Attribution 4.0 https://creativecommons.org/licenses/by/4.0/` | 署名写在视频简介 |
| Free Music Archive | 每首不同 | 看单曲 | 看单曲 | 只用筛选为 CC0 / Public Domain 的 |
| Freesound（音效） | 每个不同 | 看单个 | CC BY 要署名 | 只用 CC0 的音效最省事 |
不用：抖音/小红书 App 内的热门音乐导出到别处、网上扒的歌、录屏录下来的音乐。

## 6. 自带 3 首（BPM 都已用 beatmap 校验）
| 文件 | BPM | 时长 | 风格 | 适合 |
|---|---|---|---|---|
| `ember-neon-140.mp3` | 140 | 约 31s | 暗黑 trap，808、切分底鼓 | 街头、科技、硬朗 |
| `ember-sunrise-120.mp3` | 120 | 约 32s | house，四拍底鼓、钢琴和弦 | 正能量、产品发布 |
| `ember-lofi-90.mp3` | 90 | 约 32s | lofi，慢鼓、电钢 | 回忆、日常、温柔 |
结构都是：2 小节铺垫（无鼓）→ 鼓进来 → 中段抬升 → 结尾。重拍从第 3 小节开始最稳。
