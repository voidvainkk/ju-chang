# -*- coding: utf-8 -*-
"""结局可达性复查：
A) 静态——6 个提前结局的触发旗标在数据/引擎里的写入者；
B) 实证——扫 种子×分支偏移×谈一谈/空心动机/offer 选择，统计实际跑出的结局。
用法：python tools/audit_reachability.py [轮数] [输出json]
"""
from __future__ import annotations

import io
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "game"))

import engine as E          # noqa: E402
import loop as L            # noqa: E402

GUARD = 4000


def pick(g, step, off, rtalk_idx, kind_idx):
    t = step.get("type")
    if t == "name":
        if step.get("stage") == "style":
            g.pick_style(step["styles"][0]["id"])
        else:
            g.set_name(step["candidates"][0])
        return
    if t == "stance":
        g.choose_stance(step["stances"][0]["id"])
        return
    if t == "end":
        return
    if t in ("text", "live", "receipt", "panel", "bill"):
        g.advance()
        return
    if t == "choice":
        kind = step.get("kind")
        opts = step.get("options") or []
        if not opts:
            g.advance()
            return
        oid = opts[(n_off(off)) % len(opts)]["id"]
        if kind == "act":
            g.choose_act(oid)
        elif kind == "leave":
            g.choose_leave(oid)
        elif kind == "empty":
            g.choose_empty(oid)
        elif kind == "offer":
            g.choose_offer(oid)
        else:
            g.advance()
        return
    if t in ("card", "chat"):
        opts = step.get("options") or []
        if not opts:
            g.advance()
            return
        if step.get("rtalk"):
            oid = opts[rtalk_idx % len(opts)]["id"]
        else:
            oid = opts[(n_off(off)) % len(opts)]["id"]
        if step.get("talk"):
            g.choose_talk(oid)
        elif step.get("line"):
            g.choose_story(oid)
        else:
            g.choose_card(oid)
        return
    g.advance()


_N = {"n": 0}


def n_off(off):
    _N["n"] += 1
    return _N["n"] + off


def play(seed, off, rtalk_idx):
    _N["n"] = 0
    g = L.Game(seed=seed)
    while _N["n"] < GUARD:
        cur = g.current()
        if cur is None or cur.get("type") == "end":
            break
        _N["n"] += 1
        pick(g, cur, off, rtalk_idx, 0)
    return (g.state or {}).get("ending")


def static_check():
    import io
    world = json.load(io.open(os.path.join(ROOT, "data", "endings.json"), encoding="utf-8"))
    files = []
    for sub in ("storylines", "cards"):
        d = os.path.join(ROOT, "data", sub)
        for fn in os.listdir(d):
            if fn.endswith(".json"):
                files.append(os.path.join(d, fn))
    blobs = {}
    for f in files:
        blobs[f] = io.open(f, encoding="utf-8").read()
    out = []
    for e in world["early"]:
        flag = e["trigger"].get("flag")
        where = []
        for f, txt in blobs.items():
            if '"%s"' % flag in txt:
                where.append(os.path.relpath(f, ROOT))
        out.append({"name": e["name"], "flag": flag, "writers": sorted(set(where))})
    return out


def main():
    rounds = int(sys.argv[1]) if len(sys.argv) > 1 else 120
    out_path = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, "audit_reach.json")
    res = {"static": static_check(), "sweep": {}}
    tally = {}
    t0 = time.time()
    combos = 0
    for off in range(3):
        for rtalk in range(2):
            for i in range(rounds):
                seed = i * 7 + off * 101
                name = play(seed, off, rtalk)
                tally[name or "(无)"] = tally.get(name or "(无)", 0) + 1
                combos += 1
    res["sweep"] = {"combos": combos, "seconds": round(time.time() - t0, 1), "tally": tally}
    io.open(out_path, "w", encoding="utf-8").write(json.dumps(res, ensure_ascii=False, indent=1))
    print(json.dumps(res["sweep"], ensure_ascii=False, indent=1))
    print("static:")
    for s in res["static"]:
        print(" ", s["name"], s["flag"], "<-", s["writers"] or "!!无写入者!!")


if __name__ == "__main__":
    main()
