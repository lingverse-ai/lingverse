---
name: ember-clips
description: >-
  动态镜头：把每张过了核对的静帧用 Grok Imagine 图生视频变成 5 秒 720p 的镜头（可选主人自己的 Seedance），人基本不动、靠镜头运动出动感、不对口型；
  每条抽帧拼 QC 表人眼逐格看，记下可用窗口。静帧做完后用；主人说「这条不自然」「重做某个镜头」时也用。
---

# 动态镜头（图生视频 + 可用窗口）

运镜提示词模板、Seedance 写法、QC 判定细则：`clip-prompts.md`（同目录）。`P=/workspace/ember/projects/<名>`。

## 1. 默认工具：Grok Imagine（Bot 自带的视频生成）
- 每条：首帧 = `stills/<号>.png`，时长 5～6 秒，720p，画幅跟静帧（16:9）。
- 提示词按 `clip-prompts.md` 第 1 节：**镜头运动在前，人物动作要小，最后一行固定写禁止项**。
- 一次只生成一条，存为 `$P/clips/<号>.mp4`（和静帧同号）。生成要几分钟，期间可以写下一条的提示词。
- 可选：主人有自己的 Seedance 账号，流萤给提示词（第 3 节），主人生成后把 mp4 发回。流萤不登录主人的账号。

## 2. 硬规则（v11 的坑，一条都别破）
- 生成时**不调色、不加字**（统一调色和字都在精剪做）。
- 人基本不动，动感来自镜头：推、跟、横移、dolly zoom、crash zoom、桶滚。**不做 360° 环绕**。
- **不对口型**，不写 rap / sing / lip sync；提示词写 `mouth closed or neutral, not talking`。
- 走路 = 真实迈步（`real walking steps, feet lifting off the ground`），不能平移滑行。
- 坐着/站着要「活」：`blinks naturally, slight head turn, breathing`，不能像假人。
- 不要叹气、不要嘴动：只用干净的那几秒。

## 3. 每条都 QC（自己看，不靠自动判断）
```bash
cd $P && python3 /workspace/ember/tools/qc.py clips qc_clips.jpg clips/*.mp4
```
每条均匀抽 5 帧一行。逐格看（细则见参考文件第 4 节）：下装、鞋袜、配饰、脸、眼镜、手、乱出的字/logo、嘴有没有动、走路有没有迈步、有没有突然变形。
**记可用窗口**：通常是 0～2.5 秒（脸和眼镜 3 秒后容易变形）。写进 `$P/clips/WINDOWS.md`：
```
| 号 | 可用窗口 | 问题 | 处理 |
| 03 | 0.0–2.4 | 2.8s 眼镜变形 | 只用前 2.4s |
| 07 | — | 裤子变长 | 重做 |
```
需要更细看某一段：`ffmpeg -ss 2 -t 1.5 -i clips/07.mp4 -vf "fps=8,scale=320:-2,tile=6x2" -frames:v 1 c07.jpg`。

## 4. 不合格怎么办
- 可用窗口 ≥ 这个镜头在镜头表里的长度：留着，精剪时用 `src_start` 取那一段。
- 不够长：重做（改提示词：运动更慢、人物动作更少），或把镜头表里这一刀缩短、和相邻镜头换。
- 同一条重做 3 次还不行：退回静帧换构图。
- 全局降级（视频生成不可用）：用静帧 + 推拉摇移（render.py 对图片自动做 zoompan），告诉主人「效果会差一档，是 v1 的做法」。

## 5. 收尾
所有镜头都有可用窗口 → 把 QC 表发给主人看一眼（不用等回复），进度改「动态 ✅」，进 ember-beat-edit 做粗剪。
