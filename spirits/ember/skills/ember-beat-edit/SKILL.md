---
name: ember-beat-edit
description: >-
  卡点剪辑：先用 render.py 出粗剪（只有镜头和歌，不加字不调色）给主人过节奏（关口 2），点头后再精剪：一刀一个粗体大字踩拍进场、闪帧、缩放冲击、drop 故障、颗粒、片尾卡；
  抠像、HUD、4K 超分这类需要写代码的精修，写 REVISION 修改单交给 Claude Code（claude -p）。动态镜头做完后用；主人说「改剪辑」「字不跟拍」时也用。
---

# 卡点剪辑：粗剪 → 关口 2 → 精剪

project.json 字段、ffmpeg 配方、字效规则、REVISION 模板和 `claude -p` 命令：`edit-recipes.md`（同目录）。
`P=/workspace/ember/projects/<名>`，工具在 `/workspace/ember/tools/`。默认**在流萤自己的机器上**用 ffmpeg + python 渲染，主人什么都不用装。

## 1. 填 project.json（分镜阶段 plan.py 已出骨架）
- `shots`：每个镜头的 `src`（clips/03.mp4 或 stills/03.png）、`in`/`out`（成片时间，必须首尾相接铺满）、`src_start`（取可用窗口的起点，见 clips/WINDOWS.md）、`focus`（0 左…1 右，竖版用）。
- 可用窗口比镜头短：换素材或缩短这一刀，**不要**让 render 定格补帧超过 0.3 秒。
- 每个素材只用一次（自查：`python3 -c "import json,collections;p=json.load(open('project.json'));print([k for k,v in collections.Counter(s['src'] for s in p['shots']).items() if v>1])"` 输出必须是 `[]`）。

## 2. 粗剪（v11 最关键的一步）
```bash
cd $P && python3 /workspace/ember/tools/render.py project.json out/rough.mp4 --rough
python3 /workspace/ember/tools/qc.py out/rough.mp4 --sheet out/rough_sheet.jpg --every 1
```
自己先看联系表：有没有重复动作、有没有静止像幻灯片的镜头、景别有没有连续重复。
**关口 2**：把 `rough.mp4` 发给主人：「这是只有镜头和歌的粗剪，先定顺序和节奏。想换哪几刀？」改顺序 → 改 `shots` → 重出，直到主人点头。**没点头不做精剪。**

## 3. 精剪（render.py 能直接做的）
在 project.json 里加：
- `words`：**一刀一个词**，`t` = 这一刀的 `in`，`until` ≤ 这一刀的 `out`（绝不跨刀）；开场纯字幕段每拍一个词（用 `beats`）。
- 词只用一种语言；英文全大写。颜色 2～3 种轮换（白、主色、黑底白字 `box`）。
- `flash_on`：每个切点（1.5 帧白闪）；`glitch_on`：`big_drops`（2 帧 RGB 错位）。
- `grain`: 4～8（AI 皮肤太光滑就加到 6～8）；`endcard`：片尾标题 + 一句话。
- 字体自动用粗重中文字体（Source Han Sans Heavy / Noto Sans CJK Black，OFL）；**不用细体**。
```bash
python3 /workspace/ember/tools/render.py project.json out/preview.mp4 --preview   # 先出半分辨率快速看
python3 /workspace/ember/tools/render.py project.json out/mv_1080p.mp4
```
字效细则（进场踩拍、105%→100% 缩放冲击、闪帧）见参考文件第 3 节。

## 4. 需要写代码的精修 → Claude Code
render.py 不做的：**人像抠像让大字压在人身后**、HUD/终端打字效果、横向滚动字幕、逐字打歌词、统一调色 LUT、4K 超分。要这些时：
1. 按参考文件第 5 节模板写 `$P/REVISION.md`（镜头表照抄 project.json，规则写成可验证的）。
2. 打包：`clips/ stills/ audio/song.mp3 beatmap.json project.json out/rough.mp4 REVISION.md`。
3. 两条路：
   - 流萤机器上装了 Claude Code CLI：在 `$P` 里跑参考文件第 6 节的命令。
   - 没装：把整个 `$P` 打成 zip 交给主人，主人在自己装了 Claude Code 的电脑上解压，`cd` 进去跑同一条命令。
4. 每一轮修改只写「改哪几条 + 为什么」，其余写 `Keep everything from vN`。

## 5. 收尾
精剪出来自己先抽帧看一遍（字有没有跨刀、出画、压脸），再进 ember-qc-export。进度改「精剪 ✅（vN）」。
