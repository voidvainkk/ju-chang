# -*- coding: utf-8 -*-
"""私联线改为线性剧情后，清理 private.json 里被吸收进 storyline 的 7 张随机私联卡，
保留『那个总在搬器材的人』这类不涉及私联 OTA 的暖卡；更新 _meta 指向 storyline。"""
import json, os

P = r"C:\Users\kk\Documents\deepseek-harness\default-workspace\聚场\data\cards\private.json"
d = json.load(open(P, encoding="utf-8"))

absorbed = {"priv_late_chat", "priv_meetup", "priv_gift", "priv_borrow",
            "priv_ambiguous", "priv_jealous", "priv_shakedown"}
before = len(d["cards"])
d["cards"] = [c for c in d["cards"] if c["id"] not in absorbed]
after = len(d["cards"])
d["_meta"]["category"] = "私下的人情"
d["_meta"]["design_note"] = (
    "私联主线已改为线性剧情（见 data/storylines/storyline_shiren.json），原来的随机私联卡内容"
    "（深夜聊天/面馆/礼物/借钱/算什么呢/撞见另一个/截图威胁）已吸收为该 storyline 的剧情变体，故此处移除，避免重复。"
    "这里只保留不涉及私联 OTA 的私下暖卡：把偶像当『普通同事』对待的那一点点人情。"
)
JSON_DUMP_KW = dict(ensure_ascii=False, indent=2)
with open(P, "w", encoding="utf-8") as f:
    json.dump(d, f, **JSON_DUMP_KW)
    f.write("\n")
print("private.json", before, "->", after, "kept:", [c["id"] for c in d["cards"]])
