---
name: ember-beat-edit
description: >-
  卡点剪辑：流萤在自己的机器上用现成脚本完成全部剪辑——粗剪（关口 2）→ 精剪：粗体大字踩拍、字压在人身后（抠像）、逐字歌词、HUD、跑马灯、LUT 调色、闪帧、故障、颗粒、片尾、4K 放大；
  成片后发「改版勾选」让主人勾要改的地方再重出。Claude Code 只是可选增强；没有机器时交镜头表 + 素材 + 剪映步骤。动态镜头做完后用；主人说「改剪辑」「换滤镜」时也用。
---

# 卡点剪辑：粗剪 → 关口 2 → 精剪 → 改版勾选

字段、ffmpeg 配方、字效规则、REVISION 模板、剪映步骤：`edit-recipes.md`（同目录）。`P=/workspace/ember/projects/<名>`，`T=/workspace/ember/tools`。

## 三条路（按顺序选第一条走得通的）
1. **默认：流萤自己跑**（主人什么都不用装）：render.py + matte.py + grade.py + upscale.py。
2. **可选增强：Claude Code**：主人想要脚本做不到的定制（新字效、特殊转场、Real-ESRGAN 精修）时，写 REVISION.md 交给 `claude -p`（参考文件第 5、6 节）。不是必需。
3. **没有机器 / 工具装不上**：交 shots.md + 素材包 + 剪映步骤（参考文件第 7 节），主人自己剪。

## 1. 填 project.json（分镜阶段 plan.py 已出骨架）
- `shots`：`src`、`in`/`out`（首尾相接铺满）、`src_start`（可用窗口起点）、`focus`（竖版取景）。每个素材只用一次。
- 项目档案的选项 → 字段：LUT → `lut`；抠像开 → 大词加 `"behind": true`；HUD → `hud`；逐字歌词 → `lyrics`；跑马灯 → `ticker`；闪帧/故障 → `flash_on`/`glitch_on`；颗粒 → `grain`；片尾 → `endcard`。字体默认自动选（拉丁 Anton、中文思源黑体 Heavy，fonts.py 自动下载；主人自己的字体 `cn_font`，见参考文件「自己加字体」；像素风 `font: "pixel"`）。
- 有 `words.json`：`lyrics` 用它的 `lines`；`punch_on` 填 beatmap 的 `accent_hits`/`big_drops`（镜头跟鼓点顶一下，`punch` 默认 0.06）。
- 写完跑 `python3 $T/audit.py project.json`：切点在拍上、歌词关 N/N、开头钩子、≥3 层、闪烁不过密。不 PASS 不渲染。

## 2. 粗剪（关口 2）
```bash
cd $P && python3 $T/render.py project.json out/rough.mp4 --rough
python3 $T/qc.py out/rough.mp4 --sheet out/rough_sheet.jpg --every 1
```
先自己看联系表（重复动作、静止镜头、景别连续重复），再发 `rough.mp4`：「只有镜头和歌的粗剪，先定顺序和节奏。」用提问组件给选项：★可以，进精剪 / 换掉某几刀（allowCustom 填号）/ 节奏加快 / 节奏放慢。**没点头不做精剪。**

## 3. 精剪（全部在流萤机器上）
```bash
python3 $T/grade.py stills/03.png out/lut_compare.jpg --compare   # 想换滤镜时出 7 宫格对比图
python3 $T/render.py project.json out/preview.mp4 --preview        # 半分辨率先看
python3 $T/render.py project.json out/excerpt.mp4 --preview --excerpt 8-30   # 先出 20–40 秒最精彩的一段给主人看（gate excerpt）
python3 $T/render.py project.json out/mv_1080p.mp4                 # 正式（超过 2 分钟就用 state.py run 放后台）
python3 $T/upscale.py out/mv_1080p.mp4 out/mv_4k.mp4               # 选了 4K 才跑
```
- 有 `behind` 词时 render 会自动调 matte.py 抠像（rembg，CPU 约 0.1 秒/帧）。报 `MATTE_DEPS_MISSING` → `pip install "rembg[cpu]"`；装不上就把 `behind` 去掉，字放 top/bottom 避开脸，告诉主人。
- 字效规则：一刀一个词、踩拍进场、不跨刀、只用一种语言、粗体（参考文件第 3 节）。
- upscale.py 有 Real-ESRGAN 就用，没有就 lanczos + 锐化。

## 4. 改版勾选（每次出成片后都发）
发 preview 或成片 + 联系表，再发一个**多选**提问组件「想改哪些？」（allowCustom）：
换滤镜（再给 LUT 单选）/ 换风格预设 / 字更大 / 字更少 / 换字体 / 抠像开或关 / 加或去 HUD / 加或去逐字歌词 / 加跑马灯 / 去故障 / 颗粒加重或减轻 / 节奏加快或放慢 / 换某几个镜头（填号）/ ★不用改，进质检。
按勾选改 project.json → 只重出受影响的版本 → 再发一次勾选，直到主人选「不用改」。每版文件名加 `_v2`、`_v3`，旧版不删。

## 5. 收尾
自己抽帧看一遍（字跨刀、出画、压脸、抠像边缘）后进 ember-qc-export。进度改「精剪 ✅（vN）」。
