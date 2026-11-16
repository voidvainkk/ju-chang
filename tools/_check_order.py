# -*- coding: utf-8 -*-
"""把事件卡的事检查一遍：一周里那些卡在什么位置、碰没碰到特典、回执后面跟的是不是行动。"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "game"))
import loop as L

bad = 0
for seed in range(6):
    g = L.Game(seed=seed)
    g.advance(); g.advance(); g.advance()      # 序章三屏（三选一已删，读完直接取名）
    seq = []
    for n in range(1200):
        c = g.current()
        if c is None:
            break
        t = c.get("type")
        if t == "name":
            if c.get("stage") == "style":
                g.pick_style(c["styles"][0]["id"])
            else:
                g.set_name(c["candidates"][0])
            continue
        if t == "card":
            tag = ("WEEK" if c.get("origin") == "week" else
                   "TALK" if c.get("talk") else
                   "LINE" if c.get("line") else "CARD")
            seq.append(tag)
            oid = c["options"][0]["id"]
            if c.get("talk"):
                g.choose_talk(oid)
            elif c.get("line"):
                g.choose_story(oid)
            else:
                g.choose_card(oid)
        elif t == "choice" and c.get("kind") == "act":
            seq.append("act")
            g.choose_act(c["options"][0]["id"])
        else:
            if t in ("bill", "panel", "live"):
                seq.append(t)
            g.advance()
        if t == "end":
            break
    # 检查：WEEK 卡必须出现在 live(周六) 之后、bill 之前
    s = " ".join(seq)
    i = 0
    ok = True
    while True:
        i = s.find("WEEK", i)
        if i < 0:
            break
        before = s[:i].split()
        after = s[i:].split()
        if "live" not in before[-4:]:
            print("seed", seed, "WEEK 卡不在周六场之后:", before[-6:], "|", after[:4]); ok = False
        if "TALK" in after[:6]:
            print("seed", seed, "WEEK 卡紧贴特典:", after[:6]); ok = False
        i += 4
    if not ok:
        bad += 1
    print("seed", seed, "卡序:", [x for x in seq if x in ("WEEK", "TALK", "LINE", "act", "bill", "live")][:40])
print("有问题:", bad)
