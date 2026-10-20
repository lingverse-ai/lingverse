"""打印一个词的哈希条目，用来加进 scrub_hashes.json（名单本身不进仓库）。"""
import hashlib, json, sys
for t in sys.argv[1:]:
    n = "".join(t.lower().split())
    print(json.dumps({"sha256": hashlib.sha256(n.encode()).hexdigest(), "len": len(n)}))
