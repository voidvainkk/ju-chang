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


def tickets_of(o):
    """黏性阶梯：路人 1 张、熟客 2 张、常连 4 张，铁杆 7 张往上，
    顶级大券一个人连切十几张。消费力 ≥4 再多一张。"""
    stick = max(0.0, min(100.0, o.get("stick", 0)))
    spend = o.get("spend", 3)
    if stick >= 98:
        n = 14
    elif stick >= 95:
        n = 10
    elif stick >= 90:
        n = 7
    elif stick >= 80:
        n = 4
    elif stick >= 70:
        n = 2
    else:
        n = 1
    if spend >= 4:
        n += 1
    return max(1, n)


def bill_for(o, cheap=False):
    """一个人这一场的账单。"""
    n = tickets_of(o)
    return {"id": o["id"], "name": o["name"], "spend": o.get("spend", 3),
            "tickets": n, "yen": n * PRICE}


def weekly_bill(state, who=None):
    """整场的账单。who=None = 今天来了的所有人（引擎给的 warm 名单）。"""
    week = state.get("week", 1)
    cheap = week <= 2
    pool = who if who is not None else [o for o in state["ota"] if o.get("stick", 0) >= 30]
    rows = [bill_for(o, cheap) for o in pool]
    rows = [r for r in rows if r["tickets"] > 0]
    rows.sort(key=lambda r: (-r["yen"], r["name"]))
    total_y = sum(r["yen"] for r in rows)
    # 没来的人：在场但今天没到
    came = {r["id"] for r in rows}
    absent = [o["name"] for o in state["ota"] if o["id"] not in came]
    return {"rows": rows, "tickets": sum(r["tickets"] for r in rows), "yen": total_y,
            "absent": absent, "price": PRICE}
