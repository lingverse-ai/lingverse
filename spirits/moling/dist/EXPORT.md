# 导出墨灵分享卡（给墨灵 bot 看的操作单）· v0.1.1

**旧卡（v0.1.0）要作废，重新导出一张。** 旧卡的入门技能是 moling-getting-started，第一轮直接开始问问题，安装从来没被触发。

调用 `CreateBotShareJson`，参数全部取自同目录的 `template.json`（由 `tools/pack.py` 生成，标签 moling-v0.1.1），逐字使用，不要改写：

| 参数 | 填什么 |
|---|---|
| name | `墨灵 Moling` |
| 资料卡指令 / persona（profile.description） | template.json → `profile.description`（第一句就是「每次对话的第一件事：检查 moling- 技能有没有 11 个……先运行 moling-install」） |
| 店面简介（≤400 字符） | template.json → `_meta.storefront` |
| visibility | `public` |
| gettingStarted | **`moling-install`**（不是 moling-getting-started） |
| skills | 只放两个：`moling-install`、`moling-getting-started`（template.json → `skills`） |
| memory | template.json → `memory`（kind=log，「墨灵安装记录」那一条） |

**不放进卡里：** 其余 9 个技能，由 moling-install 第一轮从标签 moling-v0.1.1 装进去。主人的作者档案、口吻档案也不放。

**导出后自测（必须做）：** 用一个全新的 bot 导入新卡，说「你好」。第一条回复必须以「已装好 11 个技能（墨灵 v0.1.1）。」开头，接着是入门对话的第 1 题。再让它 `ls` 技能目录，确认有 11 个 moling- 技能，`moling-multi-platform/` 里有 `platforms.md`。

**导出前检查：** `python3 tools/pack.py --check` 显示最新；仓库是公开的；卡里没有密钥、内部网址、真实客户信息。
