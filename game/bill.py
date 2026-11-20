# -*- coding: utf-8 -*-
"""特典会一周一张账单：谁买了几张、谁没来。

一张券 **80 元**（2026-11-14 用户定，全团统一价）。
    tickets 按黏性阶梯（2026-11-19 用户定）：
    <70→1；70–79→2；80–89→4；90–94→7；95–97→10；98+→14；消费力 ≥4 再 +1。
  开局一整场个位数；黏性 95+ 的铁杆能一个人连切十几张。
  消费力越强的人买的张数越多——圈里说「这个人出手大」说的是他买得多，
  不是他买了一张更贵的券。所以表里只记每一场谁买了几张。
  钱 = 张数 × 80，不再乘人气系数：人气只决定今天谁来、来几个。
"""
from __future__ import annotations

PRICE = 80          # 特典券统一 80 元一张（2026-11-14 用户定）


def big_split(o):
    """这个人是大券型、小券型，还是一半一半。"""
    if o.get("spend", 3) >= 4 or o.get("archetype") == "重力系":
        return "big"
    if o.get("spend", 3) <= 2:
        return "small"
    return "mixed"


def _stage_of(state):
    """轻量舞台分：与 engine.stage_score 同口径（bill 不能反过来 import engine）。"""
    rel = [float(state.get(k) or 0) for k in ("relation_A", "relation_B", "relation_C")]
    relavg = sum(rel) / len(rel) if rel else 0.0
    return (0.32 * float(state.get("dance") or 0) + 0.28 * float(state.get("sing") or 0)
            + 0.22 * float(state.get("mc") or 0) + 0.18 * relavg)


def tickets_of(o, stage=None):
    """黏性阶梯 × 出手 × 舞台：小券一两张，顶级大券能一个人连切二十几张。

    黏性阶梯：<70→1；70→2；80→4；90→7；95→10；98→14。
    出手（大券小券）：消费力 ≤2 打 6 折，=3 全额，≥4 加 6 成。
    舞台：场子越好看买得越多——<55 全额，55→1.1，70→1.3，85→1.6。"""
    stick = max(0.0, min(100.0, o.get("stick", 0)))
    spend = o.get("spend", 3)
    if stick >= 98:
        base = 14
    elif stick >= 95:
        base = 10
    elif stick >= 90:
        base = 7
    elif stick >= 80:
        base = 4
    elif stick >= 70:
        base = 2
    else:
        base = 1
    sm = 0.6 if spend <= 2 else (1.6 if spend >= 4 else 1.0)
    st = 0.0 if stage is None else float(stage)
    tm = 1.6 if st >= 85 else (1.3 if st >= 70 else (1.1 if st >= 55 else 1.0))
    return max(1, int(base * sm * tm + 0.5))


def bill_for(o, stage=None, cheap=False):
    """一个人这一场的账单。stage = 本场开演前的舞台分。"""
    n = tickets_of(o, stage)
    return {"id": o["id"], "name": o["name"], "spend": o.get("spend", 3),
            "tickets": n, "yen": n * PRICE}


def weekly_bill(state, who=None):
    """整场的账单。who=None = 今天来了的所有人（引擎给的 warm 名单）。"""
    week = state.get("week", 1)
    cheap = week <= 2
    pool = who if who is not None else [o for o in state["ota"] if o.get("stick", 0) >= 30]
    stage = _stage_of(state)
    rows = [bill_for(o, stage, cheap) for o in pool]
    rows = [r for r in rows if r["tickets"] > 0]
    rows.sort(key=lambda r: (-r["yen"], r["name"]))
    total_y = sum(r["yen"] for r in rows)
    # 没来的人：在场但今天没到
    came = {r["id"] for r in rows}
    absent = [o["name"] for o in state["ota"] if o["id"] not in came]
    return {"rows": rows, "tickets": sum(r["tickets"] for r in rows), "yen": total_y,
            "absent": absent, "price": PRICE}
