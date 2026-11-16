# -*- coding: utf-8 -*-
"""三类修复：死门放宽（只改 gate，不动正文、不动选项）。

用户 2026-11-14：「123都要修复吧」。
每一条都对应实测证据（tools/gate_report.py：15 局 × 6 周，整季一次都不可开）：
  · 「本周已选『打工』」/「钱 < 800」——券钱进账后一季不缺钱，永远不成立
  · 私生线 7 张——键 `shiroi` 只在选项里出现，没有任何地方给它加数
  · 「任一队友关系 < 60」——起始 50、只会涨，理论上能开但实战里从没开过
  · 「曾欠队友人情」「曾冷场或翻车」——引擎从不记这两个量
另一个思路：靠「关系很差」开门的卡，改成靠「周数 + 炎上」开门；
因为队友关系是玩家养出来的，不该成为解锁条件本身。
"""
import json, io, os

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "cards")

FIX = {
    # ---- 私生线：从「私生跟踪」改为按重线进度开路（重线接管了「被一个人缠上」）
    "shiroi_tail_home": "重线进度 ≥ 1 且 周 ≥ 3",
    "shiroi_door_gift": "重线进度 ≥ 2 且 周 ≥ 3",
    "shiroi_unknown_call": "重线进度 ≥ 2 且 周 ≥ 4",
    "shiroi_photo": "重线进度 ≥ 3",
    "shiroi_front_row": "重线进度 ≥ 2 且 人气 ≥ 12",
    "shiroi_final": "重线进度 ≥ 4",
    "shir_downstairs": "重线进度 ≥ 2 且 周 ≥ 4",
    # doxx 保留「开盒风险 ≥ 55」：这条是开盒结局的前哨，不该被重线代打
    # ---- 钱：一季不缺钱了，改成「这周攒不下来」的现金流口径
    "daily_extra_shift": "钱 < 1500（手头有点紧）",
    "ota_shashu": "任一 OTA 黏性 ≥ 70 且 钱 < 1800",
    # ---- 炎上：原来的门槛在全库炎上趋近 0 时不可达，先降到能开
    "team_scapegoat": "炎上 ≥ 12",
    "ext_guilt_by_assoc": "炎上 ≥ 12",
    # ---- 靠「关系差」开门的卡：改成周 + 事件驱动
    "team_break_off": "周 ≥ 3",
    # ---- 板子：原门槛 25 在随机打法下到不了
    "ext_sns_hot_post": "人气 ≥ 12 且 板子关注度 ≥ 6",
    # ---- 「曾……」两个量引擎里没有，先改成能开的事件量
    "ext_bad_live_clip": "人气 ≥ 12 且 周 ≥ 2",
    "team_fallout": "周 ≥ 3",
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
            print("%-22s %-26s -> %s" % (c["id"], c.get("gate"), FIX[c["id"]]))
            c["gate"] = FIX[c["id"]]
            hit += 1
    if hit:
        json.dump(doc, io.open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        n += hit
print("共改 gate", n, "张")
