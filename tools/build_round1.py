# -*- coding: utf-8 -*-
"""One-shot builder: 删 #19/#60、加 6 张新卡、生成私联线性剧情线 storyline_shiren.json。
非游戏代码，属于内容构建脚本，保留以便复现。"""
import json, os

BASE = r"C:\Users\kk\Documents\deepseek-harness\default-workspace\聚场\data"
CARDS = os.path.join(BASE, "cards")


def load(fn):
    with open(os.path.join(CARDS, fn), encoding="utf-8") as f:
        return json.load(f)


def save(fn, d):
    with open(os.path.join(CARDS, fn), "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)
        f.write("\n")


# ---------- 1. 删 #19 team_defect / #60 pos_mama_fan ----------
def drop(fn, cid):
    d = load(fn)
    b = len(d["cards"])
    d["cards"] = [c for c in d["cards"] if c["id"] != cid]
    save(fn, d)
    print("DROP", fn, cid, b, "->", len(d["cards"]))


drop("team.json", "team_defect")
drop("positive.json", "pos_mama_fan")


# ---------- 2. 六张新卡 ----------
new_ota = {
    "id": "ota_remembered",
    "type": "OTA相处的瞬间",
    "title": "记得我说过的话",
    "gate": "任一 OTA 黏性 ≥ 60",
    "weight": 1.0,
    "cooldown": 5,
    "casting": [{"slot": "listener", "select": {"min_stickiness": 60}, "allow_hatch": True}],
    "narrative": "我随口跟{{listener}}提过一次，说我小时候住的那条巷子口有棵老槐树，夏天风一吹，落一地的花。今天散场，我桌上放着一个小玻璃瓶，里头是晒干的槐花，压着张纸条：『你说的那棵树。』我盯着那瓶子，忽然鼻子发酸——原来有人把我随口说的话，当成一件要记一辈子的事。",
    "options": [
        {
            "id": "keep_and_remember_back",
            "label": "好好收着，也开始记一件 TA 的事",
            "desc": "被人这样记住，是会想还回去的",
            "immediate": {"@listener": 8, "psyche": 5, "stamina": -4},
            "delayed": [
                {"when": "条件", "condition": "开盒风险 ≥ 55", "effect": {"kaibox": 6},
                 "note": "你把 TA 也记进了心里，这条线就越缠越紧，收不回来了"}
            ],
        },
        {
            "id": "deflect",
            "label": "笑说『你怎么记这个』，把话岔开",
            "desc": "我怕被人这样记住，好像欠下了什么",
            "immediate": {"@listener": -5, "psyche": -3},
            "delayed": [],
        },
        {
            "id": "polite_distance",
            "label": "当面道谢，但说『别为我花这些心思』",
            "desc": "划条线，自己好受，凉了对方",
            "immediate": {"@listener": -2, "psyche": 3, "ota_all": -2},
            "delayed": [],
        },
    ],
}

new_first_leave = {
    "id": "ext_first_leave",
    "type": "外部舆论",
    "title": "第一个退坑的人",
    "gate": "人气 ≥ 25 且 周 ≥ 3",
    "weight": 1.0,
    "cooldown": 4,
    "narrative": "板子上刷到一条长帖，是那个从我第一次上台就一直在的 ID 发的：『追不动了，谢谢这段时间。』底下有人问怎么了，没回。我认得那个头像，从第一场就坐在同一个位置，喊 call 喊得比谁都响。原来所谓的单推，也是会走的。我盯着屏幕，第一次觉得这行当里，有些告别是悄悄发生的，连句再见都不给你。",
    "options": [
        {
            "id": "dm_thanks",
            "label": "去私信问一句，哪怕只是说声谢谢",
            "desc": "就算留不住，也想让 TA 知道被看见了",
            "immediate": {"psyche": 5, "stamina": -3},
            "delayed": [
                {"when": "条件", "condition": "心理 < 30", "effect": {"psyche": -4},
                 "note": "TA 回了一句『谢谢你还记得我』，然后再没上线——你发现有些人，是留不住的"}
            ],
        },
        {
            "id": "pretend_not_seen",
            "label": "装作没看见，照常排练",
            "desc": "这行当不能为每一个离开的人停下",
            "immediate": {"psyche": -4, "ota_all": -1},
            "delayed": [],
        },
        {
            "id": "public_thanks",
            "label": "在评论区公开回一句谢谢，让留下的也看见",
            "desc": "把这份情摆上台面",
            "immediate": {"fame": 3, "psyche": 2, "banzi": 4},
            "delayed": [],
        },
    ],
}

new_lulu_cry = {
    "id": "team_lulu_cry",
    "type": "团内关系",
    "title": "撞见露露一个人在后台哭",
    "gate": "露露关系 ≥ 40 且 周 ≥ 3",
    "weight": 1.0,
    "cooldown": 5,
    "narrative": "回后台拿东西，撞见露露一个人蹲在器材箱后面，肩膀一抽一抽的。她听见动静猛地抬头，眼睛红得像被人打了一拳，第一反应是把脸别过去：『你什么都没看见。』那个平时在台上抢我镜头、说话带刺的人，原来也会这样。我站在门口，进也不是，退也不是。",
    "options": [
        {
            "id": "sit_and_tissue",
            "label": "蹲下来，什么也不问，递张纸巾",
            "desc": "有时候人要的不是办法，是有人陪着",
            "immediate": {"relation_B": 8, "psyche": 3, "stamina": -2},
            "delayed": [
                {"when": "条件", "condition": "露露关系 ≥ 70", "effect": {"relation_all": 4},
                 "note": "后来排练有人挑你刺，是露露替你挡了一句"}
            ],
        },
        {
            "id": "i_saw_nothing",
            "label": "说『我什么都没看见』，转身走",
            "desc": "守住她的面子，也关上了那扇门",
            "immediate": {"relation_B": -3, "psyche": -2},
            "delayed": [],
        },
        {
            "id": "ask_and_help",
            "label": "问她怎么了，说『我们可以一起想办法』",
            "desc": "靠近了，可她的难处也许会变成你的",
            "immediate": {"relation_B": 3, "psyche": -5, "stamina": -4},
            "delayed": [
                {"when": "条件", "condition": "心理 < 35", "effect": {"psyche": -4},
                 "note": "她的难处你扛了一半，才发现自己也没那么多余力"}
            ],
        },
    ],
}

new_cold_stage = {
    "id": "pos_cold_stage_truth",
    "type": "舞台事故",
    "title": "台上冷场，我临场说了句真心话",
    "gate": "周 ≥ 2",
    "weight": 1.0,
    "cooldown": 5,
    "narrative": "这首歌的间奏本来要放段预录，设备突然哑了，台上台下一起僵住。我脑子一空，抓着话筒说了句没排练过的话：『其实我今天特别紧张，怕你们看出来。』台下静了一秒，然后有人笑了，有人喊『看不出来！』。那一秒过去，场子忽然就活了。",
    "options": [
        {
            "id": "finish_truth",
            "label": "顺着把真心话说完，把冷场讲成段子",
            "desc": "把心掏出来给一屋子人，累，但真",
            "immediate": {"stage": 6, "fame": 4, "stamina": -4, "psyche": -2},
            "delayed": [],
        },
        {
            "id": "cue_next",
            "label": "赶紧 cue 下一首，把场子拉回流程",
            "desc": "稳住了，可那个瞬间没接住",
            "immediate": {"stage": 2, "psyche": 1, "relation_all": -2},
            "delayed": [],
        },
        {
            "id": "crowd_sing",
            "label": "cue 全场一起清唱副歌",
            "desc": "让众人接住，代价是再来一遍体力",
            "immediate": {"stage": 4, "ota_all": 5, "stamina": -6},
            "delayed": [],
        },
    ],
}

new_shiroi_downstairs = {
    "id": "shir_downstairs",
    "type": "私生跟踪",
    "title": "私生跟到我家楼下",
    "gate": "私生跟踪 ≥ 25",
    "weight": 1.0,
    "cooldown": 5,
    "narrative": "回家路上总觉得身后有脚步声。我拐进便利店，隔着玻璃看见一个人也停下来，站在路灯底下等着。等我再出门，TA 不远不近地跟着，一直跟到楼下。我站在单元门口掏钥匙，手抖得插不进锁孔——我第一次这么清楚地知道，有人在研究我每天几点回家。",
    "options": [
        {
            "id": "call_police",
            "label": "报警",
            "desc": "事情公开了，安全了，也被挂出去",
            "immediate": {"shiroi": -8, "enjou": 4, "banzi": 5},
            "delayed": [
                {"when": "条件", "condition": "私生跟踪 ≥ 40", "effect": {"shiroi": -6},
                 "note": "对方收敛了一阵，但你的住址方向已经在某些群里传开了"}
            ],
        },
        {
            "id": "move_house",
            "label": "连夜找房子搬走",
            "desc": "用钱和折腾换一夜安稳",
            "immediate": {"money": -800, "shiroi": -12, "psyche": -5, "stamina": -6},
            "delayed": [],
        },
        {
            "id": "confront",
            "label": "站住，转身当面跟 TA 摊牌",
            "desc": "你以为的勇敢，也可能被当成『TA 记得我』",
            "immediate": {"psyche": -4, "shiroi": 6, "kaibox": 5},
            "delayed": [
                {"when": "条件", "condition": "心理 < 25", "effect": {"psyche": -8},
                 "note": "TA 被你说哭了，第二天却发帖说『她跟我说话了』——你反而给了 TA 一个纪念日"}
            ],
        },
    ],
}

for fn, card in [
    ("ota.json", new_ota),
    ("external.json", new_first_leave),
    ("team.json", new_lulu_cry),
    ("positive.json", new_cold_stage),
    ("shiroi.json", new_shiroi_downstairs),
]:
    d = load(fn)
    if any(c["id"] == card["id"] for c in d["cards"]):
        print("SKIP existing", card["id"])
        continue
    d["cards"].append(card)
    save(fn, d)
    print("ADD", fn, card["id"], "-> now", len(d["cards"]))

print("cards step done")
