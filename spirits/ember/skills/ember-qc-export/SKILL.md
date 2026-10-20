---
name: ember-qc-export
description: >-
  质检与导出：精剪出来后按 v11 的 19 个坑逐条查（人物、素材、字效、音频、规格），用 qc.py 查时长、分辨率、响度、黑帧，
  再导出 16:9 母版、9:16 竖版、4K（可选）、小于 25MB 的审片版和封面，交给主人做最终确认（关口 3）。主人说「导出」「发哪个版本」时用。
---

# 质检与导出

19 坑清单、各平台规格、发布提醒：`pitfalls.md`（同目录）。`P=/workspace/ember/projects/<名>`，工具 `/workspace/ember/tools/`。

## 1. 机器检查（必须 PASS）
```bash
cd $P && python3 /workspace/ember/tools/qc.py out/mv_1080p.mp4 --expect 1920x1080 --dur <秒> --sheet out/final_sheet.jpg --every 0.5
```
查：分辨率、时长 ±0.15s、yuv420p、有音轨、响度 -16～-9 LUFS、真峰值 ≤ -0.5 dB、中途没有黑帧。FAIL 就回 ember-beat-edit 修，不要硬交。

## 2. 人眼检查（看联系表 + 整片看一遍）
按 `pitfalls.md` 第 1 节 19 条逐条过，**每条写结论**（✅ / ❌ + 秒数），存 `$P/out/QC.md`。重点：
- 人物：每个镜头锁定清单都在（下装长度、配饰、眼镜、脸）。
- 素材：每个只用一次；没有静止像幻灯片的镜头；没有乱出的 logo / 字。
- 字：一刀一个词、不跨刀、踩拍、不出画、不压脸、只有一种语言、全是粗体。
- 音频：接缝听不出来、结尾淡出、没有爆音。
任何 ❌ → 回对应技能修（人物 → ember-stills / ember-clips；字和节奏 → ember-beat-edit）。

## 3. 导出各版本（配方都在 ember-beat-edit 的 `edit-recipes.md` 第 2 节）
| 文件 | 怎么出 |
|---|---|
| `out/mv_1080p.mp4` 16:9 母版 | `render.py project.json`（已出） |
| `out/mv_9x16.mp4` 竖版 | 复制成 `project_9x16.json`，`size` 改 `[1080,1920]`，每个镜头填 `focus`，字不放底部 1/5，再 render；**重新取景，不是直接裁** |
| `out/mv_4k.mp4`（可选） | 项目档案写了 4K：lanczos 放大或交给 Claude Code 做超分 |
| `out/review.mp4` < 25MB | 审片版公式（按时长算码率） |
| `out/cover_16x9.jpg`、`cover_9x16.jpg`、`cover_grid.jpg` | 从成片抽最好看的一帧；竖版封面从竖版抽 |
竖版也要跑一次 qc.py（`--expect 1080x1920`）。

## 4. 关口 3：交给主人
发：审片版 + 联系表 + QC.md 摘要（3 行以内）+ 各文件路径。问：「这是终版，确认吗？要改哪几处？」
主人点头后告诉他（每次都说）：
- 发布由你来点；国内平台勾选「AI 生成」标识。
- 抖音、小红书、微博画面和文案里不放链接、二维码、站外导流；X 可以在帖子里放链接。
- 用的是 Suno 的歌：确认是在 Pro / Premier 订阅期内生成并下载的才能商用；用 Incompetech 的曲子：简介里写署名。
- 用了别人的脸：确认已拿到本人授权。

## 5. 收尾
项目档案进度改「交付 ✅」，把文件路径和版本号写进档案。问主人要不要让墨灵写一篇制作过程长文（只建议，不自动做）。
