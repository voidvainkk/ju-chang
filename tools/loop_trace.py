# -*- coding: utf-8 -*-
"""把一局《聚场》的每一屏都录下来，当作 loop.ts 的对账标准答案。

用法：
    python tools/loop_trace.py app/test/loop_expected.json

和 trace_dump.py 的区别：那份只比「每周结算时的状态」，这份比**每一屏**——
标题、正文、按钮文案、数值增减全都要一致。loop.py 里 4606 个汉字文案，
少一个标点都算错。

玩家是脚本化的（`_choose`）：同一屏永远点同一个位置，两边就能走出同一条路。
"""
from __future__ import annotations

import json
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "game"))

import engine as E          # noqa: E402
import loop as L            # noqa: E402

SEEDS = [0, 1, 7, 42]
GUARD = 4000                # 一局最多几屏，防死循环


def norm(v):
    """把对象变成可逐字段比对的样子：set 排序、浮点收窄、字典键排序。"""
    if isinstance(v, set):
        return sorted(norm(x) for x in v)
    if isinstance(v, float):
        return float("%.9g" % v)
    if isinstance(v, dict):
        return {str(k): norm(x) for k, x in sorted(v.items(), key=lambda kv: str(kv[0]))}
    if isinstance(v, (list, tuple)):
        return [norm(x) for x in v]
    return v


def clean(step):
    """去掉下划线开头的内部字段（里面塞着 card / slots 这些 Python 对象）。"""
    out = {}
    for k, v in step.items():
        if k.startswith("_"):
            continue
        out[k] = v
    return norm(out)


def _choose(g, step, n):
    """脚本化落子：按屏幕上的第 n 个按钮。

    两边都用同一套规则，所以只要屏幕一致，选择就一致。
    """
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
        oid = opts[n % len(opts)]["id"]
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
            # 恋爱谈一谈脚本局选第二项「只看当下」：季必须继续跑完，
            # 收场拍（前夜/撞破/办公室）才进得了基准——第一项现在是当场结季。
            oid = opts[1 % len(opts)]["id"]
        else:
            oid = opts[n % len(opts)]["id"]
        if step.get("talk"):
            g.choose_talk(oid)
        elif step.get("line"):
            g.choose_story(oid)
        else:
            g.choose_card(oid)
        return
    g.advance()


def play(seed):
    g = L.Game(seed=seed)
    screens = []
    n = 0
    while n < GUARD:
        cur = g.current()
        if cur is None:
            break
        screens.append({"i": n, "step": clean(cur), "snap": norm(g.snapshot())})
        if cur.get("type") == "end":
            break
        n += 1
        _choose(g, cur, n)
    return {
        "seed": seed,
        "screens": screens,
        "ending": (g.state or {}).get("ending"),
        "week": (g.state or {}).get("week"),
    }


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        ROOT, "app", "test", "loop_expected.json")
    runs = [play(s) for s in SEEDS]
    data = {"runs": runs}
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
    for r in runs:
        print("seed %-10s %4d 屏  结局=%s  第 %s 周"
              % (r["seed"], len(r["screens"]), r["ending"], r["week"]))
    print("写出 %s（%d bytes）" % (out, os.path.getsize(out)))


if __name__ == "__main__":
    main()
