# -*- coding: utf-8 -*-
"""第二轮死门修复（2026-11-14），按真实 id 改。

  · daily_work_conflict「排班和加练撞了」：只认「本周已选打工」，随机打法很少先打工 →
    放宽成「每周都可能撞」（打工 / 钱紧 都算）。
  · daily_rent_due「房东的消息」：只认钱 < 1200，一季钱一直够 → 改成「房租那周」。
"""
import json, io, os

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "cards")

FIX = {
    "daily_work_conflict": "本周已选打工 或 钱 < 800（手头紧）",
    "daily_rent_due": "周 ≥ 2 且 钱 < 2400（房租那周）",
}

n = 0
for name in sorted(os.listdir(BASE)):
    if not name.endswith(".json"):
        continue
    p = os.path.join(BASE, name)
    doc = json.load(io.open(p, encoding="utf-8"))
    hit = 0
    for c in doc.get("cards") or []:
        if c["id"] in FIX:
            print("%-22s %-34s -> %s" % (c["id"], c.get("gate"), FIX[c["id"]]))
            c["gate"] = FIX[c["id"]]
            hit += 1
    if hit:
        json.dump(doc, io.open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        n += hit
print("共改", n, "张")
