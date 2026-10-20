# 导出墨灵分享卡（给墨灵 bot 看的操作单）

调用 `CreateBotShareJson`，参数按下面填。内容以同目录的 `template.json` 为准（由 `tools/pack.py` 生成，版本 moling-v0.1.0）。

| 参数 | 填什么 |
|---|---|
| name | `墨灵 Moling` |
| description（店面简介，≤400 字符） | `墨灵只写长文：先学你的口吻，写出来像你、没有 AI 味；选题只用你的真事，按真正的爆款写法出标题、开头和收藏件。公众号首发，再改成 X、抖音长文、小红书、知乎、微博各自的版本。写给需要流量的项目操盘手和自媒体创业者。只交文本，不替你发布。` |
| visibility | `public` |
| gettingStarted | `moling-getting-started` |
| skills | 只放两个：`moling-getting-started`、`moling-install`（逐字使用 template.json 里的内容） |
| persona / profile | template.json 的 `profile`（name、intro、intro_en） |
| memory | template.json 的 `memory`（墨灵安装记录那一条） |

**不要放进卡里：** 其余 9 个技能（moling-voice-profile、moling-topic-and-title、moling-structure-and-opening、moling-first-draft、moling-de-ai-edit、moling-multi-platform、moling-cover-and-images、moling-pre-publish-check、moling-update）。它们由 moling-install 在第一次对话时从标签 moling-v0.1.0 装进去。主人的作者档案、口吻档案也不要放进卡里。

**导出前检查：**
1. `python3 tools/pack.py --check` 显示 dist 是最新的。
2. 仓库必须是**公开**的，否则新主人装不上完整技能（现在仍是私有）。
3. 卡里不出现任何密钥、内部网址和真实客户信息。
