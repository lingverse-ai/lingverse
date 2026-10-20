"""墨灵测试：夹具检查 + 仓库检查的反向用例。用法：python3 spirits/moling/tests/run_tests.py"""
import json, shutil, subprocess, sys, tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from check_draft import check

fails = 0


def report(ok, name, detail=""):
    global fails
    fails += not ok
    print(("PASS " if ok else "FAIL ") + name + (f"  {detail}" if detail else ""))


# 1. 夹具：查出的问题代码必须和 expected 完全一致（不漏报，也不误报）
for f in sorted((HERE / "fixtures").glob("*.json")):
    got = sorted({i["code"] for i in check(json.loads(f.read_text(encoding="utf-8")))})
    want = sorted(json.loads((HERE / "expected" / f.name).read_text(encoding="utf-8"))["expect"])
    report(got == want, f"fixture {f.stem}", f"got={got} want={want}")


# 2. 仓库检查本身要通过
r = subprocess.run([sys.executable, str(ROOT / "tools" / "validate.py"), str(ROOT)], capture_output=True, text=True)
report(r.returncode == 0, "validate: 当前仓库", r.stdout.strip().splitlines()[-1])


# 3. 反向用例：往仓库副本里埋一个错，validate 必须失败并报出对应类别
def mutate(tag, fn):
    with tempfile.TemporaryDirectory() as td:
        dst = Path(td) / "repo"
        shutil.copytree(ROOT, dst, ignore=shutil.ignore_patterns(".git", "__pycache__"))
        fn(dst)
        r = subprocess.run([sys.executable, str(dst / "tools" / "validate.py"), str(dst)], capture_output=True, text=True)
        report(r.returncode == 1 and f"[{tag}]" in r.stdout, f"validate 能拦住 {tag}")


SK = Path("spirits/moling/skills")


def append(rel, text):
    return lambda d: (d / rel).write_text((d / rel).read_text(encoding="utf-8") + text, encoding="utf-8")


# 私人词和他人痕迹用码点拼出来，避免仓库里出现明文
private_term = chr(0x5C0F) + chr(0x7237)
creator_term = "".join(map(chr, (0x5361, 0x5179, 0x514B)))
mutate("budget", append(SK / "moling-first-draft/SKILL.md", "啊" * 3000))
mutate("private", append(SK / "moling-first-draft/SKILL.md", "\n" + private_term + "\n"))
mutate("private", append("CONTRIBUTING.md", "\n" + private_term + "\n"))  # 放行只限 LICENSE/README
mutate("trace", append("spirits/moling/examples/02-样稿-老周.md", "\n" + creator_term + "\n"))
mutate("refs", append(SK / "moling-first-draft/SKILL.md", "\n见 `re" + "fs/platforms.md`\n"))
mutate("xref", append(SK / "moling-first-draft/SKILL.md", "\n交给 moling-nonexistent。\n"))
mutate("platform", append(SK / "moling-topic-and-title/SKILL.md", "\n| 平台 | 标题上限 |\n|---|---|\n| 抖音长文 | ≤55 字 |\n"))
mutate("frontmatter", lambda d: (d / SK / "moling-first-draft/SKILL.md").write_text("没有头部\n", encoding="utf-8"))

print(f"\n{'全部通过' if not fails else f'{fails} 项失败'}")
sys.exit(1 if fails else 0)
