# -*- coding: utf-8 -*-
"""看看「风」有没有吹起来：15 局界面流程，每周打印关键量的分布（中位/最大）。"""
import sys, os, statistics

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "game"))
import engine as E, loop as L

KEYS = ("fame", "enjou", "banzi", "kaibox", "shiroi", "heat", "zhong")
series = {k: [] for k in KEYS}

for seed in range(15):
    g = L.Game(seed=seed)
    last = 0
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
        st = g.state or {}
        wk = min(6, int(st.get("week", 1) or 1))
        if wk != last:
            last = wk
            for k in KEYS:
                series[k].append(float(st.get(k) or 0))

for k in KEYS:
    xs = series[k]
    print("%-7s 周均 %.1f 中位 %.1f 最大 %.1f  >0的占比 %.0f%%" % (
        k, statistics.mean(xs), statistics.median(xs), max(xs),
        100.0 * sum(1 for x in xs if x > 0) / len(xs)))
