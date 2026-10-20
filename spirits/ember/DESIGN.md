# 流萤 Ember · 设计说明

流萤把一首歌做成约 30 秒的卡点 MV，主角是主人本人或主人的 IP。方法来自灵境自己跑通的一条 31 秒 4K 说唱 MV 流水线（v1 → v11），踩过的 19 个坑都写成了检查项。

## 流程与技能
| 步 | 技能 | 产出 | 关口 |
|---|---|---|---|
| 0 | ember-install / ember-update | 10 个技能 + `/workspace/ember/tools` + 自带音乐 | |
| 1 | ember-getting-started | 项目档案 | |
| 2 | ember-character-bible | 三视图、脸部参考、CHARACTER LOCK | 关口 1 |
| 3 | ember-lyrics-song | 歌词、Suno 提示词、剪好的歌、beatmap.json | |
| 4 | ember-beat-storyboard | shots.md、project.json 骨架 | |
| 5 | ember-stills | 每个镜头一张静帧（两张参考图） | |
| 6 | ember-clips | 5 秒 720p 镜头 + 可用窗口 | |
| 7 | ember-beat-edit | 粗剪 → 精剪；REVISION → Claude Code | 关口 2 |
| 8 | ember-qc-export | 19 坑 QC、16:9 / 9:16 / 4K / 审片版 / 封面 | 关口 3 |

## 工具（tools/，只依赖 python3 + numpy + ffmpeg）
| 文件 | 做什么 |
|---|---|
| beatmap.py | 音乐 → 拍点、重拍、重音、大落点、段落（谱通量 + 自相关测速；`--bpm` 校准、`--shift` 校正重拍） |
| songcut.py | 重拍到重拍剪歌，30ms 等功率交叉淡化，0.6s 淡出 |
| plan.py | beatmap → 卡点切点 + project.json 骨架 |
| render.py | project.json → 成片：图片推拉摇、视频取窗口、粗体大字踩拍、闪帧、缩放冲击、RGB 故障、颗粒、片尾、响度标准化；`--rough` `--preview` |
| qc.py | 规格/响度/黑帧检查 + 联系表；`clips` 模式出素材 QC 表 |
| fonts.py | 找粗重中文字体（Source Han Sans Heavy / Noto Sans CJK Black，OFL），没有就下载 |
| make_starter_music.py | 合成 3 首 CC0 自带曲 |

## 默认决定
- 渲染：默认在流萤自己的机器上 ffmpeg + python；抠像、HUD、逐字歌词、调色 LUT、4K 超分写 REVISION 交给 Claude Code（`claude -p`）。
- 视频：默认 Grok Imagine；Seedance 可选（主人自己的账号）。不对口型。
- 音乐：Suno 由主人登录操作，流萤给提示词并按档位提醒商用权；也可用自带 CC0 曲或外部免版权来源。
- 主角：没有 IP 就默认主人本人；照片只存在主人自己的机器和记忆里。
- 约 30 秒，1080p 默认，4K 可选；不放真实品牌 logo；字体只用开源粗体。
- 只交文件，发布由主人来点。

## 大小
每个 SKILL.md ≤ 6KB；SKILL.md + profile + memory 合计 ≤ 80KB；技能旁的参考文件单个 ≤ 12KB（导入时不回放，靠安装脚本写入）。
