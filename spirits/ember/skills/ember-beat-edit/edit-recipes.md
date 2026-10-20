# 剪辑配方（render.py、ffmpeg、字效、REVISION、Claude Code）

## 1. project.json 全字段（时间都是成片秒数）
```json
{
 "size": [1920, 1080], "fps": 30, "duration": 30.0,
 "audio": "audio/song.mp3", "audio_start": 0, "loudnorm": true,
 "font": null,
 "shots": [
  {"src": "INTRO_CARD", "in": 0, "out": 3.429},
  {"src": "clips/01.mp4", "in": 3.429, "out": 5.143, "src_start": 0.0, "focus": 0.5, "speed": 1.0},
  {"src": "stills/02.png", "in": 5.143, "out": 6.857, "move": "push", "amount": 0.12}
 ],
 "words": [
  {"t": 0.0,   "until": 0.43,  "text": "ONE", "size": 260},
  {"t": 3.429, "until": 5.143, "text": "NIGHT", "color": "#FFE45C", "pos": "bottom"},
  {"t": 5.143, "until": 6.857, "text": "AWAKE", "color": "white", "box": "#FF2E88"}
 ],
 "flash_on": [3.429, 5.143], "glitch_on": [6.857],
 "grain": 6, "fade": 0.6, "crf": 18,
 "endcard": {"from": 27.43, "text": "一句话变成歌", "sub": "TITLE · 2026"}
}
```
| 字段 | 说明 |
|---|---|
| `src` | 视频、图片（png/jpg/webp），或 `INTRO_CARD`（黑底）/ `color:#ffffff`（纯色底，片尾白卡用） |
| `move` | 图片专用：`push` 推 / `pull` 拉 / `pan_left` / `pan_right` / `still`；`amount` 缩放幅度（默认 0.12） |
| `src_start` | 视频从第几秒开始取（= 可用窗口起点） |
| `focus` | 横向取景 0～1；竖版时按主体位置填（主体在左 0.3、在右 0.7） |
| `words.pos` | `center` / `top` / `bottom` / `left`；`size` 按短边 1080 设计，太长自动缩小不出画 |
| `words.box` | 底色块（黑底白字、白字橙底这类）；`border` 描边粗细（默认 6） |
| `loudnorm` | 默认把响度拉到 -14 LUFS、真峰值 -1.5 dB（各平台推荐值） |
| `--rough` | 粗剪：忽略 words/flash/glitch/grain/endcard |
| `--preview` | 半分辨率，几秒出片，改字效时用 |

进阶字段（都在流萤机器上跑，不用 Claude Code）：
```json
 "lut": "v11-street",
 "words": [{"t": 6.857, "until": 8.571, "text": "FUTURE", "size": 420, "behind": true}],
 "lyrics": [{"t": 7.0, "until": 8.4, "text": "ONE LINE BECOMES A SONG", "y": 0.70}], "lyric_cps": 20,
 "hud": {"title": "EMBER // LINGVERSE", "label": "TRACK 01"},
 "ticker": [{"from": 15.4, "to": 18.8, "text": "MAKE ME A MUSIC VIDEO — ", "y": 0.5, "size": 140, "speed": 600}],
 "matte_width": 512
```
| 字段 | 说明 |
|---|---|
| `lut` | 自带 6 个：v11-street / cyber-neon / guofeng-ink / retro-film / anime-bright / voxel-pop（CC0），或 .cube 路径 |
| `behind` | 这个词画在人身后：render 自动调 matte.py（rembg u2netp）出遮罩再合成；`matte_width` 越大边缘越细、越慢 |
| `lyrics` | 终端风逐字打出（`> ` 开头、光标 `_`），等宽粗体，左下；`lyric_cps` 每秒几个字 |
| `hud` | 四角等宽小字：标题、时间码、标签、闪烁 REC，加角标线 |
| `ticker` | 横向滚动大字（跑马灯），长镜头用 |

单独用的工具：
```bash
python3 $T/matte.py clips/03.mp4 masks/03.mp4          # 只出遮罩（白=人）
python3 $T/grade.py out/mv.mp4 out/mv_graded.mp4 --lut retro-film
python3 $T/grade.py frame.jpg lut_compare.jpg --compare  # 原片 + 6 个 LUT 对比图
python3 $T/upscale.py out/mv_1080p.mp4 out/mv_4k.mp4    # Real-ESRGAN 有就用，否则 lanczos+unsharp
```

竖版：复制一份 `project_9x16.json`，`size` 改 `[1080, 1920]`，每个镜头按主体位置填 `focus`，`words.pos` 别用 `bottom`（底部约 1/5 会被平台界面挡住）。

## 2. 常用 ffmpeg 配方（都已在流萤机器上试过）
```bash
# 纯 ffmpeg 粗剪（没有 render.py 时）：每段按重拍切，统一 720p30，拼接后配歌
ffmpeg -y -ss 0.5 -i clips/03.mp4 -t 1.714 -an -vf "scale=1280:720:force_original_aspect_ratio=increase,crop=1280:720,fps=30,tpad=stop_mode=clone:stop_duration=4" -t 1.714 -c:v libx264 -pix_fmt yuv420p seg03.mp4
printf "file 'seg01.mp4'\nfile 'seg02.mp4'\n" > l.txt
ffmpeg -y -f concat -safe 0 -i l.txt -i audio/song.mp3 -c:v libx264 -crf 20 -c:a aac -shortest rough.mp4

# 统一调色（轻）：压暗部、提对比、略降饱和，所有镜头同一套
ffmpeg -y -i in.mp4 -vf "eq=contrast=1.08:saturation=0.92:gamma=0.96,curves=preset=increase_contrast" -c:a copy graded.mp4

# 审片版 < 25MB（按时长算码率：25MB*8/秒数 - 音频 128k，留 10% 余量）
D=30; VB=$(( 25*8*1000*9/10/D - 128 ))k
ffmpeg -y -i out/mv_1080p.mp4 -vf scale=-2:720 -c:v libx264 -b:v $VB -maxrate $VB -bufsize $VB -c:a aac -b:a 128k out/review.mp4

# 4K 母版（lanczos 放大；有 Real-ESRGAN 更好，交给 Claude Code）
ffmpeg -y -i out/mv_1080p.mp4 -vf "scale=3840:2160:flags=lanczos" -c:v libx264 -preset slow -b:v 60M -maxrate 60M -bufsize 120M -c:a aac -b:a 320k out/mv_4k.mp4

# 从成片抽 4K/1080 静帧做封面
ffmpeg -y -ss 12.5 -i out/mv_1080p.mp4 -frames:v 1 -q:v 2 out/cover_16x9.jpg

# 2x2 宫格封面（4 个时间点）
for t in 4 10 16 22; do ffmpeg -y -v error -ss $t -i out/mv_1080p.mp4 -frames:v 1 -vf scale=960:540 g$t.png; done
ffmpeg -y -i g4.png -i g10.png -i g16.png -i g22.png -filter_complex "[0][1]hstack[a];[2][3]hstack[b];[a][b]vstack" out/cover_grid.jpg

# 只看某一段的逐帧（查闪帧、字是否跨刀）
ffmpeg -y -ss 6.7 -t 0.4 -i out/mv_1080p.mp4 -vf "scale=384:-2,tile=6x2" -frames:v 1 cut_check.jpg
```

## 3. 字效规则（v11 第 19 坑的解法）
- **一刀一个词**：`t` = 镜头 `in`，`until` ≤ 镜头 `out`；词在下一刀硬切出去，不淡出、不跨刀。
- 每个词**踩在拍上进场**：只用 `beats` / `downbeats` / `accent_hits` 里的时间，不在两拍之间。
- 进场：1.5 帧白闪（`flash_on`）+ 105%→100% 缩放冲击（render.py 自动，约 3 帧）。
- 开场纯字幕：黑底，每拍一个大词（size 240～300），颜色在白字 / 白底黑字 `box` / 主色底之间轮换。
- 大落点 `big_drops`：2 帧 RGB 错位（`glitch_on`）。
- 只用一种语言；英文全大写。渲染后检查文字：`python3 -c "import json;print([w['text'] for w in json.load(open('project.json'))['words'] if not w['text'].isascii()])"`（要求全英文时必须输出 `[]`）。
- 粗体：Heavy / Black 字重；描边 6 + 半透明黑，保证亮背景上也看得清。
- 不压脸：人脸在中间时字放 `top`/`bottom` 或用 `box`；要字压在人身后 → 抠像，交给 Claude Code。

## 4. 谁来做
| 效果 | 流萤机器上的脚本（默认） | Claude Code（可选增强） |
|---|---|---|
| 切点、配歌、响度、粗剪、竖版取景 | render.py / plan.py | |
| 大字踩拍、闪帧、缩放冲击、故障、颗粒、片尾 | render.py | |
| 字压在人身后 | render.py + matte.py（rembg） | 逐帧精修边缘、头发丝 |
| HUD、逐字歌词、跑马灯 | render.py | 定制动画（节点图、ASCII 转场） |
| 调色 | grade.py + 6 个 CC0 LUT | 自定义调色、只给脸加质感 |
| 4K | upscale.py（lanczos+锐化；有 Real-ESRGAN 就用） | 装 Real-ESRGAN / Topaz 精修 |

## 5. REVISION.md 模板（给 Claude Code）
```markdown
# REVISION {N}: {TITLE}
Base: keep everything from v{N-1} ({一句话描述上一版的风格}). Reference timing: out/rough.mp4 is the APPROVED shot order. Match it.
Inputs: clips/ stills/ audio/song.mp3 beatmap.json project.json (shot table + words are authoritative).

## 1. Shot list (each source used ONCE, every cut on a downbeat)
| # | in–out (s) | src | src start |
|---|---|---|---|
{从 project.json 逐行照抄}
Do NOT use: {弃用的素材}.

## 2. Typography
- ONE word per cut, never held across a cut. Words and times exactly as project.json "words".
- Font: {字体文件路径}, heavy weight only. Never a thin or condensed-light font.
- Every word enters ON a beat (beatmap beats/accent_hits): 1–2 frame flash, scale punch 105%→100% over 4 frames, slow drift while held.
- 2-frame RGB split / glitch slice on big_drops: {列出秒数}.
- {要的话} Person matte so big words sit BEHIND the person (rembg or mediapipe per frame).
- {要的话} Marquee: big words scroll horizontally during shots {号}.
- Language: {English ALL CAPS only → grep rendered text for non-ASCII, must be zero}.

## 3. Look
Unified grade across all clips: {如 crushed blacks, slight teal shadows}. Film grain ~6–8, light texture on the face only. NO beauty smoothing, NO added freckles.

## 4. End card
{白底/黑底}, title "{标题}", line "{一句话}", from {秒} to end.

## 5. Export
{3840x2160 lanczos or Real-ESRGAN | 1920x1080}, 30fps, H.264 high, ~{60 Mbps 4K | 16 Mbps 1080p}, AAC 320k, -14 LUFS.
Files: out/{name}_v{N}.mp4 plus out/{name}_v{N}_review.mp4 under 25MB.
Verify before finishing: duration = {秒} ±0.05, each src used once, no word spans a cut, no non-ASCII text (if English-only).
```
每一轮迭代：新建 `REVISION{N+1}.md`，开头 `Keep everything from v{N}.`，下面只列要改的条目和原因。

## 6. Claude Code 命令（可选：只在主人想要脚本做不到的定制时用）
```bash
cd /workspace/ember/projects/<名>
claude -p "Read REVISION.md and implement it fully. Clips are in clips/, stills in stills/, song is audio/song.mp3, beats are in beatmap.json, shot table and words are in project.json. Write the render code in src/, then export out/<名>_v1_4k.mp4 (3840x2160) plus a 1080p review copy under 25MB. Run the checks listed in the Export section and print the results." --allowedTools "Bash,Read,Write,Edit"
```
- 第一次用要先在那台电脑上登录 Claude Code（主人自己的账号）。`--allowedTools` 让它能直接跑 ffmpeg/python 而不用每步确认；不放心就去掉，在交互模式里逐条批准。
- 跑完先看 `out/` 里的审片版，再抽帧对照 REVISION 逐条验收。

## 7. 没有机器时：剪映步骤（交给主人）
交付：`shots.md`（时间码表）、`clips/` `stills/`、`audio/song.mp3`、`words.txt`（每刀的大词）、LUT 文件。
1. 剪映专业版 → 新建项目 → 导入全部素材和 song.mp3，歌拖到音轨。
2. 选中音轨 → 「踩点」→「自动踩点 / 踩节拍 I」，出现黄色拍点；或照 shots.md 的时间码手动打点（M 键）。
3. 按 shots.md 顺序把每个镜头拖上视频轨，首尾吸附到拍点；用「分割」裁到可用窗口。
4. 文字：每刀新建一个文本，字体选最粗的（思源黑体 Heavy 等开源字体），入场动画「放大」或「闪现」，时长 = 这一刀。
5. 特效：切点加「闪白」（2 帧），drop 加「故障 / RGB 分离」；整体加「胶片颗粒」。
6. 调色：「调节」→「LUT」导入 .cube（自带 6 个）。
7. 抠像：选中人像镜头 →「智能抠像」，复制一层放到文字上面，就能字压在人身后。
8. 导出 1080p 30fps；竖版新建 9:16 草稿重新摆位。
