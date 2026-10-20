# 分镜模板

## 1. shots.md 表头与示例（虚构项目「一句话变成歌」，140 BPM，一小节约 1.714s）
| # | 进–出 | 段落 | 景别 | 场景 | 人物动作 | 镜头运动 | 大字 | 主体 | 素材 |
|---|---|---|---|---|---|---|---|---|---|
| 00 | 0.000–3.429 | 开场 | — | 黑底 | 无人 | — | ONE / LINE / TO / A / SONG（每拍一个） | 中 | INTRO_CARD |
| 01 | 3.429–5.143 | 铺垫 | 远景 | 夜里的天桥，车流光轨 | 同一个人背对镜头站着 | 慢推 | NIGHT | 中 | clips/01.mp4 |
| 02 | 5.143–6.857 | 铺垫 | 特写 | 霓虹招牌下 | 抬眼看镜头、眨眼 | 微推 | AWAKE | 中 | clips/02.mp4 |
| 03 | 6.857–8.571 | 副歌 | 低机位 | 地铁站台，列车进站 | 真实迈步走向镜头 | 后退跟拍 | MOVE | 中 | clips/03.mp4 |
| … | | | | | | | | | |
| 15 | 27.43–30.0 | 片尾 | — | 白底 | 无 | — | 标题 + 一句话 | 中 | endcard |

## 2. 景别词表（中 → 给模型的英文）
远景 wide establishing shot ｜ 全身 full body shot ｜ 中景 medium shot ｜ 近景 medium close-up ｜ 特写 close-up ｜ 大特写 extreme close-up ｜ 侧脸 profile shot ｜ 低机位 low angle ｜ 高机位/俯拍 high angle / top-down ｜ 过肩 over-the-shoulder ｜ 背影 back view ｜ 鱼眼 fisheye close-up

## 3. 运镜词表（给 ember-clips 用）
| 中文 | 英文提示词 | 适合 |
|---|---|---|
| 慢推 | slow push-in toward the subject | 铺垫、情绪 |
| 慢拉 | slow pull-back revealing the scene | 段落开头 |
| 横移 | lateral tracking shot, camera slides left to right | 走路、街景 |
| 后退跟拍 | camera dollies backward as the subject walks toward it | 走路 |
| 环绕 90° | camera arcs 90 degrees around the subject | 中景（**不要 360°**） |
| dolly zoom | dolly zoom (vertigo effect), background stretches | 情绪转折、drop |
| crash zoom | sudden fast crash zoom into the face | 大落点 |
| 桶滚 | camera barrel-rolls 90 degrees on the beat | 大落点（注意配饰别翻出画） |
| 升降 | crane up from ground level to eye level | 段落开头 |
| 手持 | handheld, subtle shake | 街头、贴近 |

## 4. 场景库（按风格挑，12 个以上不重复）
- 霓虹街头：天桥车流、霓虹招牌、地铁站台列车进站、地铁车厢、涂鸦隧道、天台、旧街区铁丝网、停车场、楼梯间、走廊、便利店门口、雨夜路口
- 日出正能量：海边日出、天台晨光、跑道、花田、玻璃办公室、城市天际线、自行车道、咖啡馆窗边、山顶、公园草坪、桥上、晨跑街道
- lofi 怀旧：老房间书桌、黄昏公交、雨窗、旧唱片店、天台晾衣、小巷、夜市、自习室、窗台猫、铁轨、老电梯、街角路灯
- 方块像素世界：方块森林、像素城市、发光洞穴、浮空岛、方块海边、夜空萤火、像素集市、瀑布、雪山、灯塔、桥、传送门

## 5. 节奏参考
- 30 秒 ≈ 开场纯字幕 2 小节 + 正常段每小节一刀 + 副歌/drop 每半小节一刀 + 片尾 1.5 小节。
- 主人说「太慢」：把 `--bars` 从 2 改 1，或把 `--fast-from` 提前；说「太乱」：反过来。
