---
name: ember-stills
description: >-
  静帧：按镜头表给每个镜头出一张 16:9 静帧，每张都带「三视图 + 脸部参考」两张参考图生成，出来后按 CHARACTER LOCK 逐项核对，不合格重出。
  分镜定了之后用；主人说「这张不像」「换个场景」时也用。
---

# 静帧（每个镜头一张，过了锁定清单才算数）

提示词模板和逐项核对表：`still-prompts.md`（同目录）。`P=/workspace/ember/projects/<名>`。

## 1. 每张静帧怎么出
1. 从 shots.md 取这一行：景别、场景、人物动作、主体位置。
2. 按 `still-prompts.md` 第 1 节拼提示词：**景别 + 场景 + 人物动作 + CHARACTER LOCK 全文 + LOOK + 构图 + 禁止项**。
3. 调生图工具：**参考图必须同时带 `ref/turnaround.png` 和 `ref/face.png`**（工具支持多张参考图就两张都给；只支持一张就给 face，并把锁定清单写得更细）。画幅 16:9。
4. 存为 `$P/stills/<镜头号>.png`（如 `03.png`）。生图工具给的是 `file://` 路径；读不到就到附件目录找最新文件复制过来。
5. 开场纯字幕段（INTRO_CARD）和片尾卡不出静帧。

## 2. 逐张核对（`still-prompts.md` 第 3 节，逐项打勾）
自己用看图工具打开每张，按顺序看：**下装长度 → 鞋袜 → 必须出现的配饰 → 脸和眼镜 → 手（几根手指）→ 衣服和背景里有没有字、logo → 体型有没有拉长**。
- 任何一项不过 → 改提示词重出（把没过的那一项写到最前面，加 `IMPORTANT:`），同一张最多 4 次。
- 4 次还不过 → 换场景或换景别（如全身改近景避开裤子），在 shots.md 里标注。
- 背景里乱出的字：能裁掉就记下「需裁切」，裁不掉就重出。

## 3. 一次出多少
- 先出 3 张（一远一中一特）给主人看人像不像、风格对不对，确认后再批量出剩下的。
- 批量出时每出 4 张自查一次，不要攒到最后。

## 4. 拼一张总览给主人
```bash
cd $P/stills && ffmpeg -y -v error -pattern_type glob -i '*.png' -vf "scale=480:-2,drawtext=text='%{eif\:n\:d}':x=10:y=10:fontsize=28:fontcolor=yellow:borderw=2,tile=4x4" -frames:v 1 ../stills_sheet.jpg
```
（序号是排序后的第几张，对照文件名看。）

## 5. 没有生图能力时
把每个镜头的完整提示词写进 `$P/stills/PROMPTS.md`，让主人在自己的工具里生成（记得带两张参考图），存回 `stills/` 同名文件，流萤再做核对。

## 6. 收尾
全部过了核对 → 进度改「静帧 ✅（N 张）」，进 ember-clips。
