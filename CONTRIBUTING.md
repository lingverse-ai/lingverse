# 参与贡献

1. **技能规则：** 每个技能放在 `spirits/<灵>/skills/<灵>-<名字>/SKILL.md`，开头 frontmatter 写 `name`（和目录名一致）、`description`（写清什么时候用，≤400 字符）。单个 SKILL.md ≤6144 字节，一位灵的全部内容 ≤80KB。放不下的细节，写成同一目录下的附带文件，用反引号引用文件名。
2. **原创：** 用自己的话写。不复制其他创作者的句子、例子和自创术语，正文里也不点名其他创作者。CI 有痕迹扫描。
3. **隐私：** 示例只能用虚构主人，并标「示例」。不放真实姓名、账号、客户和收入数字。CI 有私人词扫描，名单只存哈希（`tools/scrub_hashes.json`）。新增名单词：`python3 tools/scrub_hash.py <词>`，词本身不要提交。
4. **平台数字：** 标题上限、封面比例以 `moling-multi-platform/platforms.md` 为准。技能里的速查表必须和它一致，CI 会比对。
5. **提交前：** 跑 `python3 tools/validate.py && python3 tools/pack.py && python3 spirits/moling/tests/run_tests.py`，dist/ 一起提交。
6. **发版：** 改 `VERSION`，在 `CHANGELOG.md` 写清改了什么（`moling-update` 会把它读给用户），打标签 `moling-vX.Y.Z`。
7. **夹具：** 新规则尽量配一份 `tests/fixtures/*.json` 和对应的 `tests/expected/*.json`；干净稿也要有，防止误报。
