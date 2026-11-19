# -*- coding: utf-8 -*-
"""《聚场》可玩流程：把一周拆成一步步等玩家点的「场景」。

分工
- engine.py 算账（动作、抽卡、结算、结局），本文件只管「什么时候停下来、停在哪、给哪几个按钮」。
- 所有跨步状态都在 Game 里；界面每次请求只拿一个 step，不自己算任何数。

step 的 type：
  text     一段文字 + 继续
  choice   文字 + 若干按钮
  card     一张卡（标题 / 正文 / 选项）
  receipt  回执（对白 + 数值增减）
  周末     演出结果
  panel    周结算 / 季结算
  name     取名（选风格 → 候选 → 自己写）
  end      结局
"""
from __future__ import annotations

import json
import os
import random
import re

import engine as E
import bill as B

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
WEEKS = 8


def _load(name):
    with open(os.path.join(DATA, name), encoding="utf-8") as f:
        return json.load(f)


TRACKED = ("money", "stamina", "psyche", "fame")
# 这几项也要报给界面：练舞练唱练话术，屏幕上必须有东西动，否则一整周都是白练
SHOWN = TRACKED + ("dance", "sing", "mc", "enjou", "banzi", "kaibox")


def _delta(before, s):
    out = {}
    for k in SHOWN:
        d = round(s.get(k, 0) - before.get(k, 0))
        if d:
            out[k] = d
    return out


def _mates_changed(before, s):
    """三个队友的关系涨跌：团内那张卡到底换来了什么，得当场看见。"""
    out = {}
    names = {"relation_A": "阿棠", "relation_B": "露露", "relation_C": "小满"}
    for k, nm in names.items():
        d = round(s.get(k, 0) - before.get(k, 0))
        if d:
            out[nm] = d
    return out


MATE_TEXT = {"{{A}}阿棠": "阿棠", "{{B}}露露": "露露", "{{C}}小满": "小满"}


def _who_hit(card, option):
    """这张卡的这一选项，主要冲谁去的：看谁的负值最狠，再看正值最多。

    排练室那些事正文里只有一个开场，谁在里面本来就该由选项决定——
    「跟她说清楚规矩」和「这次算我的」面对的是同一个人。
    """
    eff = (option or {}).get("immediate") or {}
    rel = {k: v for k, v in eff.items() if k in ("relation_A", "relation_B", "relation_C")}
    if not rel:
        return ""
    worst = sorted(((v, k) for k, v in rel.items() if v < 0))
    if worst:
        d, k = worst[0]
        return {"relation_A": "阿棠", "relation_B": "露露", "relation_C": "小满"}[k]
    best = sorted(((v, k) for k, v in rel.items() if v > 0), reverse=True)
    if best:
        v, k = best[0]
        return {"relation_A": "阿棠", "relation_B": "露露", "relation_C": "小满"}[k]
    return ""


def _osnap(s):
    """OTA 黏性的快照。_snap() 只拍四大数值，拿它去算 OTA 涨跌会永远得 0。"""
    return {"ota": [{"id": o["id"], "name": o["name"], "stick": round(o["stick"])}
                    for o in (s or {}).get("ota", [])]}


def _sticks(before, s):
    """每条 OTA 的黏性涨跌：键是名字。交互之后玩家要看得见「她离我更近了一点」。"""
    out = {}
    old = {o["id"]: o["stick"] for o in (before or {}).get("ota", []) or []}
    for o in (s or {}).get("ota", []):
        if o["id"] not in old:
            continue          # 新人不是「涨跌」
        d = round(o["stick"]) - old[o["id"]]
        if d:
            out[o["name"]] = d
    return out


def _snap(s):
    return {k: s.get(k, 0) for k in SHOWN}


def _rsnap(s):
    """三个队友的关系快照。_snap() 里没有 relation_A/B/C，
    拿它去算队友涨跌会每次都算成「0 → 当前值」。"""
    return {k: s.get(k, 0) for k in ("relation_A", "relation_B", "relation_C")}


class Game:
    ACT_LEFT = 6          # 一周六个晚上可排
    ACT_SAT = 7           # 周六那一格：排完之后 acts_done 就是 7
    WEEK_EVENTS = 3       # 一周几张「路上遇上的事」，卷在周末两场之后
    LINE_CHANCE = 0.85    # 能推的周，大概率就推（八周里每条线大约走两拍）
    # 一周 6 个事件位。团内只在第 1 位出现一次（以前两处，一季下来队友的戏比 OTA 还多）
    # 一周 6 个事件位，团里的戏只在第 3 位出现一次（一周最多一张，见 _draw_week_events）
    EVENT_SPOTS = [
        ["外部", "external", "外部舆论"],
        ["OTA互动", "OTA相处的瞬间"],
        ["团内", "团内关系"],
        ["同行"],
        ["日常", "ambient", "daily"],
        ["外部", "external", "positive", "舞台事故"],
        ["OTA互动", "daily", "ambient"],
    ]
    # 某个位置抽空了（池子为空 / 全在冷却），按这个顺序接着往下试，不然一周就少一张卡
    EV_FALLBACK = ["团内", "团内关系", "外部", "external", "外部舆论",
                   "OTA互动", "OTA相处的瞬间", "positive", "日常", "ambient",
                   "同行", "舞台事故", "私生", "私生跟踪", "私联恋爱"]

    # 卡面上那行「谁在跟我打交道」：有具体人就写人，没有就写场所
    SCENE = {
        "ambient": "这个城市",
        "日常": "家里",
        "daily": "家里",
        "外部": "网上",
        "external": "网上",
        "外部舆论": "网上",
        "positive": "这一季的运气",
        "同行": "别人的场",
        "舞台事故": "台上",
        "团内": "排练室",
        "团内关系": "排练室",
        "团内冲突": "排练室",
        "私生": "散场以后",
        "私生跟踪": "门外",
        "私联恋爱": "后台",
        "OTA记忆": "",
        "OTA互动": "",
        "OTA相处的瞬间": "",
    }

    def __init__(self, seed=None):
        self.world = E.load_world()
        self.rng = random.Random(seed)
        self.intro = _load("intro.json")
        self.endings = _load("endings.json")
        self.names = _load("idol_names.json")
        self.stances = (_load("stances.json").get("stances") or [])
        self.outside = _load("outside.json")
        self.state = None
        self.queue = []
        self.name = None
        self.acts_done = 0
        self.name_style = None
        self.name_options = []
        self.allow_stance = False   # 二周目：图鉴里有结局时才开
        self.prev_season = None     # 上一季的结局/回响，显示在姿态屏
        self.pending = None      # ("card", card, slots) / ("act",) …
        self._bill = None
        self._week_cards = []    # 这一周暂存的几件事（券账出来之后接上去）
        self._pending_week_settle = False
        # 这一周排到哪一步了：step_week() 只按它决定下一屏放什么
        self.wk = {"act": 0, "mid": 0, "fri": 0, "sat_act": 0, "sat": 0,
                   "bill": 0, "sun": 0, "bill2": 0, "sun_talk": 0,
                   "events": [], "extra": [], "talk": None}
        self.over = False
        self._build_intro()

    # ---------- 队列 ----------
    def push(self, step):
        self.queue.append(step)


    def push_front(self, step):
        self.queue.insert(0, step)

    def current(self):
        """屏幕上现在这一屏。队列是排好的，这里只负责把 pending 对到这一屏上。"""
        n = 0
        while self.queue and n < 40:
            n += 1
            head = self.queue[0]
            if head.get("type") in ("choice", "card", "chat") and not head.get("options"):
                self.queue.pop(0)
                continue
            break
        head = self.queue[0] if self.queue else None
        if head is not None:
            if head.get("type") in ("card", "chat") and head.get("_card"):
                self.pending = ("card", head["_card"], head.get("_slots") or {})
            elif head.get("line") and head.get("_line"):
                self.pending = head["_line"]
            elif head.get("rtalk") and head.get("_rtalk"):
                self.pending = head["_rtalk"]
            elif head.get("talk") and head.get("_talk"):
                self.pending = head["_talk"]
            elif head.get("type") == "choice" and head.get("kind") in ("offer", "empty", "leave"):
                self.pending = (head["kind"], None, None)
        return head


    def advance(self):
        """按「继续」。弹掉这一屏，然后让 after_step() 决定下一屏。"""
        if not self.queue:
            return None
        cur = self.queue[0]
        if cur["type"] in ("choice", "card", "name", "end"):
            return cur
        self.queue.pop(0)
        if not self.queue:
            self.after_step()
        return cur

    # ---------- 下一屏由谁决定：只有这里 ----------
    def after_step(self):
        """走到这一步了：把这一周还欠的格子一格一格补齐，直到有东西可看。"""
        s = self.state
        if s is None or self.over:
            return
        for _ in range(40):
            if self.queue:
                return
            if self.over:
                return
            if s["week"] > WEEKS:
                self._finish()
                return
            # 这一周是否已经开过头（_start_week 会重置 wk，不能用 wk 判断）
            if s.get("_week_started") != s["week"]:
                s["_week_started"] = s["week"]
                self._start_week()
                continue
            # 私联收场排到一半：先把那几屏走完，再回去过日子
            if s.get("_finale") and self._after_finale():
                continue
            if self.step_week():
                continue
            self._finish()
            return

    def start_week_next(self):
        """上一周结算完了：回到「第 N 周」开头（或收尾）。"""
        s = self.state
        if s["week"] > WEEKS:
            self._finish()
            return
        self._start_week()

    def step_week(self):
        """排这一周还没排的那一格。顺序写死在这里，别处不许再插队。

        一周的格：六个晚上 → 路线/版聊那张（第 3 晚后面）→ 周五场 →
        周六那一格晚上 → 周六场 → 券账 → 特典会 → 本周的卡 → 结算。
        """
        wk = self.wk
        if not wk["act"]:
            wk["act"] = 1
            self.push(self._wk_choice())
            return True
        if wk["act"] < self.ACT_LEFT:
            wk["act"] += 1
            if wk["act"] == 4 and not wk["mid"]:
                wk["mid"] = 1
                self.push_midweek()
            else:
                self.push(self._wk_choice())
            return True
        if not wk["sat_act"]:
            wk["sat_act"] = 1
            self.push(self._wk_choice())
            return True
        if not wk["sat"]:
            wk["sat"] = 1
            self.push_live(last=True)
            return True
        if not wk["bill"]:
            wk["bill"] = 1
            self.push(self._bill_step())
            # 周六场下来，先开特典会（人就在桌子那头），再把这一周剩下的卡接在后面，
            # 最后结算。以前是「3 张卡 → 特典」，看着像特典会没开就散场了。
            if wk["talk"]:
                self.push(wk["talk"])
            else:
                self.push({"type": "text", "title": "特典",
                            "body": ["今天收得快，几张券换完，后面就没人排了。"]})
            return True
        if not wk["sun"]:
            wk["sun"] = 1
            self.push_live(last=True, sunday=True)
            return True
        if not wk["bill2"]:
            wk["bill2"] = 1
            self.push(self._bill_step(sunday=True))
            return True
        if not wk["sun_talk"]:
            wk["sun_talk"] = 1
            # 周日的「还是这几个人」过场已删（用户 2026-11-19 拍板）：周日券账
            # 之后直接接一次性提问和三张周卡，选完最后一张卡就结算。
            # 运营/累不累/离开这些一次性提问排在三张周卡前面：选完最后一张卡，
            # 紧接着就是周结算，中间不再插别的屏。
            for st in list(wk["extra"]) + list(wk["events"]):
                self.push(st)
            return True
        self.settle_week()
        return True


    def snapshot(self):
        s = self.state
        if not s:
            return None
        return {
            "name": self.name,
            "week": s.get("week", 1),
            "money": round(s["money"]),
            "stamina": round(s["stamina"]),
            "psyche": round(s["psyche"]),
            "fame": round(s["fame"]),
            "dance": round(s.get("dance", 0)),
            "sing": round(s.get("sing", 0)),
            "mc": round(s.get("mc", 0)),
            "template": round(s.get("template", 0), 2),
            "enjou": round(s.get("enjou", 0)),
            "banzi": round(s.get("banzi", 0)),
            "kaibox": round(s.get("kaibox", 0)),
            # 身份标签（女友粉/重力系那些）不进界面：玩家看到的只是「这个人」
            "ota": [{
                "id": o["id"], "name": o["name"], "stick": round(o["stick"]),
                "weeks": int(o.get("weeks_known", 0)),
                "spend": int(o.get("spend", 3)),
            } for o in s.get("ota", [])],
            "teammates": [
                {"name": "阿棠", "relation": round(s.get("relation_A", 0))},
                {"name": "露露", "relation": round(s.get("relation_B", 0))},
                {"name": "小满", "relation": round(s.get("relation_C", 0))},
            ] if "relation_A" in s else [],
            # 下面是「这一季你都做过什么」的计数：说真话、记住她说过的事、
            # 硬撑、租子断过几次——原来这些数只活在结局判定里，玩家完全看不见
            "stats": {
                "true_talk": int(s.get("true_talk") or 0),
                "clues": len([1 for i in (s.get("clues") or {}).values()
                              if i.get("state") == "known"]),
                "clues_wrong": len([1 for i in (s.get("clues") or {}).values()
                                    if i.get("state") == "wrong"]),
                "pushed": int(s.get("pushed_while_spent") or 0),
                "spent_weeks": int(s.get("spent_weeks") or 0),
                "rent_missed": bool(s.get("rent_missed")),
                "tiers": {"dance": E.tier_name(round(s.get("dance", 0))),
                          "sing": E.tier_name(round(s.get("sing", 0))),
                          "mc": E.tier_name(round(s.get("mc", 0)))},
                "left": {"dance": E.next_tier(round(s.get("dance", 0))),
                         "sing": E.next_tier(round(s.get("sing", 0))),
                         "mc": E.next_tier(round(s.get("mc", 0)))},
            },
        }

    # ---------- 序章 ----------
    def _build_intro(self):
        g = self.intro["group"]
        self.push({
            "type": "text",
            "title": g["name"],
            "body": self.intro["text"],
        })
        self.push({"type": "text", "title": "", "body": [self.intro["before_quote"]]})
        # 2026-11-15：序章的「上台之前三选一」删了（意义不大，一分钟开场里多一次选择反而拖）。
        # 现在读完 before_quote，下一屏按「继续」就落定开局，直接取名。
        c = (self.intro.get("choices") or [{}])[0]
        base = dict(self.intro["base_state"])
        self.state = E.new_state(self.world, choice_id=c.get("id"), rng=self.rng)
        for k, v in base.items():
            if isinstance(v, (int, float)):
                self.state[k] = v
        self.push({"type": "text", "title": "", "body": self.intro["after_quote"]})
        self._build_name()

    # ---------- 取名 ----------
    def _build_name(self):
        styles = [{"id": st["id"], "label": st["name"], "desc": st.get("desc", "")}
                  for st in self.names["styles"]]
        self.push({
            "type": "name",
            "title": "海报上要印个名字",
            "body": ["这个团的 C 位总得有个名字。想要哪一种？"],
            "stage": "style",
            "styles": styles,
        })

    def pick_style(self, sid):
        st = next(x for x in self.names["styles"] if x["id"] == sid)
        pool = list(st["names"])
        self.name_style = sid
        self.name_options = self.rng.sample(pool, min(3, len(pool)))
        self.queue.pop(0)
        self.push({
            "type": "name",
            "title": "挑一个",
            "body": [st.get("desc", "")],
            "stage": "pick",
            "style": st["name"],
            "candidates": self.name_options,
        })

    def set_name(self, name):
        name = (name or "").strip()[:8]
        if not name:
            name = self.name_options[0] if self.name_options else "小夏"
        self.name = name
        self.state["name"] = name
        self.queue.pop(0)
        self.push({"type": "text", "title": "", "body": ["海报上印的是「%s」。" % name]})
        if self.allow_stance:
            self._build_stance()
        else:
            self._start_week()

    # ---------- 二周目：姿态 ----------
    def _build_stance(self):
        sts = [{"id": st["id"], "label": st["name"], "desc": st.get("desc", ""),
                "line": st.get("line", "")} for st in self.stances]
        body = []
        p = self.prev_season or {}
        if p.get("name"):
            bits = ["上一季，你走到了「%s」" % p["name"]]
            meta = []
            if p.get("week"):
                meta.append("第 %d 周" % int(p["week"]))
            if p.get("stage") is not None:
                meta.append("舞台 %s" % p["stage"])
            if p.get("psyche") is not None:
                meta.append("心理 %s" % p["psyche"])
            if meta:
                bits.append("，".join(meta))
            body.append("，".join(bits) + "。")
        body.append("这一次，先想清楚你要什么。姿态不替你选线，也不替你交房租——"
                    "它只是让这一季往那个方向偏一点。")
        self.push({"type": "stance", "title": "这一季，你想成为怎样的偶像",
                   "body": body, "stances": sts})

    def choose_stance(self, sid):
        st = next((x for x in self.stances if x["id"] == sid), None)
        if st is None:
            st = {"id": "none", "name": "不选，照旧", "bonus": {}}
        E.apply_stance(self.state, st)
        self.queue.pop(0)
        if st.get("id") == "none":
            self.push({"type": "text", "title": "", "body": ["这一季，先不给自己定什么。"]})
        else:
            self.push({"type": "text", "title": "",
                       "body": ["这一季，我给自己定的是「%s」。" % st["name"]]})
        self._start_week()

    # ---------- 一周 ----------

    def _wk_choice(self):
        """「周几晚上做点什么」这一屏（只返回 step，不往队列里塞）。"""
        left = self.ACT_SAT - self.wk["act"]
        s = self.state
        day = 7 - left if left > 0 else 6
        DAY_CN = ("", "一", "二", "三", "四", "五", "六", "日")
        st = round(s["stamina"])
        if left > 0:
            body = ["周六之前还有 %d 个晚上。" % (left - 1)]
        else:
            body = ["周五那一场刚下来，周六还有一场。"]
        if st < 15:
            body.append("身体一直是空的，脑子里像隔着一层。")
        return {
            "type": "choice",
            "title": "周%s，晚上做点什么" % DAY_CN[day],
            "body": body,
            "kind": "act",
            "options": [
                {"id": "dance", "label": "练舞",
                 "desc": "体力 −18 · 钱 −40 · 舞 +%d%s" % (
                     E.act_gain(s, "dance"), self._repeat_note(s, "dance"))},
                {"id": "sing", "label": "练唱",
                 "desc": "体力 −18 · 钱 −40 · 唱 +%d%s" % (
                     E.act_gain(s, "sing"), self._repeat_note(s, "sing"))},
                {"id": "mc", "label": "练营业话术",
                 "desc": "体力 −10 · 钱 −20 · 营业 +%d%s" % (
                     E.act_gain(s, "mc"), self._repeat_note(s, "mc"))},
                {"id": "content", "label": "拍内容发微博", "desc": "体力 −8 · 人气 +1"},
                {"id": "work", "label": "开直播", "desc": "体力 −22 · 钱 +380 · 人气 +2"},
                {"id": "rest", "label": "躺一整天", "desc": "体力 +28 · 心理 +2"},
            ],
        }


    def _face(self, card, slots, who=None):
        """这一屏是谁在对面：优先实际角色名，其次场所。"""
        names = []
        if who and who.get("name"):
            names.append(who["name"])
        for k, o in (slots or {}).items():
            if k == "speaker" and o is who:
                continue
            nm = (o or {}).get("name")
            if nm and nm not in names:
                names.append(nm)
        if names:
            if len(names) == 1:
                return names[0]
            return "、".join(names[:2]) + ("等" if len(names) > 2 else "")
        if card.get("scene"):
            return card["scene"]
        return self.SCENE.get(card.get("type", ""), "")

    @staticmethod
    def _repeat_note(s, act):
        """连着两晚做同一件事的提示。只在真的减半（0.5）的动作上写——
        拍内容是 ×0.8、躺/开播不减，不能睁眼说瞎话。"""
        if s.get("_last_act") == act and E.ACT_REPEAT.get(act) == 0.5:
            return "（连着做，减半）"
        return ""

    ACT_TEXT = {
        "dance": "练到快十点，最后一节才算顺下来。",
        "sing": "嗓子一开始是哑的，唱到后面反而开了。",
        "mc": "对着镜子说了一个小时的话，说到自己都想笑。",
        "content": "拍了一组，挑了半天配了句话发出去。",
        "work": "架好手机播到凌晨，在线人数一直没过两位数。",
        # 休息没有「事件」，回复轮着来，别天天煮面
        "rest": ["什么都没做，睡到下午，起来煮了碗面。",
                 "闹钟定了五个也没用，一觉睡到天黑，屋里暗得分不清几点。",
                 "在地板上躺了一下午，听完一整张专辑，手机都懒得看。",
                 "去楼下泡了个热水澡，出来的时候觉得骨头轻了二两。",
                 "给家里打了个电话，没提这行的事，光听我妈讲菜市场就听了半个钟头。",
                 "翻了一遍这一季的返图，挑出最喜欢的一张设成了锁屏。"],
    }

    def _maybe_ask_stay(self):
        """第六周，还剩两个晚上：这一季跳完就不跳了吧？这是「现生快乐」那一类的入口。"""
        s = self.state
        if s["week"] != WEEKS or s.get("leave_asked"):
            return None
        if self.acts_done < self.ACT_LEFT - 2:
            return None
        s["leave_asked"] = True
        return {
            "type": "choice",
            "kind": "leave",
            "title": "这个月还剩两个晚上",
            "body": ["排班表贴在排练室门后面。这个月的最后两个晚上，我盯着看了很久。"],
            "options": [
                {"id": "stay", "label": "再撑一周，把这一季跳完",
                 "desc": "都到这儿了，停下来反而空"},
                {"id": "leave", "label": "算了，这季跳完就不跳了",
                 "desc": "钱还是会紧，但晚上是自己的了"},
            ],
        }

    def choose_leave(self, oid):
        s = self.state
        s["chose_leave"] = (oid == "leave")
        self.pending = None
        self.queue.pop(0)
        if oid == "leave":
            body = ["这两个晚上，我去了一趟便利店，买了两瓶酒，坐在桥边喝到很晚。"]
            delta = {"psyche": 4, "stamina": 8}
            s["psyche"] += 4
            s["stamina"] += 8
        else:
            body = ["我把排班表折起来放进包里，第二天照常去排练了。"]
            delta = {"psyche": -2, "stamina": -4}
            s["psyche"] -= 2
            s["stamina"] -= 4
        E.clamp(s)
        self.push({"type": "receipt", "title": "这个月还剩两个晚上", "body": body, "delta": delta})
        self.after_step()
        return True

    def choose_act(self, aid):
        s = self.state
        before = _snap(s)
        _osnap_before = _osnap(s)
        _rsnap_before = _rsnap(s)
        E.do_act(s, aid, self.rng)
        self.acts_done += 1
        self.queue.pop(0)
        extra = []
        if s.get("_last_act_spent"):
            extra.append("身体是空的，手上在动，人不在。")
            s.pop("_last_act_spent", None)
        # 练功类：把「从几档到几档、离下一档还差多少」说清楚，
        # 否则玩家只看到体力掉，不知道自己练出了什么
        key = {"dance": "dance", "sing": "sing", "mc": "mc"}.get(aid)
        if key:
            v = round(s[key])
            left = E.next_tier(v)
            now = "现在 %d，%s" % (v, E.tier_name(v))
            if left:
                extra.append(now + "；再练 %d 点到下一档。" % left)
            else:
                extra.append(now + "；已经压得住整场了。")
        act_text = self.ACT_TEXT.get(aid, "")
        if isinstance(act_text, (list, tuple)):
            act_text = self.rng.choice(act_text)
        self.push({"type": "receipt", "title": act_text,
                   "body": extra, "delta": _delta(before, s),
                   "sticks": _sticks(_osnap_before, s),
                   "mates": _mates_changed(_rsnap_before, s),
                   "skill": key,
                   "skill_now": round(s[key]) if key else None,
                   "skill_tier": E.tier_name(round(s[key])) if key else None,
                   "skill_left": E.next_tier(round(s[key])) if key else None})

        self.after_step()

    # ---------- 版聊 + 一张卡 ----------
    def push_midweek(self):
        """六个晚上排完之后的版聊：一句白天的碎话 + 路上遇上的一张卡。"""
        s = self.state
        self.pending = None
        if s["stamina"] < 25:
            s["nights_stamina_low"] = s.get("nights_stamina_low", 0) + 1
        if s["stamina"] < 15:
            s["psyche"] -= 5
            s["spent_weeks"] = s.get("spent_weeks", 0) + 1
            E.clamp(s)
            self.push({"type": "receipt", "title": "身体一直是空的",
                       "body": ["这周没睡够，礼拜三开始就在飘，对着人笑的时候知道自己在笑。"],
                       "delta": {"psyche": -5}})
        card = E.draw(s, self.world, self.rng, kinds=["版聊"])
        if not card or not card.get("options"):
            self.push({"type": "text", "title": "", "body": ["今晚没人说话，我看了两眼就睡了。"]})
            return
        slots = E.cast(s, card, self.rng, self.world)
        # 抽到新人卡但新人名额满了：换一张，别把老粉当「第一次来的人」演。
        tries = 0
        while slots is None and E.wants_new_face(card) and tries < 4:
            tries += 1
            card = E.draw(s, self.world, self.rng, kinds=["版聊"])
            if not card or not card.get("options"):
                break
            slots = E.cast(s, card, self.rng, self.world)
        if slots is None:
            # 卡上要的人不在场、新生也没名额：这张卡根本演不起来。
            self.push({"type": "text", "title": "", "body": ["今晚没人说话，我看了两眼就睡了。"]})
            return
        step = self._render_chat(card, slots)
        step["_card"] = card
        step["_slots"] = slots
        self.push(step)

    def _render_chat(self, card, slots):
        """版聊上屏：把 messages 铺成聊天记录，引用的那条显示成小引用块。"""
        cid = card.get("id")
        if self.state is not None and cid:
            self.state.setdefault("seen", []).append(cid)
        msgs = []
        for m in card.get("messages") or []:
            who = m.get("from") or "speaker"
            name = "你" if who == "you" else ((slots or {}).get(who) or {}).get("name", "对方")
            quoted = ""
            qi = m.get("quote")
            if isinstance(qi, int) and 0 <= qi < len(msgs):
                quoted = msgs[qi]["text"]
            msgs.append({
                "who": name,
                "me": who == "you",
                "text": self._fill(m.get("text", ""), slots),
                "time": m.get("time", ""),
                "quote": quoted,
            })
        return {
            "type": "chat",
            "title": card.get("title", "版聊"),
            "label": "版聊",
            "no": card.get("no"),  # 全池序号（卡角标）
            "time": card.get("time", ""),
            "messages": msgs,
            "options": [{"id": o["id"], "label": self._fill(o.get("label", ""), slots),
                         "desc": self._fill(o.get("desc", ""), slots)}
                        for o in (card.get("options") or [])],
        }

    def _build_weekend_arc(self):
        """（旧接口）只排周五那一场。"""
        self.push_live(last=False)


    def _fill(self, t, slots):
        if not t:
            return t or ""
        for k, o in slots.items():
            if not o:
                continue
            t = t.replace("{{%s.ta}}" % k, "TA").replace("{{%s}}" % k, o["name"])
        # 她自己的细节：猫叫什么、常点哪杯、老家在哪、最爱哪首。
        # 这些值整局固定（见 engine.protagonist / learn_memory），
        # 必须在下面那道「兜成对方」之前换掉——否则「猫叫『对方』」。
        mem = E.prota_memory(self.state)
        for k, v in mem.items():
            if not v:
                continue
            token = "{{%s}}" % k
            if token in t:
                t = t.replace(token, str(v))
                # 她当着玩家的面说过这个细节了：登记进「已揭示」，收场拷问优先出这些。
                rec = self.state.setdefault("_prota_revealed", [])
                if k not in rec:
                    rec.append(k)
        # 还有没填上的占位符（选角没落地、或者卡要的槽跟 casting 声明的不一致）：
        # 绝不能把 {{xxx}} 原样端到玩家眼前。这里兜成「对方」，至少读得通。
        if "{{" in t:
            t = re.sub(r"\{\{[a-zA-Z_]+\}\}", "对方", t)
            t = t.replace("{{", "").replace("}}", "")
        return t

    def _card_body(self, card, slots):
        """卡面正文。回考卡里的 {truth} 必须在「上屏这一刻」就换掉——
        她第一次说这个细节时真值就得掷死，不能等玩家点了选项才定。
        特典（_render_talk）和正片（_render_card）走的都是这一条路。

        但两张卡的写法不一样：她说（say）要把真话讲出来，她问（ask）不能——
        问句原样带真值就等于把答案印在题干上（『我最近又陷进短视频里了…』
        然后问「是哪一样」）。所以 ask 一律抹成「那个」，靠下面三个选项交代范围。
        """
        body = [self._fill(card.get("narrative", ""), slots)]
        meta = card.get("_meta") or {}
        cid = meta.get("clue")
        stage = meta.get("rq_stage")
        if cid and stage in ("say", "ask"):
            # 问的那张卡正文里也写着「我上次说的那个是{truth}来着」，
            # 只补 say 那一头，问句就顶着一串花括号上场了。
            word = E.ensure_truth(self.state, cid, self.rng) if stage == "say" else "那个"
            body = [b.replace("{truth}", word or "那个") for b in body]
        return body

    def _card_opts(self, card):
        """回考「她问的是哪一样」：选项顺序按本局掷的排，别让玩家背「第一个」。"""
        opts = list(card.get("options") or [])
        meta = card.get("_meta") or {}
        if meta.get("rq_stage") == "ask":
            opts = self._ask_options(card, opts)
        return opts

    def _render_card(self, card, slots):
        # 上屏即登记：draw() 会拿这份名单给「这一季见过的卡」降权（不硬禁）。
        cid = card.get("id")
        if self.state is not None and cid:
            self.state.setdefault("seen", []).append(cid)
        meta = card.get("_meta") or {}
        rq = meta.get("rq_stage")
        body = self._card_body(card, slots)
        if rq == "ask":
            # 三选一考的是记性：选项上不能带「会加/会扣」的暗示，只要那个词本身
            body.append("（她问的是哪一样。）")
        # 排练室那些事：谁在场就说谁。卡上写了 {{A}} 就是认准了阿棠，
        # 没写的话，由第一个选项的得失推一个出来（同一个人）
        cast_name = ""
        for plain, nm in MATE_TEXT.items():
            if plain in card.get("narrative", ""):
                cast_name = nm
                break
        if not cast_name:
            for o in card.get("options") or []:
                cast_name = _who_hit(card, o)
                if cast_name:
                    break
        # 选完才给数值：选项本身只写「我打算怎么做」，
        # 具体涨跌由右下角的弹窗和回去后的队友面板交代。
        opts = self._card_opts(card)
        face = self._face(card, slots)
        if cast_name and face in ("", "排练室"):
            face = "排练室 · " + cast_name
        return {
            "type": "card",
            "title": card["title"],
            "face": face,
            "recall": rq == "ask",
            "compact": card.get("type") not in ("OTA记忆",),
            "body": body,
            "no": card.get("no"),  # 全池序号（卡角标）
            "options": [{"id": o["id"], "label": self._fill(o.get("label", ""), slots),
                         "desc": "" if rq == "ask"
                                 else self._fill(o.get("desc", ""), slots)}
                        for o in opts],
        }

    def _ask_options(self, card, opts):
        """回考三选一的上屏顺序：按这一局锁定的真值重新排。

        卡数据里三道题的正确答案都写在 pick_0（生成脚本为了让 diff 稳定），
        真值一随机就必须重排，否则玩家背「第一个」就永远答对。
        """
        meta = card.get("_meta") or {}
        cid = meta.get("clue")
        if not cid or len(opts) < 2:
            return opts
        order = E.ask_order(self.state, cid, len(opts), self.rng)
        if len(order) != len(opts):
            return opts
        return [opts[i] for i in order]

    def _rq_reply(self, card, o, slots):
        """回考答完，按原型取她那一句。"""
        pick = o.get("rq_pick")
        if not pick:
            return ""
        meta = card.get("_meta") or {}
        who = (slots or {}).get(pick.get("slot") or "speaker") or {}
        arch = who.get("archetype", "gravity")
        cid = pick.get("clue")
        # 真值从「本局锁定表」里取——她随口说那一屏定下的那个词。
        # 以前这里读 s["clues"][cid]["truth"]，但锁定线索时并不会写这个键，
        # 于是永远空着，台词里就露出字面的 {truth}。
        truth = E.ensure_truth(self.state, cid, self.rng) if cid else ""
        correct = bool(truth) and (o.get("label") or "").strip() == truth
        tab = meta.get("react_good" if correct else "react_bad") or {}
        txt = tab.get(arch) or tab.get("gravity") or ""
        if not txt:
            return ""
        wrong = o.get("label") or ""
        txt = txt.replace("{truth}", truth).replace("{wrong}", wrong)
        return txt

    def choose_card(self, oid):
        origin = (self.current() or {}).get("origin")
        if not self.pending:
            # 已经结算过（比如双击 / 回包重复）：把这一屏当成「继续」
            return self.advance()
        if self.pending[0] == "line":
            # 剧情线的卡被当成普通卡点了（line 标记丢了）：转给 choose_story
            return self.choose_story(oid)
        if self.pending[0] == "rtalk":
            # 「谈一谈」那张卡被当成普通卡点了：转给 choose_romance_talk
            return self.choose_romance_talk(oid)
        if self.pending[0] == "talk":
            # 特典那张卡被当成普通卡点了：屏幕上是特典卡才转过去，否则就是被别的卡抢了 pending
            if (self.queue and self.queue[0].get("talk")):
                return self.choose_talk(oid)
            if (self.queue and self.queue[0].get("_card")):
                self.pending = ("card", self.queue[0]["_card"], self.queue[0].get("_slots") or {})
                return self.choose_card(oid)
        cur = self.queue[0] if self.queue else {}
        if self.pending[0] == "card" and cur.get("_card"):
            # 屏幕上的卡自己带一份（周末连排时 pending 可能已经被下一张换掉）
            _, card, slots = self.pending
            if cur.get("_card") is not card:
                card = cur["_card"]
                slots = cur.get("_slots") or slots
                self.pending = ("card", card, slots)
        _, card, slots = self.pending
        # 这一屏显示的是不是 pending 那张卡？周末连排几张时 pending 会被后一张换掉，
        # 点开的是前一张，就得按队列里那一张重新取。
        shown_t = (self.queue[0].get("title") or "") if self.queue else ""
        if shown_t and shown_t != (card.get("title") or ""):
            for x in self.queue:
                if x.get("type") == "card" and (x.get("title") or "") == shown_t:
                    if x.get("talk"):
                        return self.choose_talk(oid)
                    if x.get("_card"):
                        card = x["_card"]
                        slots = x.get("_slots") or slots
                    break
        o = next(x for x in card["options"] if x["id"] == oid)
        before = _snap(self.state)
        _osnap_before = _osnap(self.state)
        _rsnap_before = _rsnap(self.state)
        _meta = card.get("_meta") or {}
        E.apply_option(self.state, o, self.rng, slots, card=card)
        # ---- 私联收场：这一题对没对，往前挪一格
        if _meta.get("finale"):
            fin = self.state.get("_finale") or {}
            truth = E.ensure_truth(self.state, (o.get("rq_pick") or {}).get("clue"),
                                   self.rng)
            if truth and (o.get("label") or "").strip() == truth:
                fin["ok"] = int(fin.get("ok") or 0) + 1
            fin["idx"] = int(fin.get("idx") or 0) + 1
            self.state["_finale"] = fin
        # ---- 收场那两条路：沉沦去「唯一」，断联去失控
        if _meta.get("finale_choice"):
            fin = self.state.get("_finale") or {}
            if oid == "cut_clean":
                # 说了别来，事情却没停。这一段玩家点不了，只有数字在走。
                fin["phase"] = "collapse"
                fin["cidx"] = 0
                fin["script"] = self._collapse_script()
                self.state["_collapse"] = True
                self.state["_collapse_who"] = (
                    (slots or {}).get("ta") or {}).get("name")
                self.state["flags"].add("final_collapse")
            else:
                # 沉沦：不公开也不断，就这么一直下去。这就是「唯一」。
                fin["phase"] = "done"
                self.state["flags"].add("truly_seen")
            self.state["_finale"] = fin
        self.state["cooldown"][card["id"]] = int(card.get("cooldown", 3))
        self.state["_extra_cards"] = self.state.get("_extra_cards", 0)
        self.pending = None
        self.queue.pop(0)
        # 这一屏上的那张卡点完就真没了：把队列里其余同一张卡的副本也拿掉。
        # 队列里排着好几张卡时（这周几件事 + 剧情线 + 特典），同一张会在队列里留副本，
        # 等轮到副本时玩家已经在别的一周了。
        self.queue[:] = [x for x in self.queue
                         if not (x.get("type") in ("card", "chat") and x.get("_card") is card)]
        # 回执不能只剩一个标题。选项没写 note 时退到 desc（那是「这么做的后果」），
        # 再没有就退一句中性的收束——总之不能给玩家一屏空白。
        body = []
        for x in (o.get("note"), o.get("desc"), "就这样吧。"):
            if x and str(x).strip():
                body = [self._fill(x, slots)]
                break
        # 回考：她问的那件事，我答对/答错了，她当场怎么接——这一句才是玩家想看的反馈
        reply = self._rq_reply(card, o, slots)
        if reply:
            body.insert(0, reply)
        for d in (o.get("delayed") or [])[:1]:
            if d.get("note"):
                body.append("（%s·%s）" % (d.get("when", ""), self._fill(d["note"], slots)))
        # 回复插队首：选了哪张卡，那条回复立刻跟在后面，不把几张卡的回复攒到一起
        self.queue.insert(0, {"type": "receipt", "title": self._fill(o.get("label", ""), slots),
                   "body": body, "delta": _delta(before, self.state),
                   "sticks": _sticks(_osnap_before, self.state),
                   "mates": _mates_changed(_rsnap_before, self.state),
                   "face": self._face(card, slots)})
        self.after_step()

    @staticmethod

    def _build_weekend_arc(self):
        """周五那一场：只出演出结果，不结算、不排特典。特典放在周六。"""
        self._build_live(last=False)

    def push_live(self, last=False, sunday=False):
        """周末那一场：只算演出、只把这一屏排出去；券账/特典/结算由 step_week 接着排。"""
        s = self.state
        rng = self.rng
        fatigue = (s["stamina"] - 50) / 50 * 5.0
        sc = E.stage_score(s) + fatigue + rng.uniform(-5, 5)
        if sunday:
            sc -= 3.5                     # 周日加场：人少一点，嗓子也哑了
        if sc >= 64:
            tier, lines = "神场", ["有一瞬间我忘了自己在哪，台下的声音是压过去的那种。"]
            E.add_fame(s, 8); s["psyche"] += 3; s["gorshou"] = s.get("gorshou", 0) + 1
            for o in s["ota"]:
                o["stick"] += 3
        elif sc >= 54:
            tier, lines = "好场", ["下来的时候 staff 说我今天眼睛是亮的。"]
            E.add_fame(s, 5); s["psyche"] += 1
            for o in s["ota"]:
                o["stick"] += 2
        elif sc >= 44:
            tier, lines = "平场", ["跳完了，不出错，也就跳完了。"]
            E.add_fame(s, 2)
        elif sc >= 34:
            tier, lines = "冷场", ["台下没坐满，掌声落下来的时候散得很快。"]
            s["psyche"] -= 4
            for o in s["ota"]:
                o["stick"] -= 1.5
        else:
            tier, lines = "翻车", ["第二段走位踩空了半步，我笑了一下，把下一个动作接过去。"]
            s["psyche"] -= 8; s["enjou"] += 3
            for o in s["ota"]:
                o["stick"] -= 2.5
        s["max_single"] = max(s["max_single"], sc)
        if tier in ("冷场", "翻车"):
            s["blew_it"] = int(s.get("blew_it") or 0) + 1
        if s["psyche"] < 20:
            s["played_while_collapsing"] = True
        E.clamp(s)
        warm = E.warm_ota(s)
        # 每场各算各的账（人气决定今天谁来、来几个），state 里累加这一周的券数与
        # 收入，结算把所有场次加总——券账屏展示的钱就是会进钱包的钱。
        self._bill = B.weekly_bill(s, warm)
        s["_week_tickets"] = s.get("_week_tickets", 0) + self._bill["tickets"]
        s["_week_income"] = s.get("_week_income", 0) + self._bill["yen"]
        self._collect_week_extras(warm)
        self.push({
            "type": "live",
            "title": ("周日·%s" % tier) if sunday else (("周六·%s" % tier) if last else ("周五·%s" % tier)),
            "body": lines,
            "tier": tier,
            "score": round(sc, 1),
            "delta": {"fame": round(s["fame"]), "psyche": round(s["psyche"])},
        })

    def _wait_after(self):
        """一屏内容出完了：队列里还剩东西就让它们接着走，空了就派发下一格。"""
        self.after_step()

    def _bill_step(self, sunday=False):
        return {"type": "bill", "title": "周日这一场的券" if sunday else "这一场的券",
                "body": ["券 %d 块一张。买了券的人，才能排到桌子前面坐一会儿。"
                         % self._bill["price"]],
                "bill": self._bill}

    def _collect_week_extras(self, warm):
        """这一周的事：三张卡、她的话、运营那条路、特典那张卡，全部先算好放着。

        push_live() 一周会跑三次（周五、周六、周日）。「累不累、接不接运营、
        这季跳不跳完」都是一次性提问，各自只生成一次：生成时就把 asked 标志
        立起来了。所以这里得把它们攒进 wk["extra"]，不能每场拿新结果整体覆盖——
        否则周五生成的那张卡，到周日排卡时已经被后两场冲成空列表了。

        同理，`ota_pick` 也有副作用（抽到 ask 卡就把线索标成已问、上冷却），
        所以一周只能抽一次：以前这里周五、周六、周日各抽一遍、只留最后一遍，
        被覆盖掉的那两次照样把线索吃掉了——「她问起那件事」整季只出现一两次，
        就是因为大半在没上屏的那两遍里被悄悄消费掉了。
        """
        wk = self.wk
        if wk.get("_prep"):
            return
        wk["_prep"] = 1
        wk["events"] = self._draw_week_events()
        have = {x.get("kind") for x in wk["extra"]}
        for st in (self._maybe_ask_tired(warm), self._maybe_ask_offer(),
                   self._maybe_ask_stay()):
            if st and st.get("kind") not in have:
                wk["extra"].append(st)
                have.add(st.get("kind"))
        wk["talk"] = self._make_talk(warm)

    def _make_talk(self, warm):
        if not warm:
            return None
        names = "、".join(
            o["name"] + ("（第一次来）" if (not o.get("is_seed", True)
                                          and o.get("met_week") == self.state["week"]) else "")
            for o in warm)
        card, who = E.ota_pick(self.state, self.world, self.rng, warm)
        if not (card and who):
            return {"type": "text", "title": "特典",
                    "body": ["留在后面等着的是%s。" % names]}
        slots = E.cast(self.state, card, self.rng, self.world)
        # 新人卡（hatch_only）生不出人时，卡就作废——不能拿今天留下来的老粉顶上去，
        # 否则「第一次来的人」演出来的是第零排那张熟了的脸。
        tries = 0
        while not slots and E.wants_new_face(card) and tries < 4:
            tries += 1
            card, who = E.ota_pick(self.state, self.world, self.rng, warm)
            if not (card and who):
                return {"type": "text", "title": "特典",
                        "body": ["留在后面等着的是%s。" % names]}
            slots = E.cast(self.state, card, self.rng, self.world)
        if not slots and E.wants_new_face(card):
            return {"type": "text", "title": "特典",
                    "body": ["留在后面等着的是%s。" % names]}
        if not slots:
            # 选角没落地：把这张卡自己声明的每个槽都指给「今天留下来的人」。
            # 以前这里只塞 speaker，卡要的槽叫 nightowl/devotee 时就填不上，
            # 正文会顶着裸占位符上场（「特典突然一张残卡」就是这么来的）。
            slots = {}
            for cs in (card.get("casting") or []):
                if cs.get("slot"):
                    slots[cs["slot"]] = who
            slots.setdefault("speaker", who)
        step = self._render_talk(card, slots, who)
        step["talk"] = True
        step["_talk"] = ("talk", card, slots)
        return step

    TEAM_TYPES = ("团内", "团内关系", "团内冲突")

    def _draw_week_events(self):
        out = []
        used = set()
        team_n = 0
        s = self.state
        spots = list(self.EVENT_SPOTS)
        tries = 0
        # 兑现卡优先：上周埋下的那件事这周回来找你，先占事件位。
        # 只给一次机会——这周排不进去（要的人不在场、位子已经满了），
        # 就当场作废，不再拖到下周；埋下的账不该越滚越久。
        due_ids = list(s.pop("_due_cards", []) or [])
        if due_ids:
            by_id = {c.get("id"): c for c in self.world.get("cards") or []}
            for cid in due_ids:
                if len(out) >= self.WEEK_EVENTS:
                    break
                card = by_id.get(cid)
                if not card or not card.get("options") or card["id"] in used:
                    continue
                slots = E.cast(s, card, self.rng, self.world)
                if slots is None:
                    continue
                used.add(card["id"])
                if card.get("type") in self.TEAM_TYPES:
                    team_n += 1
                step = self._render_card(card, slots)
                step["_card"] = card
                step["_slots"] = slots
                step["origin"] = "week"
                out.append(step)
        while len(out) < self.WEEK_EVENTS and tries < len(spots) + self.WEEK_EVENTS:
            idx = int(s.get("_ev_idx") or 0)
            kinds = spots[idx % len(spots)]
            tries += 1
            s["_ev_idx"] = idx + 1
            card = E.draw(s, self.world, self.rng, kinds=kinds)
            if not card or not card.get("options") or card["id"] in used:
                card = E.draw(s, self.world, self.rng, kinds=self.EV_FALLBACK)
            if not card or not card.get("options") or card["id"] in used:
                card = E.draw(s, self.world, self.rng,
                              kinds=[k for k in self.EV_FALLBACK if k != "ambient"])
            # 团里的戏一周最多一场：多了会让人觉得整季都在跟队友吵架
            if card and card.get("type") in self.TEAM_TYPES:
                if team_n >= 1 or not any(k in self.TEAM_TYPES for k in kinds):
                    card = E.draw(s, self.world, self.rng,
                                  kinds=["外部", "external", "日常", "daily",
                                         "OTA互动", "OTA相处的瞬间", "ambient", "positive",
                                         "同行"])
            if card and card.get("type") in self.TEAM_TYPES:
                team_n += 1
            if not card or not card.get("options") or card["id"] in used:
                continue
            used.add(card["id"])
            slots = E.cast(s, card, self.rng, self.world)
            if slots is None:
                # 演不起来（要的人不在场）：这张算没抽到，继续补，别塞一张残卡进队列
                continue
            step = self._render_card(card, slots)
            step["_card"] = card
            step["_slots"] = slots
            step["origin"] = "week"
            out.append(step)
        return out


    def _maybe_ask_tired(self, warm):
        """季中之后、我这一季一次真话都没说过、嘴上已经全是现成话的时候，
        她会当面问一句「你是不是有点累」。回什么，决定这一季会不会变成空心。"""
        s = self.state
        if s.get("empty_asked") or s["week"] < 3:
            return
        _t = int(s.get("truth_pick") or 0)
        _f = int(s.get("safe_pick") or 0)
        if (_t + _f) < 2 or (float(_t) / (_t + _f)) > 0.25:
            return
        who = None
        for o in (warm or []):
            if o.get("stick", 0) >= 45:
                who = o
                break
        if who is None:
            return
        s["empty_asked"] = True
        s["empty_asked_who"] = who["name"]
        self.pending = ("empty", None, None)
        _st = {
            "type": "choice",
            "kind": "empty",
            "title": "她问了一句",
            "body": ["收桌子的时候，%s 还没走。她把券放在桌角，没递过来，"
                     "看了一会儿才说：『你是不是有点累。』" % who["name"]],
            "options": [
                {"id": "reply", "label": "笑一下：『没有啊，挺好的。』",
                 "desc": "这句我今天已经说过好几遍了"},
                {"id": "truth", "label": "停一下，说：『有点。』",
                 "desc": "说出来的时候，声音自己先软了"},
            ],
        }
        return _st

    def choose_empty(self, oid):
        s = self.state
        s["empty_choice"] = "reply" if oid == "reply" else "truth"
        self.pending = None
        self.queue.pop(0)
        if oid == "reply":
            s["safe_pick"] = int(s.get("safe_pick") or 0) + 1
            s["template"] = min(1.0, s["template"] + 0.05)
            body = ["她说『那就好』，把券推过来，笑了一下。", "那两秒钟里我没说话，她也没再问。"]
            delta = {"psyche": -4}
        else:
            s["truth_pick"] = int(s.get("truth_pick") or 0) + 1
            s["true_talk"] = int(s.get("true_talk") or 0) + 1
            s["template"] = max(0.0, s["template"] - 0.05)
            body = ["她愣了一下，说『嗯』。", "后来她什么都没再问，我也没再多说。"]
            delta = {"psyche": 3, "fame": -1}
        E.clamp(s)
        self.push({"type": "receipt", "title": "她问了一句", "body": body, "delta": delta})
        self.after_step()

    # ---------- 运营递来的那条路（守住本心的入口） ----------
    # 引擎里 offer_seen/offer_choice 是 do_week 内部的口径；界面把一周拆成很多屏，
    # 这里要按「这一周该不该问了」自己判，不能等引擎那面旗。
    OFFER_FROM_WEEK = 4
    OFFER_TEXT = {
        "炒 CP": ("运营把一份策划摊在桌上：和露露捆一个『双人线』，每周发两条互动，"
                 "超话会自己吵起来。", "这条能火，做不做？"),
        "接一条擦边商务": ("运营推过来一张报价单，是一个擦边饮料的商单。钱不少，"
                       "发出来会有人骂，也一定会有人转。", "这条能火，做不做？"),
    }

    def _maybe_ask_offer(self):
        """季中之后，运营来递那条「会火的路」。这是我这一季唯一一次当面说不的机会，
        结局「守住本心」就靠它。引擎里早就设了 offer_seen/offer_choice，
        可界面从来没把这件事问出来——那条路一直是被默默拒绝的。"""
        s = self.state
        if s["week"] < self.OFFER_FROM_WEEK or s.get("offer_choice") or s.get("offer_asked"):
            return None
        s["offer_asked"] = True
        if not s.get("offer_kind"):
            _offers = ["炒 CP", "接一条擦边商务"]
            s["offer_kind"] = _offers[(s["week"] - 3) % 2]
        kind = s.get("offer_kind")
        head, tail = self.OFFER_TEXT.get(kind, ("运营递过来一个能火的路子。", "这条能火，做不做？"))
        # 排在券账后面（和其他几件事一起），由 _flush_week_events 接上
        _st = {
            "type": "choice",
            "kind": "offer",
            "title": "运营找我谈话",
            "face": "后台走廊",
            "body": [head],
            "options": [
                {"id": "refuse", "label": "摇了摇头：『这个我不做。』",
                 "desc": "话一出口，走廊里安静了一拍"},
                {"id": "take", "label": "点头：『行，就按这个来。』",
                 "desc": "那条路是真的会火，也真的会烧"},
            ],
        }
        return _st


    def choose_offer(self, oid):
        s = self.state
        s["offer_choice"] = "refuse" if oid == "refuse" else "take"
        self.pending = None
        self.queue.pop(0)
        if s["offer_choice"] == "refuse":
            s["psyche"] -= 3
            body = ["我说这个我不做。运营看了我一眼，把那份东西收回去，说『行，那就再想想』。",
                    "那天晚上我睡得很沉，这件事没再提过。"]
            delta = {"psyche": -3}
        else:
            s["enjou"] = float(s.get("enjou") or 0) + 30
            gained = E.add_fame(s, 12)
            body = ["我点头了。第二周超话就炸了，票是真的卖得比以前快。",
                    "也有人在板子上把我的名字和那件事一起挂了出来。"]
            delta = {"fame": int(gained) if gained == int(gained) else round(gained, 1)}
        E.clamp(s)
        self.push({"type": "receipt", "title": "运营找我谈话", "body": body, "delta": delta})
        self.after_step()

    def _render_talk(self, card, slots, who):
        # 特典也走回考卡（「她随口说的一件事」就在特典池里）：
        # 走这条路以前直接塞 narrative，{truth} 就顶着一串花括号上场了。
        meta = card.get("_meta") or {}
        rq = meta.get("rq_stage")
        body = self._card_body(card, slots)
        if rq == "ask":
            body.append("（她问的是哪一样。）")
        opts = self._card_opts(card)
        return {
            "type": "card",
            "talk": True,
            "title": card["title"],
            "face": self._face(card, slots, who),
            "speaker": who["name"],
            "recall": rq == "ask",
            "compact": card.get("type") not in ("OTA记忆",),
            "body": body,
            "no": card.get("no"),  # 全池序号（卡角标）
            "options": [{"id": o["id"], "label": self._fill(o["label"], slots),
                         "desc": "" if rq == "ask"
                                 else self._fill(o.get("desc", ""), slots)}
                        for o in opts],
            "_card": card,
            "_slots": slots,
        }

    def choose_talk(self, oid):
        if not self.pending:
            return self.advance()
        _, card, slots = self.pending
        o = next(x for x in card["options"] if x["id"] == oid)
        before = _snap(self.state)
        _osnap_before = _osnap(self.state)
        _rsnap_before = _rsnap(self.state)
        E.apply_option(self.state, o, self.rng, slots, card=card)
        self.state["cooldown"][card["id"]] = int(card.get("cooldown", 3))
        self.pending = None
        self.queue.pop(0)
        body = [x for x in [self._fill(o.get("note", ""), slots)] if x]
        if not body:
            # 选项没写 note：退到 desc，别给一屏只有标题的回执
            body = [x for x in [self._fill(o.get("desc", ""), slots)] if x]
        reply = self._rq_reply(card, o, slots)
        if reply:
            body.insert(0, reply)
        # 同 choose_card：回复插队首，选完立刻看到
        self.queue.insert(0, {"type": "receipt", "title": self._fill(o.get("label", ""), slots),
                   "body": body, "delta": _delta(before, self.state),
                   "sticks": _sticks(_osnap_before, self.state),
                   "mates": _mates_changed(_rsnap_before, self.state),
                   "face": self._face(card, slots)})
        self.after_step()

    def _journal_week(self, week):
        """每周末记一行「历史大事」的底账；只记真发生过的值。"""
        s = self.state
        line = E.mainline(s) or ""
        st = (s.get("story") or {}).get(line) or {}
        row = {
            "week": int(week),
            "stage": round(s["stage"]),
            "tier": E.tier_name(s["stage"]),
            "psyche": round(s["psyche"]),
            "money": round(s["money"]),
            "enjou": round(s["enjou"]),
            "banzi": round(s["banzi"]),
            "kaibox": round(s["kaibox"]),
            "template": round(s["template"], 2),
            "truth_rate": round(E.truth_rate(s), 2),
            "relavg": round(E.relavg(s)),
            "line": line,
            "line_stage": int(st.get("stage", -1)),
            "shiren_stage": int(((s.get("story") or {}).get("shiren") or {}).get("stage", -1)),
            "rent_missed": bool(s.get("rent_missed")),
            "chose_leave": bool(s.get("chose_leave")),
            "offer_refused": s.get("offer_choice") == "refuse",
        }
        log = s.setdefault("log", [])
        if log and log[-1].get("week") == week:
            log[-1] = row
        else:
            log.append(row)

    def settle_week(self):
        s = self.state
        if s.get("_settled_week") == s["week"]:
            # 这一周已经结算过了（特典卡被打断或多点了一次），别再推一次
            return
        s["_settled_week"] = s["week"]
        before = _snap(s)
        _osnap_before = _osnap(s)
        _rsnap_before = _rsnap(s)
        # 一周的券全部加总（每场各自记账，state 里累加；旧档没有累计时退回单场账）
        income = s.get("_week_income", 0)
        tickets = s.get("_week_tickets", 0)
        if income == 0 and tickets == 0:
            bill = self._bill or B.weekly_bill(s, E.warm_ota(s))
            income = bill["yen"]
            tickets = bill["tickets"]
        fee = 160 if s["week"] == 1 else 620
        s["money"] += income - fee
        if s["money"] < 0:
            s["psyche"] -= 10; s["stamina"] -= 5; s["money"] = 0
        s["_income_last"] = income
        if income >= 560:
            s["psyche"] += 2
        if income < 240:
            s["low_income_weeks"] = s.get("low_income_weeks", 0) + 1
            s["psyche"] -= 6
        E.clamp(s)
        # 延迟后果：卡面上写「下周 / 下个月」的，到了就结（这条原来只在引擎跑局里生效，
        # 界面上写了「下周」却什么都不会发生——玩家当然会觉得选项没后果）
        born = E.settle_delayed(s, self.world, self.rng)
        E.cool_down(s)
        E.clamp(s)
        self._journal_week(s["week"])
        _done_week = s["week"]
        _body = ["一共卖出 %d 张券，进账 %d 块；场租和分成 %d 块。"
                 % (tickets, round(income), fee)]
        if born:
            _body.append("她把朋友带来了：%s。" % "、".join(born))
        panel = {"type": "panel", "title": "第 %d 周结算" % _done_week,
                 "body": _body,
                 "delta": _delta(before, s), "kind": "week"}
        self._bill = None
        # 先把周号推上去，再 push 结算屏：after_step 靠
        # _settled_week == week 判断「这一周收完了」，顺序反了会连着结算到季末。
        s["week"] = _done_week + 1
        s["_settled_week"] = _done_week
        for o in s["ota"]:
            o["weeks_known"] += 1
        # 结算屏放在最前面；它后面接哪一格，等玩家按「继续」时 after_step 再决定
        self.push(panel)

    def _before_finish(self):
        self.after_step()

    def start_week(self):
        """新的一周：先排周初那几屏，再让 step_week 排剩下的。"""
        s = self.state
        self.acts_done = 0
        self.wk = {"act": 0, "mid": 0, "fri": 0, "sat_act": 0, "sat": 0,
                   "bill": 0, "sun": 0, "bill2": 0, "sun_talk": 0,
                   "events": [], "extra": [], "talk": None}
        s["_extra_cards"] = 0
        s["_gap_done"] = -1
        s["_mid_done"] = False
        rent = "，这周还要交 %d 块房租" % E.RENT if s["week"] % 2 == 1 else ""
        body = ["六天晚上，周五、周六各一场 live。手里还剩 %d 块%s。"
                % (round(s["money"]), rent)]
        self.push({"type": "text", "title": "第 %d 周" % s["week"], "body": body})
        if s["week"] % 2 == 1 and s["money"] < E.RENT:
            s["psyche"] -= 18
            s["stamina"] -= 10
            s["rent_missed"] = True
            E.clamp(s)
            self.push({"type": "receipt", "title": "房租没交上",
                       "body": ["房东在门口站了一会儿，没说话。这天晚上我在排练室的沙发上睡的。"],
                       "delta": {"psyche": -18, "stamina": -10}})
        st = self._maybe_story()
        if st:
            self.push(st)

    def _start_week(self):
        """新的一周：周初那几屏 + 房租 + 这一周的剧情线那一拍。

        不在这里调 after_step——周流程是 after_step 自己循环推的，这里排完就返回。"""
        s = self.state
        # 「这一周已经开过头」的标记在这里落库：set_name / startWeekNext 会直接
        # 调 _start_week，不走 after_step 的守卫——以前只有守卫那一侧置位，
        # 每个新档第 1 周都会开两次周（两张「第 1 周」屏、两次剧情骰），
        # 房租真扣款之后，第二次开局还会拿扣完的钱误判「房租没交上」。
        s["_week_started"] = s["week"]
        s["_week_tickets"] = 0
        s["_week_income"] = 0
        self.acts_done = 0
        self.wk = {"act": 0, "mid": 0, "fri": 0, "sat_act": 0, "sat": 0,
                   "bill": 0, "sun": 0, "bill2": 0, "sun_talk": 0,
                   "events": [], "extra": [], "talk": None}
        s["_extra_cards"] = 0
        s["_gap_done"] = -1
        s["_mid_done"] = False
        # 推线周期号要跟着周走：`_this_week` 比的是「本周有没有推过这条线」，
        # 而 tick 以前只在抽到线之后才更新，于是上周推过的那条线这周开头就被误判成
        # 「本周已推」，`line_stage` 直接返回 None——私联从此再也轮不到，8 周只走一拍。
        s["_line_tick"] = s["week"]
        # 房租：交得起就真扣。交不上才是下面那套惩罚。
        rent_paid = False
        if s["week"] % 2 == 1 and s["money"] >= E.RENT:
            s["money"] -= E.RENT
            rent_paid = True
        rent = ""
        if s["week"] % 2 == 1:
            rent = "，房租已经交了" if rent_paid else "，这周还要交 %d 块房租" % E.RENT
        body = ["六天晚上，周六、周日各一场 live。手里还剩 %d 块%s。"
                % (round(s["money"]), rent)]
        self.push({"type": "text", "title": "第 %d 周" % s["week"], "body": body})
        if s["week"] % 2 == 1 and not rent_paid:
            s["psyche"] -= 18
            s["stamina"] -= 10
            s["rent_missed"] = True
            E.clamp(s)
            self.push({"type": "receipt", "title": "房租没交上",
                       "body": ["房东在门口站了一会儿，没说话。这天晚上我在排练室的沙发上睡的。"],
                       "delta": {"psyche": -18, "stamina": -10}})
        # 末周开头：「收场」就是那一晚。越了线就必到，不等 stage4 走完。
        if E.shiren_finale_ready(s, self.world):
            self._begin_finale()
            return
        # 末周开头：恋爱线还没到收场，就把「那一晚」排上（不再等 stage4 走完）。
        _force = (E.mainline(s) == "romance"
                  and int(((s.get("story") or {}).get("romance") or {}).get("stage", -1)) < 4
                  and s["week"] >= int(s.get("weeks_total") or 8))
        st = self._maybe_story(force_finale=_force)
        if st:
            self.push(st)

    # ---------- 私联终局：收场 ----------
    def _begin_finale(self):
        """末周开头把「收场」排上：先一句前夜的话，然后是三问。"""
        s = self.state
        # 方案A：拷问走私联独立通道，只从她自己随口说过的小事出题。
        # 真值在 protagonist() 里已预锁（她说的=拷问问的=判对的同一个值），
        # 不再需要「收场前临时补三条线索」那一段——那正是线索突兀的根源。
        quiz = E.shiren_finale_quiz_cards(s, self.world, self.rng, 3)
        s["_finale"] = {"phase": "intro", "quiz": quiz,
                        "idx": 0, "ok": 0, "total": len(quiz)}
        ln = E.shiren_line(self.world) or {}
        fin = ln.get("finale") or {}
        slots, _ta = self._finale_slots()
        intro = self._fill(fin.get("intro") or "", slots)
        body = [intro] if intro else ["场馆空着，灯只开了一半。"]
        self.push({"type": "text", "title": "收场", "body": body})

    def _after_finale(self):
        """终局进行到哪一步了。返回 True 表示这一步已经排了新屏。"""
        s = self.state
        fin = s.get("_finale")
        if not fin or self.queue:
            return False
        phase = fin.get("phase")
        if phase in ("intro", "quiz"):
            return self._push_finale_quiz()
        if phase == "outcome":
            return self._push_finale_choices()
        if phase == "collapse":
            return self._push_collapse()
        if phase == "done":
            s.pop("_finale", None)
            # 收场走完，这一季就到这里。以前是走完继续过日子、拖到第 8 周结算，
            # 但 13「用完」/14「唯一」的正文写的是「你在第 X 周走到了这里 / 剩下的周没有发生」，
            # 所以这里必须真的提前结束，不能空着那几周再判。
            self._finish()
            return True
        return False

    # ---------- 断联之后的失控 ----------
    def _collapse_script(self):
        """断联之后那几分钟。

        她要的是「我控制不了」，所以这里不写选项、不给按钮：
        `auto` 标记让前端自己往下翻，玩家只能看着。炎上和板子一路涨到 999，
        最后进「控制不了」结局。

        这一段不是「我没能让她停」，而是「原来我不止她一个」——
        前面一整季玩家只看见一个人，崩溃的时候才发现自己攒了一本账。
        甜是先发生在屏幕外的，这里只用一屏一屏把账翻出来。

        数字不是一口气跳上去的——一屏一屏涨，玩家才会觉得事情在滑走。
        """
        s = self.state
        who = s.get("_collapse_who") or "她"
        return [
            {"title": "", "auto": True, "body": [
                "我说完那句话就回家了。那天晚上睡得很沉，心想这件事总算处理干净了。"]},
            {"title": "", "auto": True, "body": [
                "第四天晚上，板子上出现了一条帖子，标题只有三个字：想聊聊。",
                "我以为是%s。点进去，第一行写着：「周三那次，你也是这么跟我说的。」" % who],
             "bump": {"enjou": 60, "banzi": 40}},
            {"title": "", "auto": True, "body": [
                "周三。我在心里过了一遍周三，是空的。",
                "第二条帖子是周六发的：「你说，只有我听得懂。」我也想不起自己说过。"]},
            {"title": "", "auto": True, "body": [
                "她们开始对句子。同一句「你是特别的」，出现了三次，落款是三个人。",
                "有人把截图按日期排开，三行字一模一样，连标点都没差。"],
             "bump": {"enjou": 130, "banzi": 110}},
            {"title": "", "auto": True, "body": [
                "我翻自己的聊天记录。有几段话完全没有印象，语气却确实是我的。",
                "同一个晚上，同一个地址，我发给了三个人。间隔十七分钟。"]},
            {"title": "", "auto": True, "body": [
                "她们开始对照片。同一张拍切，裁掉不同的人，发给不同的人。",
                "有人问：这张到底拍的是谁。没有人回答。"],
             "bump": {"enjou": 180, "banzi": 190}},
            {"title": "", "auto": True, "body": [
                "运营的电话是晚上打来的。他没有问是不是真的。",
                "他问：到底几个。"]},
            {"title": "", "auto": True, "body": [
                "我张了一下嘴，发现说不出准确的数。",
                "那一刻我才意识到，我连自己都骗过去了。"],
             "bump": {"enjou": 220, "banzi": 240}},
            {"title": "", "auto": True, "body": [
                "第二天早上，热搜第三，第二，第一。",
                "标题里那句是她们中一个人写的：她好像对每个人都这样。"]},
            {"title": "", "auto": True, "body": [
                "群里没有人问我。小满发了一句「我们先别说话」。露露退群了。"],
             "bump": {"enjou": 250, "banzi": 300}},
            {"title": "", "auto": True, "body": [
                "傍晚，场地退了，票全退。我坐在空的列里，把版聊往上翻。",
                "翻到最早那条，她说：你是第一个记住我名字的人。我盯着这句话，想不起来是哪一个。"]},
            {"title": "", "auto": True, "body": [
                "她们还在对日子。第四十七个。落款一栏排得很整齐。",
                "我数到第四十七个，停住了。第四十八个是谁，我到现在也没想起来。"],
             "bump": {"enjou": 999, "banzi": 999}},
        ]

    def _push_collapse(self):
        """排失控演出的下一屏。演完就把这一季收掉。"""
        s = self.state
        fin = s.get("_finale") or {}
        idx = int(fin.get("cidx") or 0)
        script = fin.get("script") or []
        if idx >= len(script):
            # 演完了：这里必须直接收场。若只把 phase 改成 done 就返回，
            # after_step 会接着 step_week() 把这一周过下去，失控就成了插曲。
            s.pop("_finale", None)
            self._finish()
            return True
        row = script[idx]
        fin["cidx"] = idx + 1
        s["_finale"] = fin
        step = {"type": "text", "title": row.get("title") or "",
                "body": list(row.get("body") or []), "auto": True, "cidx": idx}
        if idx == 0:
            step["collapse_start"] = True
        bump = row.get("bump") or {}
        if bump:
            # 这里不能走 apply_effect：它末尾会 clamp，而 clamp 本来会把
            # 炎上/板子削回 100。断联之后这两个数不归那套规矩管（见 engine.clamp）。
            # 顶端仍是 999——一路涨上去，涨到顶就停在那儿。
            delta = {}
            for k, v in bump.items():
                old = s.get(k, 0)
                new = min(999, old + v)
                s[k] = new
                delta[k] = new - old
            step["delta"] = delta
        self.push(step)
        return True

    def _finale_slots(self):
        ta = self._line_slots("shiren", {}).get("ta")
        return ({"ta": ta, "speaker": ta} if ta else {}), ta

    def _push_finale_quiz(self):
        s = self.state
        fin = s.get("_finale") or {}
        quiz = fin.get("quiz") or []
        idx = int(fin.get("idx") or 0)
        slots, ta = self._finale_slots()
        if idx < len(quiz):
            fin["phase"] = "quiz"
            s["_finale"] = fin
            card = quiz[idx]
            step = self._render_card(card, slots)
            step["face"] = (ta or {}).get("name") or "特典会"
            step["_card"] = card
            step["_slots"] = slots
            step["finale_quiz"] = True
            self.push(step)
            return True
        # 答完了：判成绩，写成一句能看懂的话
        n_ok = int(fin.get("ok") or 0)
        n_all = len(quiz)
        key, _ok = E.apply_finale_outcome(s, n_ok, n_all)
        fin["phase"] = "outcome"
        fin["key"] = key
        fin["ok_quiz"] = bool(_ok)   # 答上了才有得选，答错直接收场
        s["_finale"] = fin
        ln = E.shiren_line(self.world) or {}
        note = ""
        for oc in ((ln.get("finale") or {}).get("outcomes") or []):
            if oc.get("id") == key:
                note = oc.get("note") or ""
                break
        if n_all:
            head = "她一共问了我 %d 件小事，我答上了 %d 件。" % (n_all, n_ok)
        else:
            head = "她问的那些，我一件都说不上来。"
        body = [head]
        if note:
            body.append(note)
        self.push({"type": "text", "title": "她问完了", "body": body})
        return True

    def _finale_choices_card(self):
        """答对了才问这一句：接下来，你想怎么办。

        以前这里直接把 storyline 里那四条抄出来（公开/断联/沉沦/划边界），
        四条都只改资源，不改结局——玩家选完，结局早在答题那一刻定死了。
        现在只剩两条，而且它们真的通向不同的地方。"""
        return {
            "id": "finale_choice",
            "type": "私联恋爱",
            "title": "收场",
            "_meta": {"finale_choice": True},
            "narrative": "台上那一晚还没到。最后一场之前，我得决定这件事往哪放。",
            "options": [
                {"id": "sink", "label": "就这么下去",
                 "desc": "不公开，也不断。当它没有尽头",
                 "note": "我没有回那条消息，也没有不回。第二天她照常坐在列里等我。",
                 "immediate": {"psyche": 4, "kaibox": 10, "enjou": 6}},
                {"id": "cut_clean", "label": "跟她说清楚，以后别来了",
                 "desc": "把线剪干净，各自回到岸上",
                 "note": "我打了一大段，删了，又打了一段。最后发出去的是最短的那句。",
                 "immediate": {"psyche": -8, "kaibox": -14, "shiroi": -10}},
            ],
        }

    def _push_finale_choices(self):
        s = self.state
        fin = s.get("_finale") or {}
        # 答错了就没有这一屏：直接往「用完」走，别给一个选不了任何事的选项。
        if not fin.get("ok_quiz"):
            fin["phase"] = "done"
            s["_finale"] = fin
            return False
        card = self._finale_choices_card()
        fin["phase"] = "choices"
        s["_finale"] = fin
        slots, ta = self._finale_slots()
        step = self._render_card(card, slots)
        step["face"] = (ta or {}).get("name") or "特典会"
        step["_card"] = card
        step["_slots"] = slots
        step["finale_choice"] = True
        self.push(step)
        return True

    def _shiren_if_crossed(self):
        """越了线之后，私联就一周推一拍，不再等骰子。

        以前这里只在「按剩余周数算，再不推就来不及」时才插队，其余周仍走
        正常抽卡（2.6 倍权重）。结果越线早的档，中间几周可能一次都抽不到，
        玩家看到的是「刚加微信，下一屏就是决赛前夜」。这条线一旦开始就是我
        过的另一种日子，拍数又固定 5 拍，所以只要主线已经落在私联，就每周
        强推；主线还没定给别人、或已经走到裂痕，`line_stage` 会自己返回空。"""
        s = self.state
        if "crossed_line" not in (s.get("flags") or set()):
            return None
        main = E.mainline(s)
        if main and main != "shiren":
            return None                        # 这一季走的是别的线，私联不再出现
        ln = E.shiren_line(self.world)
        if ln is None or E.line_locked(s, ln):
            return None
        st = E.line_stage(s, ln)
        if st is None:
            return None
        return ln, st

    def _romance_if_main(self):
        """恋爱线一旦成了这一季的主线，就一周推一拍，不再等骰子。

        以前只靠 draw_line 的 45% 落率，八周里经常只轮到两三拍，
        玩家还没走到「确认」就季末了。"""
        s = self.state
        if E.mainline(s) != "romance":
            return None
        ln = E.romance_line(self.world)
        if ln is None or E.line_locked(s, ln):
            return None
        st = E.line_stage(s, ln)
        return (ln, st) if st else None

    def _maybe_romance_talk(self):
        """「谈一谈」独立幕：确认关系后、还没做过一次性表态时，每周开头来问一次。
        选「再等等/逃避」只攒 risk，下周照问（越拖越勤）；选「公开/只看当下」收下表态，不再问。
        不占抽线骰子、不写 story 进度；末周 force_finale 时跳过它，直接推收场。"""
        s = self.state
        if E.mainline(s) != "romance":
            return None
        fl = s.get("flags") or set()
        if "romance_confirmed" not in fl:
            return None
        # 表过态就不再问（公开 / 只看当下，都是一次性收下）
        if "romance_public_intent" in fl or "romance_now_intent" in fl:
            return None
        # 每周最多问一次
        if int(s.get("_rtalk_week", -1)) == int(s.get("week", 0)):
            return None
        ln = E.romance_line(self.world)
        if ln is None or E.line_locked(s, ln):
            return None
        talks = ln.get("talks") or []
        if not talks:
            return None
        # 三变体轮换：尽量不接着问同一张
        last = s.get("_last_rtalk", "")
        pool = [t for t in talks if t.get("id") != last]
        talk = self.rng.choice(pool if pool else talks)
        s["_last_rtalk"] = talk.get("id")
        slots = {"ta": {"name": "阿棠"}}
        pending = ("rtalk", talk, slots)
        body = [self._fill(talk.get("narrative", ""), slots)]
        return {
            "type": "card",
            "rtalk": True,
            "title": self._fill(talk.get("title", ""), slots),
            "face": slots["ta"]["name"],
            "speaker": slots["ta"]["name"],
            "compact": True,
            "body": body,
            "options": [{"id": o["id"], "label": self._fill(o["label"], slots),
                         "desc": self._fill(o.get("desc", ""), slots)}
                        for o in (talk.get("options") or [])],
            "_rtalk": pending,
        }

    def choose_romance_talk(self, oid):
        """「谈一谈」那张卡的落子：收下表态或只攒一点 risk。"""
        if not self.pending:
            return self.advance()
        _, talk, slots = self.pending
        o = next(x for x in talk["options"] if x["id"] == oid)
        s = self.state
        before = _snap(s)
        E.apply_option(s, o, self.rng, slots, card=talk)
        # 关键：apply_option 只把 flag 塞进 s["flags"]，risk 的数值累积在 apply_story_flags 里
        E.apply_story_flags(s, o)
        s["_rtalk_week"] = s["week"]
        E.clamp(s)
        self.pending = None
        self.queue.pop(0)
        body = [x for x in [self._fill(o.get("note", ""), slots)] if x]
        if not body:
            body = [x for x in [self._fill(o.get("desc", ""), slots)] if x]
        self.push({"type": "receipt", "title": self._fill(o.get("label", ""), slots),
                   "body": body, "delta": _delta(before, s),
                   "face": (slots.get("ta") or {}).get("name", "阿棠")})
        self.after_step()

    def _maybe_story(self, force_finale=False):
        """每周开头先问一句：这一周有没有哪条线在走。

        以前这里的 `_story_try` 两周共用一次拦截（_build_weekday2 会调它，
        choose_story 收尾也调它），结果排完动作那一周就再也推不动线——
        一周也推进不了。现在只由每周开头那一次调用决定，本函数不自锁。"""
        s = self.state
        # 「谈一谈」是独立通道：不占每周抽线的骰子，也不写 story 进度。
        if not force_finale:
            rtalk_step = self._maybe_romance_talk()
            if rtalk_step is not None:
                return rtalk_step
        line = None
        forced = False
        if force_finale:
            # 末周兜底：恋爱线还没走到收场，也把「那一晚」排上。
            ln = E.romance_line(self.world)
            if ln is not None:
                st = next((x for x in ln["stages"] if int(x["stage"]) == 4), None)
                if st is not None:
                    line = (ln, st)
                    forced = True
        else:
            line = self._shiren_if_crossed()
            forced = line is not None          # 私联进度落后：不等骰子
            if line is None:
                line = self._romance_if_main()
                forced = line is not None
        if line is None:
            line = E.draw_line(s, self.world, self.rng)
        if line is None:
            return None
        if not forced and self.rng.random() > self.LINE_CHANCE:
            return None
        lid, st = line
        lid_id = lid["_meta"]["id"]
        v = None
        if lid_id == "romance" and st["stage"] == 4:
            # 收场这一晚会不会被人撞破：不再一票否决，按「意图 + 攒下的 risk」掷一次骰。
            # 公开意图 = 本来就打算摊开，几乎不怕被看见（risk 攒够才有一点风声）；
            # 只想顾当下 / 一直没表态 = 越拖越悬，risk 越高越容易被推开门。
            fl = s.get("flags") or set()
            risk = max(0, int(float(s.get("romance_risk") or 0)))
            if "romance_public_intent" in fl:
                caught_pct = 20 if risk >= 3 else 0
            elif "romance_now_intent" in fl:
                caught_pct = min(90, 60 + 10 * risk)
            else:
                caught_pct = min(90, 50 + 15 * risk)
            if self.rng.random() * 100 < caught_pct:
                v = next((x for x in st["variants"] if x["id"] == "finale_caught"), None)
        if v is None:
            # 同一拍隔两周再回来时，尽量换一张没演过的：
            # 玩家推开的那个选项不该让同一张卡原地重播（「又遇到第一拍」）。
            seen = (s.get("_line_seen") or {}).get(lid_id) or []
            pool = [x for x in st["variants"] if x["id"] not in seen] or st["variants"]
            v = self.rng.choice(pool)
            s["_line_seen"] = s.get("_line_seen") or {}
            s["_line_seen"][lid_id] = (seen + [v["id"]])[-8:]
        lid_id = lid["_meta"]["id"]
        s["_line_tick"] = s["week"]
        s["_story_try"] = s["week"]
        s["_line_week"] = s.get("_line_week") or {}
        E._remember_chaser(s, lid, v, self.rng)
        slots = self._line_slots(lid_id, v)
        pending = ("line", lid_id, st, v, slots)
        self.pending = pending
        return {
            "type": "card",
            "line": True,
            "line_name": self._line_name(lid_id),
            "_line": pending,
            "face": ("、".join([o["name"] for o in slots.values() if o and o.get("name")])
                     or {"shiren": "特典会", "zhong": "散场以后", "romance": "排练室"}.get(lid_id, "")),
            "title": self._fill(v.get("title", ""), slots),
            "body": [self._fill(v.get("narrative", ""), slots)],
            "options": [{"id": o["id"], "label": self._fill(o["label"], slots),
                         "desc": self._fill(o.get("desc", ""), slots)}
                        for o in v["options"]],
        }

    @staticmethod
    def _line_name(lid):
        return {"shiren": "私联", "zhong": "重线", "romance": "恋爱"}.get(lid, "")

    def _confess_step(self, slots):
        """私联踩空后她又发来的那条私信。带选项，回/冷/推开各有代价。

        卡库里 type=私联表白 的卡 gate 恒假，永远不会进普通抽卡池，只从
        这里显式推。三张轮换，尽量不连着发同一张（记 _last_confess）。
        """
        s = self.state
        cards = [c for c in self.world.get("cards", []) if c.get("type") == "私联表白"]
        if not cards:
            return None
        last = s.get("_last_confess")
        pool = [c for c in cards if c.get("id") != last] or cards
        card = self.rng.choice(pool)
        s["_last_confess"] = card.get("id")
        step = self._render_card(card, slots)
        step["_card"] = card
        step["_slots"] = slots
        step["face"] = ((slots or {}).get("ta") or {}).get("name") or "版聊"
        return step

    def _line_slots(self, lid, v):
        """剧情线里 {{ta}} 是谁：重线跟着「一直来的那个人」，私联/恋爱各有自己的对象。"""
        s = self.state
        ta = None
        if lid == "zhong":
            cid = s.get("_chaser")
            if not cid and s.get("ota"):
                # 高黏性里随机挑，不再固定 max(stick)——否则永远同一个人。
                pool = [o for o in s["ota"] if not o.get("is_storyline")]
                pool = sorted(pool, key=lambda o: -float(o.get("stick") or 0))[:3]
                if pool:
                    cid = self.rng.choice(pool)["id"]
                    s["_chaser"] = cid
            ta = next((o for o in s["ota"] if o["id"] == cid), None)
        elif lid == "romance":
            ta = {"name": (v.get("partner") or "阿棠")}
        elif lid == "shiren":
            # 私联对象从现有高黏性 OTA 里挑一个「不会走的」，整季固定。
            ta = E.protagonist(s, self.world, self.rng)
        if ta is None and s.get("ota"):
            pool = [o for o in s["ota"] if not o.get("is_storyline")]
            pool = sorted(pool, key=lambda o: -float(o.get("stick") or 0))[:3]
            if pool:
                ta = self.rng.choice(pool)
        return {"ta": ta} if ta else {}

    def choose_story(self, oid):
        s = self.state
        if not self.pending or self.pending[0] != "line":
            return self.advance()
        lid_id, st, v, slots = self.pending[1], self.pending[2], self.pending[3], self.pending[4]
        o = next(x for x in v["options"] if x["id"] == oid)
        before = _snap(s)
        _osnap_before = _osnap(s)
        _rsnap_before = _rsnap(s)
        _snapv = {k: s.get(k, 0) for k in ("zhong", "zhongs", "heat", "heart")}
        s["_line_tick"] = s["week"]
        E.apply_option(s, o, self.rng, slots, card=None)
        # 她讲出来的事：这一拍 `learns` 里写的东西，从此算「你知道」。
        # 以前引擎根本不读 learns，所以 {{cat_name}}/{{home}} 这类全是空的。
        E.learn_memory(s, o.get("learns"), o.get("note") or "")
        # 那些「选了就真的有事发生」的旗标：断线、被记住家在哪、
        # 官方辟谣反而坐实、答应过的话被截图……
        E.apply_story_flags(s, o)
        # 推进量在引擎这一层补：选项一般只写「她攒下的」，不写「重线进度」
        if (_snapv["zhong"] or 0) >= (s.get("zhong") or 0):
            s["zhong"] = (_snapv["zhong"] or 0) + 1
        # 私联看选项的 advance：答应了、去了、回了，才算往前走一步。
        # 以前这里是 `0 >= 0` 恒真，连「当晚就跟她说以后别来了」也照样 +1，
        # 与 design_note 的「冷淡则卡住甚至断线」正好相反。
        if lid_id == "shiren" and o.get("advance") and (_snapv["heat"] or 0) >= (s.get("heat") or 0):
            s["heat"] = (_snapv["heat"] or 0) + 1
        if lid_id == "romance" and o.get("advance") and (_snapv["heart"] or 0) >= (s.get("heart") or 0):
            s["heart"] = (_snapv["heart"] or 0) + 1
        if lid_id == "zhong":
            s["shiroi"] = float(s.get("shiroi") or 0) + (12 if st["stage"] >= 3 else 8)
        if lid_id == "shiren":
            s["kaibox"] = float(s.get("kaibox") or 0) + 4
        # 只有真的往前走了一拍才记进度：重线的选项没有 advance（怎么答都压过来），
        # 另外两条要看选项。没推进就别写 story——否则私联「半开一扇门」也会
        # 留下一条 stage 0 的记录，可能被兜底选成主线，而它永远迈不出下一步。
        confessed = False
        if lid_id == "zhong" or o.get("advance") or st["stage"] >= 4:
            # 收场拍（stage 4）的选项都不带 advance（它不再「往前走」），
            # 但这一拍本身必须记下来，否则末周会反复排「决赛前夜」。
            s["story"][lid_id] = {"stage": st["stage"]}
        elif lid_id == "shiren":
            # 私联踩空：不写进度、也不加冷却。她会再发一条私信表白过来。
            # 一直不往前，她就一直表白——卡库里三张轮换，回/冷/推开各有代价。
            confessed = True
        s["_line_week"] = s.get("_line_week", {})
        s["_line_week"][lid_id] = s["week"]
        E.clamp(s)
        self.pending = None
        self.queue.pop(0)
        body = [x for x in [self._fill(o.get("note", ""), slots)] if x]
        if not body:
            body = [x for x in [self._fill(o.get("desc", ""), slots)] if x]
        self.push({"type": "receipt", "title": self._fill(o.get("label", ""), slots),
                   "body": body, "delta": _delta(before, s)})
        # 被撞破 / 当场公开 / 重线那句「全都告诉她」：这一季到此为止，不拖到季末。
        # final_intimate 以前只写 flag、要等 judge，结果第 5 周就能触发的
        # 「我只是太爱你了」被硬拖到第 8 周——和恋爱线撞破是同一个问题。
        if set(o.get("flags") or []) & {"romance_caught", "romance_public", "final_intimate"}:
            self._finish()
            return
        # 这一拍踩空了（拒绝、把线关了）：这条线安静两周
        closed = "line_closed" in (o.get("flags") or []) or "romance_giveup" in (o.get("flags") or [])
        if closed:
            E.line_cool(s, lid_id, 2)
        # 私联踩空且没有明确断线：她又发来一条私信表白。插到队首，立刻成为下一屏。
        # 一直不往前就一直表白（三张轮换），而不是同一拍换卡重播。
        if confessed and not closed:
            step = self._confess_step(slots)
            if step:
                self.push_front(step)
        self.after_step()

    def _resume_live(self):
        """周六这一格已经排过、但还没结算：把剩下的那一格补上，不重放演出。"""
        self.after_step()


    def _finish(self):
        s = self.state
        self._journal_week(s.get("week") or 1)
        # 「再跳一场」：没选离开、一路演到季末 = last_live。以前只有离线 do_week
        # 会置位，线上永远拿不到彗星（判定恒 False，图鉴永远锁死）。
        if not s.get("chose_leave"):
            s["last_live_choice"] = True
        name, is_early = E.judge(s, self.world, None)
        s["ending"] = name
        self.over = True
        text = self.ending_text(name)
        self.push({
            "type": "end",
            "title": name,
            "ending": name,
            "early": bool(is_early),
            "echo": self._echo(),
            "outside": self.outside,
            "body": [text] if text else ["（这个结局的正文还没写进来。）"],
        })

    def _echo(self):
        """结局那一屏底下「这一季的回响」：只报这一局真发生过的数，不写攻略。"""
        s = self.state
        snap = self.snapshot() or {}
        stats = snap.get("stats") or {}
        tp = int(s.get("truth_pick") or 0)
        sp = int(s.get("safe_pick") or 0)
        picked = tp + sp
        stage = round(E.stage_score(s), 1)
        return {
            "week": int(s.get("week") or 0),
            "stage": stage,
            "tier": E.tier_name(round(E.stage_score(s))),
            "psyche": round(s.get("psyche", 0)),
            "money": round(s.get("money", 0)),
            "enjou": round(s.get("enjou", 0)),
            "kaibox": round(s.get("kaibox", 0)),
            "line": s.get("_mainline") or "",
            "truth_pick": tp,
            "safe_pick": sp,
            "truth_rate": round(tp / picked, 2) if picked else None,
            "clues": int(stats.get("clues") or 0),
            "clues_wrong": int(stats.get("clues_wrong") or 0),
            "pushed": int(stats.get("pushed") or 0),
            "rent_missed": bool(s.get("rent_missed")),
            "chose_leave": bool(s.get("chose_leave")),
            "offer_refused": bool(s.get("offer_refused")),
            "shiren_stage": int(((s.get("story") or {}).get("shiren") or {}).get("stage", -1)),
            "stance": s.get("stance") or "",
            "stance_name": s.get("stance_name") or "",
        }

    @staticmethod
    def ending_text(name):
        """从 结局.md 里抠出某一段正文。找不到就返回空，界面只显示结局名。"""
        path = os.path.join(DATA, "..", "结局.md")
        if not os.path.isfile(path):
            return ""
        with open(path, encoding="utf-8") as f:
            src = f.read()
        import re
        # 章节：## N · 名字 … 直到下一个 ## 或文末
        blocks = re.split(r"\n(?=##\s)", src)
        for b in blocks:
            head = b.split("\n", 1)[0]
            if name and name in head:
                m = re.search(r"\*\*正文\*\*\s*\n(.*?)(?=\n\*\*|\Z)", b, re.S)
                if m:
                    t = m.group(1).strip()
                    return re.sub(r"\n{3,}", "\n\n", t)
                # 有的结局（如散场）把正文直接写在 **内核** 后面，没有 **正文** 标题
                m = re.search(r"\*\*内核\*\*[:：].*?\n\s*\n(.*?)(?=\n\*\*|\Z)", b, re.S)
                if m:
                    t = m.group(1).strip()
                    return re.sub(r"\n{3,}", "\n\n", t)
        return ""


def auto_play(seed=0, n_weeks=1, log=False):
    """自动走 n_weeks 周（随机选项），给平衡测试用。"""
    g = Game(seed=seed)
    g.advance(); g.advance()
    g.choose_intro(g.rng.choice([c["id"] for c in g.intro["choices"]]))
    g.advance(); g.advance()
    g.set_name("小夏")
    guard = 0
    while g.state["week"] <= n_weeks and guard < 500:
        guard += 1
        cur = g.current()
        if cur is None:
            break
        t = cur["type"]
        if t in ("text", "live", "receipt", "panel"):
            g.advance()
        elif t == "choice" and cur.get("kind") == "act":
            g.choose_act(g.rng.choice([o["id"] for o in cur["options"]]))
        elif t == "card":
            g.choose_card(cur["options"][0]["id"]) if not hasattr(g, "_pending_week_settle") \
                else g.choose_talk(cur["options"][0]["id"])
        else:
            break
    return g


if __name__ == "__main__":
    gg = auto_play(seed=1, n_weeks=1)
    print(gg.snapshot())
