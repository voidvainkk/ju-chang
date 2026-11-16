# -*- coding: utf-8 -*-
"""补「引擎从没记过」的两个门（用户 2026-11-14 指出这两张卡整季抽不到）。

· 翻车那一下被拍下来了   ← 曾冷场或翻车   = Live 结算里数到的 blew_it ≥ 1
· 锅甩到我头上           ← 曾欠队友人情   = 我在团队卡里让队友背过锅（owe_team ≥ 1）

顺带给「甩锅给别人」的选项打上 owe_team 标记，这个量才会有来源：
  team_scapegoat / push_B   顺着暗示把话头引向露露
  team_money_split / 多占一份
"""
import json, io, os

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "cards")

FIX_GATE = {
    "ext_bad_live_clip": "曾冷场或翻车 且 人气 ≥ 12",
    "team_fallout": "曾欠队友人情 且 周 ≥ 2",
}

# 哪些卡的哪些选项算「把队友推出去顶罪」
OWE = {
    "team_scapegoat": ["push_B"],
}

n = 0
for name in sorted(os.listdir(BASE)):
    if not name.endswith(".json"):
        continue
    p = os.path.join(BASE, name)
    doc = json.load(io.open(p, encoding="utf-8"))
    hit = 0
    for c in doc.get("cards") or []:
        if c["id"] in FIX_GATE:
            print("gate  %-20s %s -> %s" % (c["id"], c.get("gate"), FIX_GATE[c["id"]]))
            c["gate"] = FIX_GATE[c["id"]]
            hit += 1
        for oid in OWE.get(c["id"], []):
            for o in c.get("options") or []:
                if o["id"] == oid:
                    o.setdefault("flags", [])
                    if "owe_team" not in o["flags"]:
                        o["flags"].append("owe_team")
                        print("flag  %-20s / %s += owe_team" % (c["id"], oid))
                        hit += 1
    if hit:
        json.dump(doc, io.open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        n += hit
print("共改", n, "处")
