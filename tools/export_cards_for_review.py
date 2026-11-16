# -*- coding: utf-8 -*-
"""把全部卡导成一份给人看的清单（用户要审核）。

输出 聚场\卡库审核.md：按类型分组，每张卡给出 标题 / 触发条件 / 冷却 / 正文 / 三个选项。
只读数据，不改任何文件。
"""
import json, io, os, collections

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "cards")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "卡库审核.md")

ORDER = ["团内", "团内关系", "日常", "外部", "外部舆论", "舞台事故", "positive", "OTA互动",
         "OTA相处的瞬间", "私联恋爱", "私生", "私生跟踪", "ambient"]
NICE = {
    "positive": "好事（positive）",
    "ambient": "环境（ambient，不选，只给气氛）",
    "OTA互动": "OTA 互动（特典会现场）",
    "OTA相处的瞬间": "OTA 相处的瞬间（特典会现场）",
    "私联恋爱": "私联·恋爱",
    "私生": "私生（重线打开后）",
    "私生跟踪": "私生跟踪（重线打开后）",
    "团内": "团内",
    "团内关系": "团内关系（刷队友好感）",
    "日常": "日常（钱 / 身体 / 夜里的事）",
    "外部": "外部（外面的事）",
    "外部舆论": "外部舆论（炎上 / 板子）",
    "舞台事故": "舞台事故",
}

buckets = collections.OrderedDict((t, []) for t in ORDER)
other = []
for f in sorted(os.listdir(DATA)):
    if not f.endswith(".json"):
        continue
    doc = json.load(io.open(os.path.join(DATA, f), encoding="utf-8"))
    for c in doc.get("cards") or []:
        t = c.get("type", "?")
        (buckets[t] if t in buckets else other).append((f, c))

lines = []
lines.append("# 卡库审核清单")
lines.append("")
total = sum(len(v) for v in buckets.values()) + len(other)
lines.append("共 %d 张。按类型分组，同组内按 id 排序。" % total)
lines.append("")
lines.append("> 每张卡只写「卡面会看到的东西」：标题、触发条件、正文、每个选项。")
lines.append("> 触发条件里的数值就是这一周开始时的门槛，达不到这张卡就不会出现。")
lines.append("")

for t, items in buckets.items():
    if not items:
        continue
    lines.append("## %s（%d 张）" % (NICE.get(t, t), len(items)))
    lines.append("")
    for f, c in sorted(items, key=lambda x: x[1]["id"]):
        opts = c.get("options") or []
        lines.append("### %s　`%s`" % (c.get("title", ""), c["id"]))
        meta = []
        if c.get("gate"):
            meta.append("触发：%s" % c["gate"])
        if c.get("cooldown"):
            meta.append("冷却：%s 周" % c["cooldown"])
        if c.get("weight") not in (None, 1, 1.0):
            meta.append("权重：%s" % c["weight"])
        if meta:
            lines.append("　")
            lines.append("　" + "　｜　".join(meta))
        body = (c.get("narrative") or "").strip()
        if body:
            lines.append("　")
            lines.append("　" + body)
        if opts:
            lines.append("　")
            for o in opts:
                eff = []
                for k, v in (o.get("immediate") or {}).items():
                    eff.append("%s%+g" % (k, v) if isinstance(v, (int, float)) else "%s:%s" % (k, v))
                tail = "（%s）" % " ".join(eff) if eff else ""
                note = (o.get("note") or "").strip()
                lines.append("　- **%s**%s" % (o.get("label", ""), tail))
                if o.get("desc"):
                    lines.append("　　%s" % o["desc"])
                if note:
                    lines.append("　　%s" % note)
        else:
            eff = c.get("effect") or {}
            if eff:
                lines.append("　")
                lines.append("　（不选，直接生效：%s）" % " ".join("%s%+g" % (k, v) for k, v in eff.items()
                                                       if isinstance(v, (int, float))))
        lines.append("")

if other:
    lines.append("## 其它类型（%d 张）" % len(other))
    lines.append("")
    for f, c in other:
        lines.append("- `%s` %s（%s）" % (c["id"], c.get("title", ""), c.get("type")))

io.open(OUT, "w", encoding="utf-8").write("\n".join(lines))
print("wrote", OUT, "cards:", total)
for t, items in buckets.items():
    if items:
        print("  %-10s %d" % (t, len(items)))
