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
| 7 | ember-beat-edit | 粗剪 → 精剪（全部脚本自跑）→ 改版勾选；Claude Code 可选 | 关口 2 |
| 8 | ember-qc-export | 19 坑 QC、16:9 / 9:16 / 4K / 审片版 / 封面 | 关口 3 |

## 工具（tools/，只依赖 python3 + numpy + ffmpeg）
| 文件 | 做什么 |
|---|---|
| beatmap.py | 音乐 → 拍点、重拍、重音、大落点、段落（谱通量 + 自相关测速；`--bpm` 校准、`--shift` 校正重拍） |
| songcut.py | 重拍到重拍剪歌，30ms 等功率交叉淡化，0.6s 淡出 |
| plan.py | beatmap → 卡点切点 + project.json 骨架 |
| render.py | project.json → 成片：图片推拉摇、视频取窗口、粗体大字踩拍、闪帧、缩放冲击、RGB 故障、颗粒、片尾、响度标准化；`--rough` `--preview` |
| qc.py | 规格/响度/黑帧检查 + 联系表；`clips` 模式出素材 QC 表 |
| matte.py | 人像抠像遮罩（rembg u2netp，CPU，可选依赖），给「字压在人身后」用 |
| grade.py | 套 LUT 调色、出 LUT 对比图 |
| upscale.py | 4K 放大：Real-ESRGAN 有就用，否则 lanczos + 锐化 |
| make_luts.py | 生成 6 个 CC0 LUT（`luts/`） |
| fonts.py | 默认字体全部 OFL、自动下载到 $EMBER_HOME/fonts：拉丁大字 Anton（v11 同款超粗窄体）、中文 思源黑体 Heavy、等宽 JetBrains Mono ExtraBold、像素 Fusion Pixel |
| fonts.py（中文） | 默认只有思源黑体 Heavy（自动下载）；主人自己的字体放项目的 fonts/ 目录，用 cn_font 指定；可选内置字体（用到时才下载）：cn-smiley 得意黑、cn-kuaile 站酷快乐体、cn-huangyou 站酷庆科黄油体、cn-serif 思源宋体 Heavy、cn-brush 马善政毛笔楷书，全部 SIL OFL 1.1；`fonts.py sheet` 出对比图。没收录：站酷酷黑、站酷高端黑（官方声明免费商用，但转授权和部分企业用途另算，而且只能从站酷网页下载）、阿里巴巴普惠体（不能转授权，官方没有脚本可用的下载地址）、HarmonyOS Sans（不能单独再分发，官方仓库没有 Black 字重）、庞门正道标题体和优设标题黑（只有公众号或网页声明，不能脚本下载） |
| lyrics_cn.py | 中文歌词体检：字数对槽位（按 v11 实测校准）、十三辙押韵、连续第三声、多音字、Suno 格式（括号、数字、段落标记、语言标签）、AI 套话 |
| state.py | 项目进度表 8 步 + 下一步命令；DECISIONS.md 原话记录；gates.json 关口；后台任务 RUNS.md（换对话可续） |
| lyrics_align.py | 歌词对时间：faster-whisper 出词时间，对齐到主人写的歌词（可选，`--even` 兜底） |
| audit.py | 剪辑工程自检：切点在拍上、歌词关 N/N、开头钩子、≥3 层、闪烁、片尾卡 |
| make_starter_music.py | 合成 3 首 CC0 自带曲 |

## 默认决定
- 渲染：全部在流萤自己的机器上 ffmpeg + python（含抠像、逐字歌词、HUD、跑马灯、LUT、4K 放大）；Claude Code 只是可选增强（`claude -p`）；没有机器就交镜头表 + 素材 + 剪映步骤。
- 交互：所有选择用提问组件出选择题（多选、可自填），默认 v11 同款；成片后发「改版勾选」。
- 风格预设：v11 同款（旗舰）+ 赛博街头、国风、复古胶片、动漫、方块世界（`ember-getting-started/styles.md`）。
- 视频：默认 Grok Imagine；Seedance 可选（主人自己的账号）。不对口型。
- 音乐：Suno 由主人登录操作，流萤给提示词并按档位提醒商用权；也可用自带 CC0 曲或外部免版权来源。
- 主角：没有 IP 就默认主人本人；照片只存在主人自己的机器和记忆里。
- 约 30 秒，1080p 默认，4K 可选；不放真实品牌 logo；字体只用开源粗体。
- 只交文件，发布由主人来点。

## 大小
每个 SKILL.md ≤ 6KB；SKILL.md + profile + memory 合计 ≤ 80KB；技能旁的参考文件单个 ≤ 12KB（导入时不回放，靠安装脚本写入）。
