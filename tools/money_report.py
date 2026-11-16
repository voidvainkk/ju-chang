# -*- coding: utf-8 -*-
"""看钱的走势：一季下来玩家到底会不会「穷」。

用户 2026-11-14：「感觉很多要穷的都碰不上」。
"""
import sys, os, statistics

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "game"))
import engine as E, loop as L

weeks = []
for seed in range(15):
    g = L.Game(seed=seed)
    last = None
    while True:
        c = g.current()
        if c is None:
            break
        t = c.get("type")
        if t == "name":
            g.pick_style(c["styles"][0]["id"]) if c.get("stage") == "style" else g.set_name(c["candidates"][0])
        elif t == "choice":
            k = c.get("kind"); oid = c["options"][0]["id"]
            if k == "intro": g.choose_intro(oid)
            elif k == "act": g.choose_act(oid)
            elif k == "empty": g.choose_empty(oid)
            elif k == "leave": g.choose_leave(oid)
        elif t == "card":
            oid = c["options"][0]["id"]
            if c.get("line"):
                g.choose_story(oid)
            elif c.get("talk"):
                g.choose_talk(oid)
            else:
                g.choose_card(oid)
        elif t == "end":
            break
        else:
            g.advance()
        st = g.state
        if st and st.get("week") != last:
            last = st.get("week")
            weeks.append((st["week"], st["money"], st.get("_income_last") or 0))

for wk in range(1, 8):
    xs = [m for w, m, _ in weeks if w == wk]
    inc = [i for w, _, i in weeks if w == wk]
    if xs:
        print("周%d  钱 中位 %5.0f  最低 %5.0f  最高 %5.0f | 上周进账 中位 %5.0f"
              % (wk, statistics.median(xs), min(xs), max(xs),
                 statistics.median(inc) if inc else 0))
low = [1 for _, m, _ in weeks if m < 1500]
print("钱 < 1500 的周数占比 %.0f%%" % (100.0 * len(low) / max(1, len(weeks))))
