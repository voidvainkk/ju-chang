# -*- coding: utf-8 -*-
"""界面流程冒烟：不经过浏览器，直接把 loop 走到底，看有没有卡死/报错。

每次改动 loop.py 都跑一遍：python tools/_smoke_loop.py
"""
import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "game"))
import engine as E, loop as L

STEPS = int(sys.argv[1]) if len(sys.argv) > 1 else 400
ok = 0
for seed in range(3):
    g = L.Game(seed=seed)
    n = 0
    last = None
    while n < STEPS:
        cur = g.current()
        if cur is None:
            break
        n += 1
        t = cur.get("type")
        if t == "name":
            if cur.get("stage") == "style":
                g.pick_style(cur["styles"][0]["id"])
            else:
                g.set_name(cur["candidates"][0])
        elif t == "choice":
            kind = cur.get("kind")
            oid = cur["options"][0]["id"]
            if kind == "intro":
                g.choose_intro(oid)
            elif kind == "act":
                g.choose_act(oid)
            elif kind == "empty":
                g.choose_empty(oid)
            elif kind == "leave":
                g.choose_leave(oid)
            elif kind == "offer":
                g.choose_offer(oid)
        elif t in ("card", "chat"):
            oid = cur["options"][0]["id"]
            g.choose_talk(oid) if cur.get("talk") else g.choose_card(oid)
        elif t == "end":
            last = cur.get("ending")
            break
        else:
            g.advance()
    print("seed", seed, "步数", n, "结局", last or "（没走到结局）",
          "周", (g.state or {}).get("week"))
    ok += 1 if last else 0
print("走到结局:", ok, "/ 3")
