# 发布清单 RELEASE（每一位灵、每一个版本都照做）

> 来由：墨灵 v0.1.0 的分享卡导进新 Bot 后**一个技能都没有**。原因是入门技能抢在安装前面、记忆里没有仓库地址、模板字段不对。下面每一条都是为了让这件事不再发生。

## 1. 自动检查（`python3 tools/validate.py` 全部 OK 才能继续）
validate 对 `spirits/` 下每一位灵都检查：
- [ ] 店面介绍（`profile.json` 的 `description`）写明三样：安装技能名 `<灵>-install`、仓库 `github.com/<owner>/lingverse`、标签 `<灵>-v<VERSION>`。
- [ ] 分享卡的安装记忆是 `kind=profile`（不是 log）。
- [ ] 分享卡 `gettingStarted` = `<灵>-install`；卡里带 `<灵>-install` 和 `<灵>-getting-started` 两个技能。
- [ ] `install.sh` 存在，生成后的标签 `T=<灵>-v<VERSION>` 和 `VERSION` 一致，没有没填的占位符。
- [ ] 人设 instructions 和安装记忆里都有：install.sh 一行命令、配方 raw 地址、仓库地址、「N 个技能」（N = 实际技能数）。
- [ ] `<灵>-install` 里有一行命令、配方地址、`NO_SKILL_DIR` 兜底、「已装好 N 个技能」。
- [ ] 单个 SKILL.md ≤ 6KB；SKILL.md + profile + memory 合计 ≤ 80KB；参考文件单个 ≤ 12KB。
- [ ] 私人词、其他创作者名、旧素材目录路径扫描通过。

## 2. 打包和测试
```bash
python3 tools/pack.py                    # 重新生成 dist/
python3 tools/pack.py --check            # dist 是最新的
python3 tools/validate.py
python3 spirits/<灵>/tests/run_tests.py  # 每位灵自己的测试
```
- [ ] `CHANGELOG.md` 写了这一版改了什么；README 徽章版本号更新。

## 3. 推送和打标签（需要主人批准）
```bash
git push origin main
git tag -a <灵>-v<VERSION> -m "<灵> v<VERSION>" && git push origin <灵>-v<VERSION>
python3 tools/validate.py --online <灵>  # 标签下的 recipe.json 和 install.sh 能打开
```
- [ ] `--online` 通过（配方在标签下可达）。

## 4. 干净环境安装测试（自动）
在没有 gh、没有登录的临时目录里：
```bash
EMBER_SKILL_DIR=/tmp/t-skills MOLING_SKILL_DIR=/tmp/t-skills bash -c "curl -fsSL https://raw.githubusercontent.com/<owner>/lingverse/<灵>-v<VERSION>/spirits/<灵>/dist/install.sh | bash"
```
- [ ] 输出 `INSTALLED N`，`/tmp/t-skills` 里有 N 个 `<灵>-` 技能。
- [ ] 把 git 屏蔽掉（`PATH` 里去掉 git）再跑一次：走 curl 兜底也是 `INSTALLED N`。
- [ ] 不给技能目录（`<灵>_SKILL_DIR` 指向不存在且找不到默认目录）：输出 `NO_SKILL_DIR`。

## 5. 强制人工关口：新 Bot 导入测试（不过不许对外分享）
1. 用 `spirits/<灵>/dist/template.json` 的内容在 Grok Bot 里**新建一个全新的 Bot**（不要用已经装过的 Bot）。
2. 对它说「你好」。
3. 通过标准：它的**第一条回复第一句**是「已装好 N 个技能（<灵名> v<VERSION>）。」，N 等于实际技能数；同一条消息接着入门第 1 步。
4. 再问一句「你有哪些技能？」，列出的技能和 recipe.json 一致。
5. 截图存档，写进 `spirits/<灵>/dist/EXPORT.md` 的测试记录。
- [ ] 新 Bot 测试通过，截图已存。

**任何一步没过：不分享卡片、不发公告，先修再从第 1 步重来。**
