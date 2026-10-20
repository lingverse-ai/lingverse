---
name: ember-character-bible
description: >-
  建角色圣经：用主人的照片或 IP 参考图出白底三视图、脸部参考、姿势和表情，写一份逐项写死的 CHARACTER LOCK 锁定清单。
  入门之后、出任何镜头之前用；主人说「换造型」「人不像」时也回到这里。这是关口 1，主人确认才往下走。
---

# 角色圣经（先锁人，再出镜头）

模板和提示词全文：`bible-template.md`（同目录）。

## 1. 收素材
- 有 IP：收主人的 IP 参考图，放 `ref/`。
- 默认用主人本人：3～6 张照片（正脸、侧脸、全身）。**不收别人的照片**，除非主人说明已拿到本人授权。
- 照片只放在项目文件夹 `ref/` 和主人的记忆里，不传到其他服务。

## 2. 出 4 张资产（用 Bot 自带的生图工具，把主人照片作为参考图）
按 `bible-template.md` 的提示词，依次出：
1. `turnaround.png` 白底三视图：正面 / 3/4 侧 / 背面，全身，同一套衣服，16:9。
2. `face.png` 脸部参考：正脸 + 3/4 侧脸特写，柔光，1:1。
3. `poses.png` 姿势表：4～6 个动作（站、走、蹲、伸手、回头）。
4. `expressions.png` 表情表：平静、自信、笑、专注、惊讶。
存到 `/workspace/ember/projects/<名>/ref/`。生图工具给的是 `file://` 路径；读不到就到附件目录里找最新的那张，复制过来。

**像不像的判断**：拿 `face.png` 和主人原照并排（`ffmpeg -i a.png -i b.png -filter_complex hstack sbs.png`）自己看一遍：脸型、眼距、发际线、眼镜形状。不像就重出，最多 3 次，还不像就跟主人说哪里不像。

## 3. 写 CHARACTER LOCK（每一项写死，后面每个镜头都抄这段）
格式见模板。必须覆盖：发型、脸部特征、上衣、外套、下装（**写明长度**，如「及膝短裤，绝不是长裤」）、袜子、鞋、配饰（眼镜、链子、耳机…）、体型、禁止项。
- 对必须出现的配饰写「in EVERY shot」。
- **不写真实品牌**：不要「BAPE」「AP」「Nike 勾」这类，改成「black camo hoodie, no logo」「plain black sneakers, no logo」。
- 风格一句话（LOOK）：如「gritty neon night, 35mm film grain, crushed blacks」。
- 用英文写（给生图/视频模型看），另附中文对照给主人看。

## 4. 规则（写进档案）
- **每张静帧都同时带两张参考图生成：`turnaround.png` + `face.png`。**
- 每张静帧出来先按锁定清单逐项核对，不合格不进动态。
- 没有照片又没有 IP：先做一个原创 IP（模板第 4 节），主人确认后再用。
- 不能生图（工具不可用）：把提示词整理好，让主人在别的工具里生成后发回。

## 5. 关口 1
把 4 张资产拼成一张给主人看（`ffmpeg -i turnaround.png -i face.png -filter_complex "[0]scale=-2:720[a];[1]scale=-2:720[b];[a][b]hstack" bible_sheet.jpg`），附中文锁定清单，问：「这就是 MV 里的你，确认吗？哪一项要改？」
主人确认后：把锁定清单英文全文写进项目档案（记忆），进度改成「角色圣经 ✅」，进 ember-lyrics-song。
