# -*- coding: utf-8 -*-
"""查：每张卡的 gate 在真实一局里到底什么时候能开、开了以后还剩多长的可抽时间。

假设（用户 2026-11-14 的猜测）：「很多卡的前置条件其实很难达到」。
只读，不改任何数据。
"""
import sys, os, collections

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "game"))
import engine as E, loop as L

w = E.load_world()
cards = [c for c in w["cards"] if c.get("options")]

# 1) 用 15 局界面流程，记录每周结束时每张卡的 gate 是否通过
seasons = 15
openlog = collections.defaultdict(lambda: [0] * 7)      # id -> week1..6 可开周数计
totals = collections.Counter()
never = collections.Counter()
for seed in range(seasons):
    g = L.Game(seed=seed)
    last_week = 0
    while True:
        cur = g.current()
        if cur is None:
            break
        t = cur.get("type")
        if t == "name":
            g.pick_style(cur["styles"][0]["id"]) if cur.get("stage") == "style" else g.set_name(cur["candidates"][0])
        elif t == "choice":
            g.choose_intro(cur["options"][0]["id"]) if cur.get("kind") == "intro" else g.choose_act("dance")
        elif t == "card":
            g.choose_talk(cur["options"][0]["id"]) if cur.get("talk") else g.choose_card(cur["options"][0]["id"])
        elif t == "end":
            break
        else:
            g.advance()
        wk = min(6, int((g.state or {}).get("week", 1) or 1))
        if wk != last_week:
            last_week = wk
            for c in cards:
                try:
                    ok = E.eval_gate(g.state, c.get("gate"))
                except Exception:
                    ok = False
                if ok:
                    openlog[c["id"]][wk] += 1
                    totals[c["id"]] += 1

print("卡总数", len(cards))
rows = []
for c in cards:
    oid = c["id"]
    n = totals.get(oid, 0)
    rows.append((n, c.get("type"), c.get("title"), c.get("gate")))
rows.sort()
print("\n—— 可开周数最少的 25 张（15 局 × 最多 6 周 = 最多 90）——")
for n, typ, title, gate in rows[:25]:
    print(f"{n:3d}  {typ:6s} {str(title)[:22]:24s} {gate}")
print("\n—— 可开周数最多的 10 张 ——")
for n, typ, title, gate in rows[-10:]:
    print(f"{n:3d}  {typ:6s} {str(title)[:22]:24s} {gate}")

zero = [r for r in rows if r[0] == 0]
print("\n整季从来不可开的卡:", len(zero))
for n, typ, title, gate in zero:
    print("   ", typ, title, "|", gate)
