---
name: ember-lyrics-song
description: >-
  歌词与作曲：写 hook 和歌词、给可直接粘贴的 Suno 风格提示词，主人在自己的 Suno 账号里生成并下载后，流萤从重拍剪到重拍、剪成约 30 秒，再跑出 beatmap.json。
  角色圣经确认后用；主人说「写首歌」「换首歌」「歌太长」，或者用自有歌曲、自带免版权曲时也用它。
---

# 歌词与作曲 → 剪歌 → beatmap

提示词模板、Suno 操作、商用权、免版权音乐来源：`suno-and-music.md`（同目录）。
工具都在 `/workspace/ember/tools/`，项目文件夹记作 `P=/workspace/ember/projects/<名>`。

## 1. 三条路（按项目档案里的选择）
- **A 用 Suno（推荐）**：流萤写词和风格，主人在 Suno 里操作（流萤不登录主人的账号）。
- **B 主人自有的歌**：只确认版权归主人，直接跳到第 4 步。
- **C 自带免版权曲**：`/workspace/ember/music/` 里 3 首 CC0（见 `LICENSES.md`），复制到 `$P/audio/full.mp3`，跳到第 4 步。

## 2. 写歌词（A）
- 结构：`[Intro]` 一句可以念的口号（给开场纯字幕用）→ `[Hook]` 4 行 → `[Verse]` 4 行 → `[Hook]` → `[Outro]` 1～2 行。30 秒 MV 最后只用得上 Intro + Hook + 一点 Outro。
- Hook 第一句 = 项目档案里的「一句话」，每行 6～10 个音节，好念、好打成大字。
- 中英混写可以，但**画面字幕只打一种语言**（v11 教训：机器转写中文会错，最后只打英文大写）。
- 歌词以主人确认的为准；先给主人看歌词，改到满意。

## 3. 交给主人去 Suno（A）
给主人一张卡片（模板见参考文件第 1 节），内容：
1. 打开 suno.com → Create → **Advanced（Custom）**。
2. Style 框粘贴：风格提示词（含 BPM，例：`… 140 bpm …`）。
3. Lyrics 框粘贴：带 `[Hook]` 等段落标记的歌词。
4. Title：歌名。生成 2～4 条，挑一条副歌最抓耳的，**Download → WAV（付费档）或 MP3**，发回给我。
5. **商用提醒（每次都说）**：免费档只能个人非商用，且终身最多 7 次试用下载；要商用（带货、广告、商单）必须是 Pro / Premier 档、在订阅期内生成并通过 Suno 下载。升级不追溯以前免费档的歌。
收到文件存为 `$P/audio/full.wav`（或 .mp3）。

## 4. 整首歌先跑 beatmap，找剪点
```bash
cd $P/audio && python3 /workspace/ember/tools/beatmap.py full.wav full_beatmap.json --bpm <Suno 里写的 BPM>
```
打开 json 看 `downbeats`（每小节第一拍）和 `sections`。挑 30 秒左右：开头一段念白/铺垫（给纯字幕开场）+ 副歌 + 重拍结尾。
**耳朵复核重拍**：用参考文件第 3 节的「打点试听」命令生成 `click_check.wav` 发给主人（或自己看波形），咔哒声要落在小节第一拍；偏了就加 `--shift 1/2/3` 重跑。

## 5. 剪歌（每一刀都从重拍到重拍）
```bash
python3 /workspace/ember/tools/songcut.py full.wav song.mp3 --ranges 7.964-14.791,47.369-71.6
```
自动做：30ms 等功率交叉淡化、开头 5ms 淡入、结尾 0.6 秒淡出，并打印「成片时间 = 原曲 − x」对照表，存进 `$P/audio/NOTES.md`。
单段（不拼接）就只写一个范围。

## 6. 剪好的歌再跑一次 beatmap（后面所有卡点都用这份）
```bash
python3 /workspace/ember/tools/beatmap.py song.mp3 ../beatmap.json --bpm <BPM>
```
字段：`duration bpm beats downbeats accent_hits big_drops sections`。有歌词就手工加 `lyrics: [{t, text}]`（时间用耳朵对，或者机器转写只拿时间、文字用自己写的）。

## 7. 收尾
告诉主人：时长、BPM、重拍数、几个大落点（big_drops）在哪几秒。项目档案进度改「歌 ✅」，进 ember-beat-storyboard。
