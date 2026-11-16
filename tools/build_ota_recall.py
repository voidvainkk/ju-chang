# -*- coding: utf-8 -*-
"""生成 OTA 记忆回考的「两拍」卡组（2026-11-14）。

背景：个人线砍掉后，21 条回考线索没有了「她第一次说出细节」的入口。
本脚本把回考拆成两拍，各自独立随机刷出：

  第一拍「她说」 card id = ota_say_<clue>   —— 她在特典会上随口说出一个三选一的细节
                                            → 真值在这一刻锁定进本局
                                            → 三个反应（认真接话 / 随意应一声 / 岔开话题）
                                            → 三个都会被考，差别只在「她问的时候期望多高」
  第二拍「她问」 card id = ota_ask_<clue>   —— 隔了 ≥2 场之后她用一句自然问法再提
                                            → 玩家三选一答，对加分、错扣分
                                            → 反应按她的原型写（线 in ota_memory.json 的 react_good/react_bad）

设计要点（用户 m01234/m01235 定）：
  · 不管第一拍选什么，真值都锁定、都会考 —— 没认真听不是安全选项。
  · 认真接话 → 她以为你记住了，问的时候期望更高，答错扣得更狠。
  · 岔开话题 → 她当时不吭声了，答错时她的反应更凉（「我那天说的时候你就没听」）。
  · 重型线索（第一次来 / 为什么一直来 / 上个团怎么散的）不参与随机，
    要等黏性 ≥ 70 且认识 ≥ 3 周才开口。

输出：data/cards/ota_recall.json（与 ota.json 并列，独立文件便于整体开关）
非游戏代码，内容构建脚本，改文案改这里再跑，别手改 json。
"""
import json, os

BASE = r"C:\Users\kk\Documents\deepseek-harness\default-workspace\聚场\data"
MEM_PATH = os.path.join(BASE, "ota_memory.json")
OUT = os.path.join(BASE, "cards", "ota_recall.json")

MEM = json.load(open(MEM_PATH, encoding="utf-8"))
CLUES = {c["key"]: c for c in MEM["clues"]}
from _ota_memory_askheavy import ASK_HEAVY
ARCH = MEM["_meta"]["archetypes"]          # gravity/bold/mom/angler/shy/nerd/joker -> 中文名
POINTS = MEM["_meta"]["points"]            # '+2/-3' 等字符串，仅作文档用

# 重型线索必须等关系深了才说（不参与常驻随机）
HEAVY_LOCK_GATE = "（任一 OTA 黏性 ≥ 70 且 认识周数 ≥ 3）"

# ---- 第一拍三个反应 ----
# mode: warm = 认真接话（她以为你记住了，答错更痛）
#       flat = 随意应一声（正常）
#       cold = 岔开话题（她当场收回去，答错时更凉）
SAY_OPTIONS = [
    {
        "id": "say_warm",
        "label": "顺着她的话往下问一句",
        "desc": "「那你怎么没买？」把这句话接住了",
        "mode": "warm",
        "immediate": {"@speaker": 5, "psyche": -1, "stamina": -1},
        "delayed": [],
        "note": "她说了好多，说到自己笑起来。后面还排着人，我一点都没催",
    },
    {
        "id": "say_flat",
        "label": "点点头，说一句「哦，是吗」",
        "desc": "听见了，但没往心里去",
        "mode": "flat",
        "immediate": {"@speaker": 1, "stamina": -1},
        "delayed": [],
        "note": "她说完自己又补了一句「也没什么」，就没再说了",
    },
    {
        "id": "say_cold",
        "label": "把话题拐回今天的营业",
        "desc": "「今天最后一首你们跳得真好」",
        "mode": "cold",
        "immediate": {"@speaker": -3, "fame": 2},
        # 用户 m01384 定：岔开话题当场就要疼，而且这条线索本轮作废。
        # 作废标记走 rq_drop（和 rq_lock / rq_pick 同一套命名），运行时看到就
        # 把这条线索从本局回考池里删掉 —— 她不会再问了，我也永远不知道答案。
        "delayed": [{
            "when": "本场结束",
            "effect": {"@speaker": -4},
            "note": "她收拾券的时候没再说话，走的时候也没回头。这件事，我大概是不会知道了。",
        }],
        "note": "她愣了一下，顺着我的话说了句「谢谢」，眼睛往旁边偏了偏",
        "rq_drop": True,
    },
]

# ---- 第二拍：岔开过的话题，答错时额外的一刀 ----
COLD_EXTRA = "『……我那天说的时候，你好像就在看后面。』"


# ---- 每张卡的环境收尾（避免 21 张共用一个模板，玩到第三张就露馅）----
# 只在「她说」这一拍用；「她问」那拍的收尾看 ASK_TAILS
SAY_TAILS = {
    "fruit_craving": "说完自己笑了一下，像是才想起来我在听。",
    "food_hate": "她把这句话说完，才抬起眼看我。",
    "daily_drink": "说这话的时候她手里还捏着个空杯。",
    "pet_dream": "她说得很轻，像在讲一个还没敢实现的愿望。",
    "weather_hate": "外面的天阴着，她往里看了一眼。",
    "loop_song": "她说起这个的时候，手指在桌沿上敲了两下。",
    "commute": "她说这段的时候没什么表情，像是在说别人的事。",
    "snack": "她从包里摸出一小包，又塞了回去。",
    "phone_app": "她的手机在桌上震了一下，她没看。",
    "work_file": "她说起这个，语气一下子变得很平。",
    "off_work": "她说完看了看表，好像该走了，可还坐着。",
    "pet_type": "她说得笃定，像早想过很多遍。",
    "dream_place": "说到这儿她停了一下，没再说下去。",
    "family_pressure": "她说的时候声音小了，往旁边看了一眼。",
    "money_habit": "她说到这里自己先笑了，有点不好意思。",
    "commuter_route": "她给我比划了一下换乘的方向，手上还拎着东西。",
    "first_visit": "她说起第一次的时候，语速慢了下来。",
    "spare_thing": "她说得很随意，可我看她在那儿放了好一会儿。",
    "alone_reason": "她说完抿了一下嘴，像说多了。",
    "what_keeps": "她说完就不看我了，去看后面的排队。",
    "prev_group": "她说这个的时候很平静，平静得不太对。",
}

ASK_TAILS = {
    "fruit_craving": "她还拿手比了一下大小。",
    "food_hate": "她把筷子放下，等我说话。",
    "daily_drink": "她看着我，是真的在等我答。",
    "pet_dream": "她大概自己也没想到会问出口。",
    "weather_hate": "她说这话的时候，肩膀缩了一下。",
    "loop_song": "她问得很随口，眼睛却没离开我。",
    "commute": "她大概只是没话找话。",
    "snack": "她把手里的东西举起来晃了晃。",
    "phone_app": "她说完自己也觉得有点好笑。",
    "work_file": "她说完就后悔了，往后靠了靠。",
    "off_work": "她问出口，好像自己也不确定该不该问。",
    "pet_type": "她抬着下巴看我，一副等着被说中的样子。",
    "dream_place": "她问得很轻，像是随口一提。",
    "family_pressure": "她的笑还挂在脸上，眼睛没笑。",
    "money_habit": "她问这个的时候，语气反而很认真。",
    "commuter_route": "她说完就低头去翻包里的东西。",
    "first_visit": "她问的时候没看我，看的是桌上的券。",
    "spare_thing": "她说得很轻，好像不指望我记得。",
    "alone_reason": "她问完就笑了，笑得有点勉强。",
    "what_keeps": "她抬眼看我，这次没躲。",
    "prev_group": "她问得很快，快得像不想听答案。",
}


def say_card(key, c):
    """第一拍：她说出细节，三个反应都锁定真值。"""
    gate = "任一 OTA 黏性 ≥ 45"
    if c["level"] == "heavy":
        gate = "任一 OTA 黏性 ≥ 70 且 认识周数 ≥ 3"
    opts = []
    for o in SAY_OPTIONS:
        oo = dict(o)
        oo["rq_lock"] = {"clue": key, "slot": "speaker"}
        opts.append(oo)
    # 重型线索：真值在上场前还没定，由玩家运行时抽定后取 say_full[该值] 的整句；
    # 文案里先用第一句做占位，并标记 say_mode 让运行时知道要换。
    say_text = c["say"]
    say_mode = "template"
    if c.get("say_full"):
        first_key = next(iter(c["say_full"]))
        say_text = c["say_full"][first_key]
        say_mode = "full"
    return {
        "id": "ota_say_%s" % key,
        "type": "OTA记忆",
        "title": "她随口说的一件事",
        "gate": gate,
        "weight": 1.0 if c["level"] != "heavy" else 0.6,
        "cooldown": 6,
        "narrative": (
            "{{speaker}}在列里说到一半忽然想起什么：%s%s"
        ) % (say_text, SAY_TAILS[key]),
        "casting": [{"slot": "speaker", "select": {"min_stickiness": 45 if c["level"] != "heavy" else 70},
                     "allow_hatch": True}],
        "options": opts,
        "_meta": {"rq_stage": "say", "clue": key, "say_mode": say_mode,
                  "say_full": c.get("say_full")},
    }


def ask_card(key, c):
    """第二拍：她用一句自然问法再提，三选一。"""
    gate = "任一 OTA 黏性 ≥ 45"
    if c["level"] == "heavy":
        gate = "任一 OTA 黏性 ≥ 70 且 认识周数 ≥ 3"
    # 三个选项 = 三个同类值；顺序固定为 set 的顺序，运行时洗牌
    opts = []
    for i, v in enumerate(c["set"]):
        is_true = (i == 0)
        im = dict(c["points"]["good" if is_true else "bad"])
        # points 里是 {'ota_all': 2} 这类，改成投给本人
        im = {("@speaker" if k == "ota_all" else k): val for k, val in im.items()}
        opts.append({
            "id": "pick_%d" % i,
            "label": v,
            "desc": "",
            "immediate": im,
            "delayed": [],
            "rq_pick": {"clue": key, "slot": "speaker", "choice": "true" if is_true else "false"},
            "note": "",
        })
    # 问法：重型线索用专门指向「我」的问法（ASK_HEAVY），其余用 ask[0]
    ask_text = ASK_HEAVY.get(key, c["ask"][0]) if c["level"] == "heavy" else c["ask"][0]
    return {
        "id": "ota_ask_%s" % key,
        "type": "OTA记忆",
        "title": "她问起那件事",
        "gate": gate,
        "weight": 1.0 if c["level"] != "heavy" else 0.6,
        "cooldown": 8,
        "narrative": (
            "{{speaker}}排到桌前，说了几句闲的，忽然抬头问：%s%s"
        ) % (ask_text, ASK_TAILS[key]),
        "casting": [{"slot": "speaker", "select": {"min_stickiness": 45 if c["level"] != "heavy" else 70},
                     "allow_hatch": True}],
        "options": opts,
        "_meta": {"rq_stage": "ask", "clue": key,
                  "react_good": c["react_good"], "react_bad": c["react_bad"],
                  "cold_extra": COLD_EXTRA},
    }


cards = []
_missing = [k for k in CLUES if k not in SAY_TAILS or k not in ASK_TAILS]
assert not _missing, ("缺收尾台词", _missing)
for key, c in CLUES.items():
    cards.append(say_card(key, c))
    cards.append(ask_card(key, c))

doc = {
    "_meta": {
        "category": "OTA记忆回考",
        "design_note": (
            "两拍制（2026-11-14 定）：第一拍『她说』——她随口说出一个三选一的细节，"
            "真值在这一刻锁定进本局；三个反应会全部被考，差别只在第二拍她的期望与失望程度。"
            "第二拍『她问』——隔 ≥2 场之后她用一句自然问法再提，玩家三选一，对加分、错扣分。"
            "没有档案本、没有『记得吗』式的提示，也没有安全选项。"
            "岔开话题 = 这条线索作废（rq_drop），她不会再问，我也永远不知道答案，且当场再掉一段黏性。"
        ),
        "rq_stage": "say | ask",
        # 全局闸门：一局最多开 6 条线索（用户 m01384 定）。
        # 21 条线索里真正会出现在一局中的只有这么多，剩下的留给二周目重开。
        "max_clues_per_run": 6,
        "drop_on_cold": True,
        "points": POINTS,
        "react_by": "react_good/react_bad 按 OTA 原型取（见 ota_memory.json 的 archetypes）",
        "archetypes": ARCH,
        "note": "本文件由 tools/build_ota_recall.py 生成，改文案改脚本再跑。",
    },
    "cards": cards,
}

os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w", encoding="utf-8") as f:
    json.dump(doc, f, ensure_ascii=False, indent=2)
    f.write("\n")

from collections import Counter
c2 = Counter(c["_meta"]["rq_stage"] for c in cards)
print("WROTE", os.path.basename(OUT))
print("  cards:", len(cards), "| say:", c2["say"], "| ask:", c2["ask"])
print("  clues:", len(CLUES), "| heavy 走硬闸门:", sum(1 for c in CLUES.values() if c["level"] == "heavy"))
