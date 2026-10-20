# 灵境 Lingverse

> 一组能直接安装的 Grok Bot。每位「灵」只做好一件事。
> A family of installable Grok Bots ("spirits"). Each spirit does one job well.

| 灵 | 做什么 | 版本 |
|---|---|---|
| **墨灵 Moling** | 长文写手，写给需要流量的项目操盘手和自媒体创业者 | `moling-v0.1.0` |

## 墨灵 · Moling

墨灵先学你自己的口吻，写出来的东西像你，读不出 AI 味。选题只从你亲手干过的事里挑：踩过的坑、算过的账、当时是怎么想的，让读者觉得「这说的就是我」。再用标题公式、开头和收藏件把文章往爆款和收藏上推。一篇写完，改成 X Article、公众号、抖音长文、小红书、知乎专栏、微博头条各自的版本。墨灵只交文本，**从不替你发布**。

Moling writes long-form posts for project operators and self-media founders who need traffic. It learns your voice, writes from your real pits and numbers with no AI flavor, aims for viral and bookmark-worthy pieces, and rewrites each one for X, WeChat, Douyin, Xiaohongshu, Zhihu and Weibo. It hands you text only and never publishes for you.

**流程 / Flow：** 入门对话 → 口吻学习 → 选题与标题 → 结构与开头 → 写初稿 → 去 AI 味（深改）→ 多平台改写 → 配图与封面 → 发布前自检

### 安装 / Install

一行：从资料卡导入墨灵模板（链接发布后补上；仓库：github.com/lingverse-ai/lingverse），然后对它说：

```
安装墨灵
```

One line: import the Moling template, then say **"安装墨灵"** (install Moling). The `moling-install` skill fetches the pinned tag `moling-v<VERSION>` from this repo and writes every skill into your bot. It installs no plugins and asks for no keys. If GitHub is unreachable, Moling finishes onboarding first and retries next time.

### 更新 / Updates

- 版本只走 git 标签（`moling-vX.Y.Z`），不追 `main`，所以每个人装到的都是测过的版本。
- `moling-update` 每周最多自动查一次；有新版先用 4 行以内说明改了什么，**你同意才装**。
- 作者档案、口吻档案存在你自己的记忆里，安装和更新都不会覆盖。

Updates ship as git tags. Moling checks at most weekly, tells you what changed, and installs only after you say yes. Your profiles are never overwritten.

## 仓库结构 / Layout

```
shared/                 人设规范、安装技能写法（所有灵共用）
tools/                  validate.py（检查）· pack.py（打包配方）· check_draft.py（稿件机械检查）
spirits/moling/
  VERSION  profile.json  memory.md  DESIGN.md
  skills/moling-*/      11 个技能；规格卡 platforms.md 在 moling-multi-platform/ 里
  examples/             全部是虚构主人的示例
  tests/                fixtures/ + expected/ + run_tests.py
  dist/                 recipe.json（完整配方）· template.json（薄模板），由 pack.py 生成
```

## 开发 / Development

```bash
python3 tools/validate.py                 # frontmatter、大小、交叉引用、隐私、他人痕迹、平台数字、refs 路径
python3 tools/pack.py moling              # 重新生成 dist/
python3 tools/pack.py --check             # CI：dist 必须是最新的
python3 spirits/moling/tests/run_tests.py # 夹具 + 反向用例
```

只用 Python 3 标准库，不需要安装依赖。见 [CONTRIBUTING.md](CONTRIBUTING.md)。

## 许可 / License

版权所有 © 2026 小爷。双许可，详见 [LICENSE](LICENSE)：
- **内容**（技能、示例、资料卡、记忆、shared/ 和所有文档）：[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)，转载或改编请署名「灵境 Lingverse · 小爷」并附仓库链接。
- **工具代码**（tools/、tests/、.github/）：MIT。

Copyright © 2026 小爷. Content and skills: CC BY 4.0. Tooling (tools/, tests/, .github/): MIT.
