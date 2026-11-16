# -*- coding: utf-8 -*-
"""重跑 gate 报告：15 局界面流程，逐局每周记录「此刻 gate 通过的有几张卡」。

只读。比起 v1 多三样统计：
  · 每局每周可开卡数（看「刷出来的量」够不够）
  · 每张一个卡在一季里可开的占比
  · 整季一次不开的卡（要看是真死还是只是 15 局没抽到）
"""
import sys, os, collections

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "game"))
import engine as E, loop as L

w = E.load_world()
cards = [c for c in w["cards"] if c.get("options")]

SEASONS = 15
open_days = collections.Counter()
per_week = collections.defaultdict(list)
peak = collections.defaultdict(list)


def run(seed, chooser):
    g = L.Game(seed=seed)
    last_week = 0
    while True:
        cur = g.current()
        if cur is None:
            break
        t = cur.get("type")
        if t == "name":
            if cur.get("stage") == "style":
                g.pick_style(cur["styles"][0]["id"])
            else:
                g.set_name(cur["candidates"][0])
        elif t == "choice":
            if cur.get("kind") == "intro":
                g.choose_intro(cur["options"][0]["id"])
            else:
                g.choose_act(chooser.pick_act(g.state, cur["options"]))
        elif t == "card":
            opts = cur["options"]
            o = chooser.pick(objs=opts) if hasattr(chooser, "pick") else 0
            oid = opts[o if isinstance(o, int) else 0]["id"]
            g.choose_talk(oid) if cur.get("talk") else g.choose_card(oid)
        elif t == "end":
            break
        else:
            g.advance()
        st = g.state or {}
        wk = min(6, int(st.get("week", 1) or 1))
        if wk != last_week:
            last_week = wk
            n_ok = 0
            for c in cards:
                try:
                    ok = E.eval_gate(st, c.get("gate"))
                except Exception:
                    ok = False
                if ok:
                    n_ok += 1
                    open_days[c["id"]] += 1
            per_week[wk].append(n_ok)
            peak[wk].append({k: round(st.get(k, 0) or 0, 1) for k in
                             ("enjou", "banzi", "kaibox", "shiroi", "heat", "zhong", "fame", "psych", "psyche")})


class Random3(object):
    def pick_act(self, s, opts):
        return 0

    def pick(self, objs):
        return 0


for seed in range(SEASONS):
    run(seed, Random3())

total = SEASONS * 6
print("卡（有选项）:", len(cards), " 局数:", SEASONS)
print("\n—— 每局每周「此刻能开」的卡数（平均 / 最少 / 最多）——")
for wk in range(1, 7):
    xs = per_week[wk]
    if not xs:
        continue
    print("  周%d  %5.1f  /  %3d  /  %3d" % (wk, sum(xs) / len(xs), min(xs), max(xs)))

print("\n—— 关键量的走势（15 局平均）——")
for wk in range(1, 7):
    xs = peak[wk]
    if not xs:
        continue
    keys = ("enjou", "banzi", "kaibox", "shiroi", "heat", "zhong", "psyche")
    print("  周%d  " % wk + "  ".join(
        "%s=%.1f" % (k, sum(x.get(k, 0) or 0 for x in xs) / len(xs)) for k in keys))

rows = []
for c in cards:
    rows.append((open_days.get(c["id"], 0), c.get("type"), c.get("title"), c.get("gate")))
rows.sort()
print("\n—— 可开占比最低的 20 张 ——")
for n, typ, title, gate in rows[:20]:
    print("%3d/%d  %5.0f%%  %-8s %-22s %s" % (n, total, 100.0 * n / total, typ, str(title)[:20], gate))
print("\n整季一次不开:", sum(1 for r in rows if r[0] == 0))
for n, typ, title, gate in rows:
    if n == 0:
        print("   ", typ, title, "|", gate)
