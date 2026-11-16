# -*- coding: utf-8 -*-
"""验证：一周里所有卡的选择屏，是否全部发生在「结算之前」。

以前特典对话（talk 卡）之前会冒出一张 gap 卡，就是因为它排在结算之后。
"""
import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "game"))
import engine as E, loop as L


def run(seed):
    g = L.Game(seed=seed)
    seq = []
    guard = 0
    while guard < 900:
        guard += 1
        c = g.current()
        if c is None:
            break
        t = c.get("type")
        settled = g.state.get("_settled_week") == g.state.get("week") if g.state else False
        if t == "card":
            seq.append(("card", c.get("talk"), c.get("origin"), settled, g.state.get("week")))
        elif t == "name":
            g.pick_style(c["styles"][0]["id"]) if c.get("stage") == "style" else g.set_name(c["candidates"][0])
        elif t == "choice":
            k = c.get("kind"); oid = c["options"][0]["id"]
            if k == "intro": g.choose_intro(oid)
            elif k == "act": g.choose_act(oid)
            elif k == "empty": g.choose_empty(oid)
            elif k == "leave": g.choose_leave(oid)
        elif t == "card":
            oid = c["options"][0]["id"]
            if c.get("line"): g.choose_story(oid)
            elif c.get("talk"): g.choose_talk(oid)
            else: g.choose_card(oid)
        elif t == "end":
            break
        else:
            g.advance()
    return seq


bad = 0
talk_after_gap = 0
for seed in range(6):
    seq = run(seed)
    for i, (t, talk, origin, settled, wk) in enumerate(seq):
        if talk and i > 0 and seq[i - 1][2] == "gap":
            talk_after_gap += 1
        if settled and not talk:
            bad += 1
print("非特典卡在结算之后被点开:", bad)
print("特典对话紧跟在 gap 卡之后:", talk_after_gap)
