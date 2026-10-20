"""项目进度表：看项目文件夹里有什么，告诉你现在到哪一步、下一步做什么（换了对话也能接着干）。
用法：python3 state.py status <项目目录>          打印 8 步进度和下一步命令
      python3 state.py decide <项目目录> "原话"   主人拍板的话原样记进 DECISIONS.md（带北京时间）
      python3 state.py run <项目目录> <名字> -- <命令…>   长任务后台跑，日志写 runs/，记进 RUNS.md
      python3 state.py runs <项目目录>            看后台任务是不是还在跑
      python3 state.py gate <项目目录> <关卡> ok   主人在某个关卡点了头（brief/lead/board/excerpt/final）"""
import datetime, json, os, subprocess, sys
from pathlib import Path

BJ = datetime.timezone(datetime.timedelta(hours=8))
now = lambda: datetime.datetime.now(BJ).strftime("%Y-%m-%d %H:%M 北京时间")
T = Path(__file__).parent


def has(d, *globs):
    return any(list(d.glob(g)) for g in globs)


def steps(d):
    g = load_gates(d)
    return [  # （名字, 完成了没, 下一步怎么做）
        ("1 选题和风格（题材/风格/滤镜/时长/画幅，按钮选）", "brief" in g, "ember-getting-started：发选择题，答完 state.py gate . brief ok"),
        ("2 主角设定 + 4 张试镜图（特写/半身/全身/远景）", "lead" in g, "ember-character-bible：出设定 + 4 张试镜图给主人选，选定 gate lead ok"),
        ("3 歌（Suno 或自带）+ 拍点 + 歌词对时间", has(d, "beatmap.json") and has(d, "words.json", "lyrics.none"),
         f"python3 {T}/beatmap.py song.mp3 beatmap.json；有词：python3 {T}/lyrics_align.py song.mp3 lyrics.txt words.json"),
        ("4 分镜表（钩子 + 主线 + 每句一个画面点子）", has(d, "storyboard.md") and "board" in g, "ember-beat-storyboard：写 storyboard.md，给主人看，gate board ok"),
        ("5 画面（静帧 + 动起来的片段）", has(d, "stills/*", "clips/*"), "ember-stills / ember-clips：按分镜出图出片，qc.py clips 看一遍"),
        ("6 剪辑工程 + 自检", has(d, "project.json") and has(d, "audit.ok"), f"写 project.json，python3 {T}/audit.py project.json 直到 PASS"),
        ("7 片段先审（20–40 秒）", "excerpt" in g, f"python3 {T}/render.py project.json out/excerpt.mp4 --preview --excerpt A-B，发给主人，gate excerpt ok"),
        ("8 成片 + 质检 + 分享版 + 发布文案", "final" in g, f"render.py → qc.py out/final.mp4 --sheet → qc.py share；主人认可后 gate final ok"),
    ]


def load_gates(d):
    f = d / "gates.json"
    return json.loads(f.read_text()) if f.exists() else {}


def status(d):
    nxt = None
    for name, done, how in steps(d):
        print(("✅ " if done else "⬜ ") + name)
        if not done and nxt is None: nxt = how
    print("\n下一步：" + (nxt or "全部完成 🎉 草稿交给主人自己发布"))
    live = [r for r in read_runs(d) if r["alive"]]
    if live: print("后台还在跑：" + "，".join(r["name"] for r in live) + "（等的时候告诉主人：好了说「继续」）")


def read_runs(d):
    out = []
    for line in (d / "runs" / "index.jsonl").read_text().splitlines() if (d / "runs" / "index.jsonl").exists() else []:
        r = json.loads(line)
        try: os.kill(r["pid"], 0); r["alive"] = True
        except OSError: r["alive"] = False
        out.append(r)
    return out


def main():
    a = sys.argv[1:]
    if len(a) < 2: sys.exit(__doc__)
    cmd, d = a[0], Path(a[1]); d.mkdir(parents=True, exist_ok=True)
    if cmd == "status": status(d)
    elif cmd == "decide":
        with open(d / "DECISIONS.md", "a", encoding="utf-8") as f: f.write(f"- {now()}：{a[2]}\n")
        print("已记录")
    elif cmd == "gate":
        g = load_gates(d); g[a[2]] = now() if a[3:4] == ["ok"] else g.pop(a[2], None)
        g = {k: v for k, v in g.items() if v}; (d / "gates.json").write_text(json.dumps(g, ensure_ascii=False, indent=1)); print(g)
    elif cmd == "run":
        name, argv = a[2], a[a.index("--") + 1:]
        (d / "runs").mkdir(exist_ok=True); log = d / "runs" / f"{name}.log"
        p = subprocess.Popen(argv, stdout=open(log, "w"), stderr=subprocess.STDOUT, start_new_session=True, cwd=d)
        with open(d / "runs" / "index.jsonl", "a") as f: f.write(json.dumps({"name": name, "pid": p.pid, "log": str(log), "at": now(), "cmd": argv}, ensure_ascii=False) + "\n")
        with open(d / "RUNS.md", "a", encoding="utf-8") as f: f.write(f"- {now()} {name} pid={p.pid} 日志 runs/{name}.log\n")
        print(f"后台开始 {name}（pid {p.pid}）。告诉主人：大概要等几分钟，好了说「继续」。")
    elif cmd == "runs":
        for r in read_runs(d): print(("运行中 " if r["alive"] else "已结束 ") + f"{r['name']} {r['at']} {r['log']}")
    else: sys.exit(__doc__)


if __name__ == "__main__":
    main()
