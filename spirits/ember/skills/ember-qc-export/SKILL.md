---
name: ember-qc-export
description: >-
  质检与导出：精剪出来后按 v11 的 19 个坑逐条查（人物、素材、字效、音频、规格），用 qc.py 查时长、分辨率、响度、黑帧，
  再导出 16:9 母版、4K（可选）、小于 25MB 的审片版和封面，交给主人做最终确认（关口 3）。主人说「导出」「发哪个版本」时用。
---

# 质检与导出

19 坑清单、各平台规格、发布提醒：`pitfalls.md`（同目录）。`P=/workspace/ember/projects/<名>`，工具 `/workspace/ember/tools/`。

## 1. 机器检查（必须 PASS）
```bash
cd $P && python3 /workspace/ember/tools/qc.py out/mv_1080p.mp4 --expect 1920x1080 --dur <秒> --sheet out/final_sheet.jpg --every 0.5
```
查：分辨率、时长 ±0.15s、yuv420p、有音轨、响度 -16～-9 LUFS、真峰值 ≤ -0.5 dB、中途没有黑帧、1 秒内不超过 3 次闪（光敏）、带 BT.709 色彩标记。FAIL 就回 ember-beat-edit 修，不要硬交。

## 2. 人眼检查（看联系表 + 整片看一遍）
按 `pitfalls.md` 第 1 节 19 条逐条过，**每条写结论**（✅ / ❌ + 秒数），存 `$P/out/QC.md`。重点：
- 人物：每个镜头锁定清单都在（下装长度、配饰、眼镜、脸）。
- 素材：每个只用一次；没有静止像幻灯片的镜头；没有乱出的 logo / 字。
- 字：一刀一个词、不跨刀、踩拍、不出画、不压脸、只有一种语言、全是粗体。
- 音频：接缝听不出来、结尾淡出、没有爆音。
任何 ❌ → 回对应技能修（人物 → ember-stills / ember-clips；字和节奏 → ember-beat-edit）。
- 抠像：字压在人身后的镜头，看头发和手的边缘有没有闪烁、有没有把字也抠出来；不行就换镜头重出。

## 3. 导出各版本（配方都在 ember-beat-edit 的 `edit-recipes.md` 第 2 节）
| 文件 | 怎么出 |
|---|---|
| `out/mv_1080p.mp4` 16:9 母版 | `render.py project.json`（已出） |
| `out/mv_4k.mp4`（可选） | 选了 4K：`python3 /workspace/ember/tools/upscale.py out/mv_1080p.mp4 out/mv_4k.mp4`（自己跑；Claude Code 精修是可选） |
| `out/review.mp4` < 25MB | `qc.py share out/mv_1080p.mp4 out/review.mp4 --max-mb 25` |
| `out/share.mp4` < 190MB | `qc.py share …`（微信/网盘发送用；更大的文件给网盘链接） |
| 发布文案（存 out 目录，POST 文本） | 标题、3 行文案、话题标签、「AI 生成」声明、音乐来源/署名；只是草稿 |
| `out/cover_16x9.jpg`、`cover_grid.jpg` | 从成片抽最好看的一帧 |
只出 16:9 横版。另外 `render.py project.json --qc` 的字透主角检查必须 PASS。

## 4. 关口 3：交给主人
发：审片版 + 联系表 + QC.md 摘要（3 行以内）+ 各文件路径，再发提问组件：★确认终版 / 还要改（多选，选项同 ember-beat-edit 第 4 节的改版勾选，allowCustom）。
没有机器时：交 ember-beat-edit 参考文件第 7 节的剪映步骤和素材包，质检清单照样给主人逐条对。
自评分（写进 QC.md，1–5 分）：人像一致、卡点、字效、画面层次、调色、声音。任何一项 <4 或没写分 = 不交，回去修。
主人点头后 `state.py gate <目录> final ok`，告诉他（每次都说）：
- 发布由你来点；国内平台勾选「AI 生成」标识。
- 抖音、小红书、微博画面和文案里不放链接、二维码、站外导流；X 可以在帖子里放链接。
- 用的是 Suno 的歌：确认是在 Pro / Premier 订阅期内生成并下载的才能商用；用 Incompetech 的曲子：简介里写署名。
- 用了别人的脸：确认已拿到本人授权。

## 5. 收尾
项目档案进度改「交付 ✅」，把文件路径和版本号写进档案。问主人要不要让墨灵写一篇制作过程长文（只建议，不自动做）。
