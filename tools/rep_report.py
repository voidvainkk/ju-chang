# -*- coding: utf-8 -*-
"""查：一季里同一张卡最多出现几次、哪些卡反复出现。

用户 2026-11-14：「同样的卡反复出现，像在刷同一张」。
先量再改——这里只读，不改任何数据。
"""
import sys, collections, os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "game"))
import engine as E, loop as L
import policy as P

MIX = ["dance", "rest", "sing", "work", "dance", "rest"]

w = E.load_world()
titles = {}
for c in w["cards"]:
    titles[c["id"]] = c.get("title") or c["id"]

dup_hist = collections.Counter()     # 同一季里出现 n 次的卡，有多少
reps = collections.Counter()
seasons = 15
for seed in range(seasons):
    g = L.Game(seed=seed)
    seen = collections.Counter()
    while True:
        cur = g.current()
        if cur is None:
            break
        t = cur.get("type")
        if t == "name":
            g.pick_style(cur["styles"][0]["id"]) if cur.get("stage") == "style" else g.set_name(cur["candidates"][0])
        elif t == "choice":
            g.choose_intro(cur["options"][0]["id"]) if cur.get("kind") == "intro" else g.choose_act(MIX[len(seen) % 6])
        elif t == "card":
            seen[cur.get("title") or ""] += 1
            oid = cur["options"][0]["id"]
            if cur.get("talk"):
                g.choose_talk(oid)
            elif cur.get("line"):
                g.choose_story(oid)
            else:
                g.choose_card(oid)
        elif t == "end":
            break
        else:
            g.advance()
    for t, n in seen.items():
        dup_hist[n] += 1
        reps[t] += 1
    total = sum(seen.values())
    print("seed", seed, "卡数", total, "不同", len(seen), "重复最多的:", seen.most_common(3))

print("\n同一季里出现 n 次的（卡·季）次数:", dict(sorted(dup_hist.items())))
print("跨季出现最多的 10:", reps.most_common(10))
