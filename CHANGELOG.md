# Changelog

格式参考 Keep a Changelog；每位灵单独打标签（`<spirit>-vX.Y.Z`）。

## moling-v0.1.2 — 2026-10-20

修复：导入后只带进一条记忆，技能正文没到，bot 找不到仓库。
- 资料卡指令（persona）和那条记忆里都直接写上完整仓库地址、标签、raw 配方地址和完整安装步骤，就算一个技能都没带进来也能装。
- 新增 `spirits/moling/dist/install.sh`：一行 `curl … | bash` 就能装（git clone 失败自动改用 curl 拉配方）。
- 入门对话开头自带安装命令，单独也能完成安装。
- README 补了「moling lingverse」检索词和手动安装命令；仓库加了 description 和 topics。

## moling-v0.1.1 — 2026-10-20

修复：从分享卡导入后没有装上完整技能包。
- 分享卡的 gettingStarted 改成 `moling-install`：第一轮先装，再入门。
- 资料卡加了 bot 指令，记忆和入门对话开头都写明「moling- 技能不满 11 个就先装」。
- moling-install 改成可以直接运行的脚本：用 git 克隆固定标签，失败就用 curl 拉 raw 的 recipe.json，不需要 gh、不需要登录、不先问主人；写入后报告「已装好 N 个技能」。找不到技能目录时改用技能工具逐个写入。
- template.json 改成 Grok Bot 模板的字段格式（profile / memory / skills / gettingStarted）。

## moling-v0.1.0 — 2026-10-20

首个版本。
- 11 个技能：安装、更新、入门对话（含演练模式）、口吻学习、选题与标题、结构与开头、写初稿（含「真实感与共鸣」）、去 AI 味改稿（默认深改、只补档案里已有的料）、多平台改写（6 个平台，附 platforms.md 规格卡和 X / 公众号爆款要点）、配图与封面、发布前自检（19 项）。
- 小红书：长文正文 ≤6000 字、封面 3:4（1080×1440），这两项是半核实（公开资料一致，官方页面看不到）。
- 工具：validate.py、pack.py、check_draft.py；CI 跑检查、配方是否最新、测试。
