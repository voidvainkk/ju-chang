# -*- coding: utf-8 -*-
"""剧情线可开性（正确版）：用 line_stage() 判「这一周这条线的下一拍能不能推」。

v1 用 _gate_ok 判全部拍，结果全是 True——因为 evaluated 的是拍本身而不是「下一拍」。
只读。
"""
import sys, os, collections

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "game"))
import engine as E, loop as L

w = E.load_world()
lines = w["lines"]
openlog = collections.Counter()
samples = collections.Counter()
reached = collections.Counter()

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
            if cur.get("line"):
                g.choose_story(cur["options"][0]["id"])
            else:
                g.choose_talk(cur["options"][0]["id"]) if cur.get("talk") else g.choose_card(cur["options"][0]["id"])
        elif t == "end":
            break
        else:
            g.advance()
        st = g.state or {}
        wk = min(6, int(st.get("week", 1) or 1))
        if wk != last:
            last = wk
            for line in lines:
                lid = line["_meta"]["id"]
                prog = st.get("story", {}).get(lid)
                nxt = 0 if prog is None else prog["stage"] + 1
                k = "%s/S%d" % (lid, nxt)
                samples[k] += 1
                _st = dict(st)
                _st.setdefault("week", wk)
                _st.setdefault("story", st.get("story") or {})
                _st.setdefault("flags", set())
                _st.setdefault("ota", st.get("ota") or [])
                _st.setdefault("cooldown", st.get("cooldown") or {})
                _st.setdefault("_line_cool", st.get("_line_cool") or {})
                _st.setdefault("_line_week", st.get("_line_week") or {})
                _st.setdefault("_line_tick", st.get("_line_tick", wk))
                if E.line_stage(_st, line) is not None:
                    openlog[k] += 1
    for line in lines:
        lid = line["_meta"]["id"]
        prog = (g.state or {}).get("story", {}).get(lid)
        reached["%s=stage%s" % (lid, -1 if prog is None else prog["stage"])] += 1

print("—— 每一拍作为「下一拍」时能不能推（15 局 × 6 周）——")
for k in sorted(samples):
    print("%-18s 可推 %3d / %3d" % (k, openlog[k], samples[k]))
print("\n—— 季末各线走到的拍 ——")
for k in sorted(reached):
    print("  %-22s %d 局" % (k, reached[k]))
