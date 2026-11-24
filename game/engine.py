# -*- coding: utf-8 -*-
"""《聚场》纯逻辑引擎（第一版，无界面）。
目标：把 data/ 里的卡库、剧情线、回考线索、序章、判决表跑起来，支持自动跑局看结局分布。

设计约定
--------
* 资源键（与剧本一致）：money stamina psyche fame stage dance sing mc
  enjou kaibox banzi shiroi shiren template relavg + relation_A/B/C + 动态 OTA 槽
* 槽位键（@xxx）：把效果挂到本卡 casting 选出的某个 OTA 身上；`ota_all` 才是全体。
* 状态：`S` 字典 + `S['ota']` 是 OTA 对象列表（id/stick/archetype/fan_type/gender/...）。
* 抽卡：三层 —— 硬闸门（gate 表达式的子集）→ 权重 → cooldown。
* 剧情线：按 gate 推进，一拍一变体；选完写 flags + delayed。
* 结局：读 data/endings.json 的 flow；提前结束读 early[].trigger.flag。
* 随机：全部走传入的 random.Random 实例，种子可复现。

已知未实现（第一版故意留白，见 CODE_PLAN.md）
----------------------------------------------
* 「曾冷场或翻车」「曾欠队友人情」「舞台翻车」已接到真实状态：blew_it（冷场/翻车）、
  owe_team（甩锅给队友）。「下次体力<30」这类预告型 gate 仍先当 False。
* 回考第二拍的三选一：本版按 65% 蒙对/答对处理，不读玩家的记忆（等界面来）。
* 抽卡另有一层「这一季见过的卡降权 ×0.25」：靠 loop.py 上屏登记的 s["seen"]，
  不硬禁，目的是压住低门槛卡反复抽、让一季里能多见到几张不同的卡。
"""
import json, os, random, math, re

DATA = r"C:\Users\kk\Documents\deepseek-harness\default-workspace\聚场\data"

BAD = {"enjou", "kaibox", "banzi", "shiroi"}   # 越高越糟


# ---------------------------------------------------------------- 读取数据
def _load(name):
    with open(os.path.join(DATA, name), encoding="utf-8") as f:
        return json.load(f)


_MEM = None


def _memory():
    """ota_memory.json 的线索表（key -> clue 那条）。回考的真值要从 set 里抽。"""
    global _MEM
    if _MEM is None:
        _MEM = {c["key"]: c for c in (_load("ota_memory.json").get("clues") or [])}
    return _MEM


def _pick_truth(rng, cid):
    """锁定这一个细节的「真值」：她这次说的是三选一里的哪一个。

    ota_memory 的 design_note 要求「值在本局锁定」——同一局反复回考必须问同一个，
    重开才重掷。以前这里写死 set[0]，等于第二局就能背下来了。
    """
    c = _memory().get(cid) or {}
    pool = list(c.get("set") or [])
    return rng.choice(pool) if pool else ""


def ensure_truth(s, cid, rng):
    """取这条线索本局的真值；还没掷过就掷一次死。

    「说」的那张卡（ota_say_*）正文里就写着「我想吃{truth}」——那是她第一次提，
    所以真值必须在显示那一刻就定下来，不能等到玩家选了选项才掷：
    否则屏幕上说「荔枝」、系统里锁成「芒果」，下一张回考卡就永远答不对。
    """
    tb = s.setdefault("_truth", {})
    if cid not in tb:
        tb[cid] = _pick_truth(rng, cid)
    return tb[cid]


def ask_order(s, cid, n, rng):
    """回考三选一的显示顺序：本局固定（同一张卡反复显示不会跳），跨局不同。"""
    ao = s.setdefault("_ask_order", {})
    if cid not in ao or len(ao[cid]) != n:
        idx = list(range(n))
        rng.shuffle(idx)
        ao[cid] = idx
    return ao[cid]


def load_world():
    world = {
        "cards": [],
        "lines": [],
        "intro": _load("intro.json"),
        "endings": _load("endings.json"),
        "memory": _load("ota_memory.json"),
        "pool": _load("ota_pool.json"),
        "names": _load("idol_names.json"),
    }
    cdir = os.path.join(DATA, "cards")
    for fn in sorted(os.listdir(cdir)):
        if fn.endswith(".json"):
            for c in _load(os.path.join("cards", fn)).get("cards", []):
                c["no"] = len(world["cards"]) + 1  # 全池全局序号（文件名码点序 + 文件内顺序）
                world["cards"].append(c)
    sdir = os.path.join(DATA, "storylines")
    for fn in sorted(os.listdir(sdir)):
        if fn.endswith(".json"):
            world["lines"].append(_load(os.path.join("storylines", fn)))
    return world


# ---------------------------------------------------------------- 状态
BASE = dict(money=1800, stamina=100, psyche=70, fame=5, enjou=0, kaibox=0, banzi=0,
            shiroi=0, shiren=0, relation_A=50, relation_B=50, relation_C=50, romance_risk=0)
STATE_KEYS = ["money", "stamina", "psyche", "fame", "stage", "dance", "sing", "mc",
              "enjou", "kaibox", "banzi", "shiroi", "shiren", "relation_A", "relation_B",
              "relation_C"]


def new_state(world, choice_id=None, name_style=None, rng=None):
    rng = rng or random.Random(0)
    intro = world["intro"]
    b = intro["base_state"]
    s = dict(BASE)
    s.update(money=b["money"], stamina=b["stamina"], psyche=b["psyche"], fame=b["fame"],
             dance=b["dance"], sing=b["sing"], mc=b["mc"],
             relation_A=b["relation"][0], relation_B=b["relation"][1], relation_C=b["relation"][2])
    # 五个种子 OTA
    s["ota"] = []
    for seed in world["pool"]["seeds"]:
        s["ota"].append(dict(id=seed["id"], name=seed["name"], stick=float(seed["stickiness"]),
                             archetype=seed["archetype"], fan_type=seed["fan_type"],
                             gender=seed.get("gender", "女"), risk=seed.get("risk", 0.1),
                             spend=int(seed.get("spend", 3)),   # 消费力：谁买得多
                             weeks_known=6))
    s["week"] = 1
    s["weeks_total"] = int(intro.get("weeks_total", 8))   # 一季几周
    s["beat"] = 0
    s["flags"] = set()
    s["delayed"] = []          # [{when, cond, effect, note, speaker}]
    s["cooldown"] = {}         # card_id -> 剩余回合数
    s["seen"] = []             # 已发生的卡 id
    s["log"] = []
    s["chose_leave"] = False
    s["last_live_choice"] = None
    s["max_single"] = 0.0
    s["template"] = 0.3
    s["clues"] = {}            # clue -> {truth_slot, level, state: 'said'|'asked'|'dropped'}
    s["clues_said"] = 0
    s["story"] = {}            # line_id -> 进度
    s["name"] = None
    s["name_style"] = name_style
    s["ended"] = None
    s["okawari"] = []          # 回考记录
    s["acting"] = None
    return s


def clamp(s):
    s["psyche"] = soft_cap_psyche(s["psyche"])
    # 断联之后那一段，炎上和板子不归这套数管了：它要涨到 999。
    # 这里如果照常封顶，后面那些屏刚写进去的数下一帧就被人削回 100。
    runaway = bool(s.get("_collapse")) or ("final_collapse" in (s.get("flags") or ()))
    for k in ("stamina", "psyche", "enjou", "shiroi", "kaibox", "banzi"):
        if runaway and k in ("enjou", "banzi"):
            s[k] = max(0, s[k])
            continue
        s[k] = max(0, min(100, s[k]))
    for k in ("dance", "sing", "mc"):
        s[k] = max(0, min(SKILL_CAP, s[k]))     # 练到 100 封顶
    for k in ("bold", "kuyang_count", "heat", "heart", "zhong", "zhongs", "gorshou",
              "true_talk", "clues_said", "low_income_weeks", "max_single", "romance_risk"):
        if k in s and isinstance(s[k], (int, float)):
            s[k] = max(0, s[k])       # 计数类只保证非负，别被上面的 0~100 截断
    for o in s["ota"]:
        o["stick"] = max(0.0, min(100.0, o["stick"]))
    return s


# ---------------------------------------------------------------- 派生量
def stage_score(s):
    """我这一季练成了什么。体力不在这里：它是「这一场还剩多少力气」，
    是单场发挥的折损（见 live_score），不是能力本身。"""
    relavg = (s["relation_A"] + s["relation_B"] + s["relation_C"]) / 3
    # 体力不进这里：它是「这一场还剩多少力气」，单独走 fatigue（见 do_week 的 Live 结算），
    # 否则「没练过但睡得好」的人会比「练过但累」的人强。
    return 0.32 * s["dance"] + 0.28 * s["sing"] + 0.22 * s["mc"] + 0.18 * relavg


def relavg(s):
    return (s["relation_A"] + s["relation_B"] + s["relation_C"]) / 3


def _derive(s):
    """补几个「算出来的量」。剧情线的闸门会读「舞台」，卡面 gate 里也写它，
    但 state 里从来没有这个键——只靠直接 s.get("舞台") 是拿不到数的。"""
    if not s.get("stage"):
        try:
            s["stage"] = round(stage_score(s), 1)
        except Exception:
            s["stage"] = 0


def stick_values(s):
    return [o["stick"] for o in s["ota"]]


def max_share(s):
    vs = stick_values(s)
    t = sum(vs) or 1.0
    return max(vs) / t


# ---------------------------------------------------------------- OTA 槽
def pick_ota(s, sel=None, rng=None):
    """按 casting.select 选一个当前在场的 OTA；选不到返回 None。"""
    sel = sel or {}
    cand = []
    for o in s["ota"]:
        # 剧情对象不跑龙套：她只在自己那条线里出现，
        # 否则「私联对象」会作为陌生 OTA 站到特典会队列里去。
        if o.get("is_storyline"):
            continue
        if "archetype" in sel and o["archetype"] != sel["archetype"]:
            continue
        if "fan_type" in sel and o["fan_type"] != sel["fan_type"]:
            continue
        if "gender" in sel and o["gender"] != sel["gender"]:
            continue
        if o["stick"] < sel.get("min_stickiness", 0):
            continue
        cand.append(o)
    if not cand:
        return None
    # 黏性越高越可能被选中
    weights = [max(1.0, o["stick"]) for o in cand]
    return rng.choices(cand, weights=weights, k=1)[0]


def _match_archetype(pool, sel):
    """给一个 casting.select，找出能拿来孵化的原型。"""
    archs = pool.get("archetypes") or []
    want = sel.get("archetype")
    if want:
        for a in archs:
            if a["id"] == want:
                return a
    ft = sel.get("fan_type")
    if ft:
        for a in archs:
            if ft in (a.get("fan_types") or []):
                return a
    # 只指定了性别（「一个女生第一次来」）：按性别找对口的原型，
    # 不能落到 archs[0]——那会让每个新人都是同一个原型
    g = sel.get("gender")
    if g and archs:
        tag = "女友粉" if g == "女" else ("男友粉" if g == "男" else "")
        if tag:
            pool_g = [a for a in archs if tag in (a.get("fan_types") or [])]
            if pool_g:
                return pool_g[0]
    if sel.get("any_archetype") and archs:
        # 新人不挑原型：这么多种人都可能是第一次来
        return archs[0]
    if not want and not ft:
        return None
    return None


def _gender_for(arch, rng):
    fts = arch.get("fan_types") or []
    if "女友粉" in fts and "男友粉" not in fts:
        return "女"
    if "男友粉" in fts and "女友粉" not in fts:
        return "男"
    return rng.choice(["女", "女", "男"])


def hatch(s, world, sel, rng, ignore_cap=False, base_stick=None):
    """生一个新 OTA：她第一次出现。一季最多 hatch_max 个
    （「带朋友来」这种剧情触发的可以 ignore_cap=True 绕过）。"""
    pool = world.get("pool") or world.get("ota_pool") or {}
    if not ignore_cap and s.get("hatch_n", 0) >= s.get("hatch_max", 3):
        return None
    arch = _match_archetype(pool, sel)
    if arch is None:
        return None
    gender = sel.get("gender") or _gender_for(arch, rng)
    used = {o["name"] for o in s["ota"]}
    names = [n for n in (pool.get("name_pools") or {}).get(gender, []) if n not in used]
    if not names:
        return None
    name = rng.choice(names)
    fts = [f for f in (arch.get("fan_types") or [])]
    if sel.get("fan_type") and sel["fan_type"] in fts:
        ft = sel["fan_type"]
    else:
        ft = fts[0] if fts else "事业粉"
    base = float(arch.get("base_stickiness", 60))
    need = float(sel.get("min_stickiness", 0) or 0)
    stick = min(need, base) if need else base
    if base_stick is not None:
        stick = float(base_stick)
    stick = max(0.0, min(100.0, stick))
    o = {
        "id": "hatch_%d" % (s.get("hatch_n", 0) + 1),
        "name": name,
        "gender": gender,
        "fan_type": ft,
        "archetype": arch["id"],
        "spend": int(arch.get("base_spend", 3)),
        "stick": stick,
        "weeks_known": 1,
        "is_seed": False,
        "met_week": s["week"],
        "notes": sel.get("notes") or "第一次来。",
    }
    s["ota"].append(o)
    s["hatch_n"] = s.get("hatch_n", 0) + 1
    s.setdefault("hatched", []).append(name)
    return o


def _prota_preset(mem_def, rng):
    """给这一季的私联对象掷一套「她自己的细节」（kind=choice 的项）。"""
    out = {}
    for key, item in (mem_def or {}).items():
        if (item or {}).get("kind") != "choice":
            continue
        pool = list((item or {}).get("pool") or [])
        if pool:
            out[key] = rng.choice(pool)
    return out


def protagonist(s, world, rng):
    """这一季的私联对象：从已经认识的 OTA 里挑一个「不会走的」，不再凭空造人。

    旧实现每次凭空生成一个 stick=75 的 shiren_prota：既跟玩家已经在追的人
    毫无关系，又永远顶着最高黏性，把重线 chaser 的位置也占了（两条线的
    专属 OTA 因此串台）。现在改成：从现有 OTA 里取黏性靠前的几个，随机挑
    一个当私联对象——不一定是黏性最大的那个。选中后整季固定（写进
    s["_prota"]），并补一套 memory 预设：{{cat_name}} 这类占位符和终局
    拷问都要靠它，漏了就会整屏填成「对方」。
    """
    p = s.get("_prota")
    if p:
        return p
    pool = [o for o in (s.get("ota") or []) if not o.get("is_storyline")]
    # 黏性靠前的几位里随机；不足三位就都算候选
    pool = sorted(pool, key=lambda o: -float(o.get("stick") or 0))[:3]
    if not pool:
        return None
    p = rng.choice(pool)
    ln = shiren_line(world) or {}
    mem_def = ln.get("memory_key") or {}
    preset = _prota_preset(mem_def, rng)
    mem = p.setdefault("memory", {})
    truth = s.setdefault("_truth", {})
    for k, v in preset.items():
        mem.setdefault(k, v)
        # 方案A：把她自己说过的值预先锁进真值表（加前缀与普通回考隔离）。
        # 收场拷问的 ensure_truth 见键已存在便不再另掷——「她说的=拷问问的=判对的」同一个值。
        truth.setdefault("shiren_" + k, mem[k])
    p["is_storyline"] = True
    p.setdefault("notes", "私下里认识的那个人。")
    s["_prota"] = p
    return p


def prota_memory(s):
    """她这一季被记住的那些细节：{key: 值}。剧情文案拿它填占位符。"""
    p = s.get("_prota") or {}
    return p.get("memory") or {}


def learn_memory(s, keys, text=""):
    """剧情选项的 `learns`：这一拍她讲出来的事，从此算「你知道」。

    fact 类没有 pool，值就取她那句话（`note`）——占了位也不至于填错。
    返回这次真正新记住的 key，界面可以据此说一句「你记住了这件事」。
    """
    p = s.get("_prota")
    if not p:
        return []
    if isinstance(keys, str):
        keys = [keys]
    mem = p.setdefault("memory", {})
    got = []
    for k in keys or []:
        if not k or k in mem:
            continue
        mem[k] = text or ""
        got.append(k)
    return got


def apply_story_flags(s, option):
    """剧情线选完之后的「后果」：那些只在数据里出现过、从来没人读的旗标。

    以前 `cut_early` / `deleted_ta` / `denied` / `double_life` 这些只会进
    `s["flags"]` 这个集合，进完就算了——玩家选「当晚就跟她说以后别来了」，
    线照样往下走。这里给每一个都接上一个真实的后果。
    """
    fl = option.get("flags") or []
    if not fl:
        return
    got = set(fl)
    # 真的断线：这两条是「主动结束」，不是「这一拍没踩准」。
    # 断掉之后 `_line_shut` 会让这条线从主线候选里消失，收场也不会再排。
    if got & {"cut_early", "deleted_ta"}:
        s["flags"].add("line_closed")
    if "knows_home" in got:
        s["kaibox"] = float(s.get("kaibox") or 0) + 8     # 她知道你家在哪了
    if "met_at_night" in got:
        s["kaibox"] = float(s.get("kaibox") or 0) + 5
    if "official_denial" in got:
        # 官方辟谣反而坐实了另一半：板子上多一张图，火上再浇一勺油
        s["banzi"] = float(s.get("banzi") or 0) + 6
        s["enjou"] = float(s.get("enjou") or 0) + 5
    if "double_life" in got:
        s["psyche"] = float(s.get("psyche") or 0) - 6     # 两边都要演，心力是这里耗掉的
    if "manager_leverage" in got:
        s["fame"] = float(s.get("fame") or 0) - 3         # 从这天起她说的话你不敢不听
        s["psyche"] = float(s.get("psyche") or 0) - 3
    if "team_knows" in got:
        s["relation_C"] = float(s.get("relation_C") or 0) + 4   # 有人替你兜着
        s["_team_knows"] = int(s.get("_team_knows") or 0) + 1
    if "denied" in got:
        s["psyche"] = float(s.get("psyche") or 0) - 4
        s["relation_A"] = float(s.get("relation_A") or 0) - 4
    if "dodged" in got:
        s["psyche"] = float(s.get("psyche") or 0) - 3
    if "promised_exclusive" in got:
        s["psyche"] = float(s.get("psyche") or 0) + 4
        s["kaibox"] = float(s.get("kaibox") or 0) + 6      # 那句话被截图存下来了
    if "promised_offduty" in got:
        s["kaibox"] = float(s.get("kaibox") or 0) + 6
    if "promised_remember" in got:
        s["psyche"] = float(s.get("psyche") or 0) + 3
    if "refused_promise" in got:
        s["psyche"] = float(s.get("psyche") or 0) - 5
        s["relation_A"] = float(s.get("relation_A") or 0) - 3
    # 恋爱线风险累积：每踩一次「推进」就 +1，供收场撞破掷骰用
    if "romance_risk" in got:
        s["romance_risk"] = int(s.get("romance_risk") or 0) + 1
    clamp(s)


def wants_new_face(card):
    """这张卡是不是「必须是个生面孔」：casting 里有 hatch_only 的槽。"""
    for cs in (card.get("casting") or []):
        if cs.get("hatch_only"):
            return True
    return False


def cast(s, card, rng, world=None):
    """执行一张卡的 casting，返回 slot -> ota 的映射。

    2026-11-15：以前任何带 allow_hatch 的卡在池子里凑不出人时都会现场生一个，
    结果「第一次来的人」之外的老卡也动不动蹦出个新名字，
    玩家看到的却是「来了个老粉」。现在生人必须显式 force_hatch：
    allow_hatch 只表示「找不到人可以生一个来顶」，force_hatch 才是「这张卡就是新人卡」。

    hatch_only 是 force_hatch 的严格版：**不先去现有 OTA 里找**，直接生人。
    这是给「第一次来的人」这种卡用的——它要的就是个生面孔，
    用 pick_ota 的话空 select 总能挑到一个老粉，force_hatch 一辈子走不到。
    """
    out = {}
    for cs in card.get("casting") or []:
        slot = cs.get("slot")
        if cs.get("hatch_only"):
            o = None
        else:
            o = pick_ota(s, cs.get("select"), rng)
        if o is None:
            if not (cs.get("force_hatch") or cs.get("hatch_only")):
                return None        # 这个卡要求的人不在场，整张卡不成立
            if world is not None:
                o = hatch(s, world, cs.get("select"), rng)
        if o is None:
            return None            # 新生儿也没生成出来（名额满了/没名字了）：整张卡不成立
        out[slot] = o
    # 回考守门：问句里「我上次说过的那个」必须是真说过的人。线索登记时
    # 存了 who（说出口的那一位）；ta 今天不在场（黏性掉了没来/退坑）就
    # 把这张回考卡整个撤掉——无中生有的提问比没有提问更伤。
    meta = card.get("_meta") or {}
    if meta.get("rq_stage") == "ask" and meta.get("clue"):
        info = (s.get("clues") or {}).get(meta["clue"]) or {}
        sid = info.get("who")
        if sid:
            o = next((x for x in s["ota"] if x["id"] == sid), None)
            if o is None or float(o.get("stick") or 0) < 30:
                return None
            out["speaker"] = o
    return out


# ---------------------------------------------------------------- 效果应用
# 「这件事会不会被外人看见」：卡面上没写，但它是整个游戏的重量所在。
BOLD_AXES = ("开盒", "板子", "炎上")


# 结局层要认的「这次是不是站到了台上」：私生场景里被拍到、上台撑着，也算站过
STAGE_TYPES = ("positive", "舞台事故", "外部舆论", "私生", "私生跟踪", "团内", "团内关系", "外部")


def _seethe_cost(s, option, card_type=None, slots=None):
    """选项被看见的代价（内账，不进 immediate）。
    - option["bold"] 是显式标记：'开盒' / '板子' / '炎上'，每标记一次记一次。
    - option["开盒"] / ["板子"] / ["炎上"] 这类数字键直接加到对应资源。
    - 卡面文案里明写着「发到超话 / 公开 / 被拍到」的选项，也算一次被看见：
      卡库的数值只有 1~6 点，撑不起 20~90 的结局门槛，这一笔是它的重量。
    - 「欠人情」这类选项（跨过那条线、欠了队友的、欠了钱的）
      每做一次，就把一段关系往死里推一格。"""
    kind = option.get("bold")
    if kind:
        s["bold"] = s.get("bold", 0) + 1
        if kind == "开盒":
            s["kaibox"] = s.get("kaibox", 0) + 4
        elif kind == "板子":
            s["banzi"] = s.get("banzi", 0) + 4
        elif kind == "炎上":
            s["enjou"] = s.get("enjou", 0) + 4
    else:
        blob = " ".join(str(option.get(k) or "") for k in ("id", "label", "desc", "note"))
        if any(w in blob for w in ("公开", "发出去", "超话", "发到", "说出去",
                                   "写上", "发帖", "群里", "录下来", "被拍到")):
            s["bold"] = int(s.get("bold") or 0) + 1
            # 话说出去会被截图，但「一句话」不是「一张照片」。
            # 卡类型决定分量：外部/外部舆论说出去的东西才真会被挂在板子上，
            # 团内和 OTA 互动里的一句话基本只在圈子里转两天。
            heavy = card_type in ("外部", "外部舆论", "舞台事故", "positive")
            s["banzi"] = float(s.get("banzi") or 0) + (0.2 if heavy else 0.0)
    # 卡库的数额太小，撑不起「关系坏掉」这种一整季的走势：选了就走远 10 点
    for f in (option.get("flags") or []):
        if f == "crossed_line":
            s["kuyang_count"] = s.get("kuyang_count", 0) + 1
            for r in ("relation_A", "relation_B", "relation_C"):
                s[r] -= 10
            # 「给了联系方式」先不记人：给了联系方式不等于越界，
            # 数人这件事交给下面的 met_alone，否则一条线上的人会被重复数三遍。
        elif f == "owe_team":
            # 把队友推出去顶罪：这张卡「锅甩到我头上」就是欠了人情才会发生
            s["owe_team"] = int(s.get("owe_team") or 0) + 1
        elif f in ("work_only", "zhong_boundary"):
            s["relation_B"] = s.get("relation_B", 50) - 10
        elif f == "met_alone":
            # 私下见过面：这才是「私联了几个人」真正数到的程度。
            # 只给联系方式还算不上越界，见上面才算。
            s["met_alone_n"] = s.get("met_alone_n", 0) + 1
            s["kaibox"] = s.get("kaibox", 0) + 5
            # 数「人」不数「次数」：同一个人见了三次，是一段关系，不是三个人
            # 谁：优先本卡 casting 选出的那个 OTA；剧情线没 casting，就看这条线的 chaser
            _who = ""
            for _slot in (slots or {}).values():
                if isinstance(_slot, dict) and _slot.get("id"):
                    _who = _slot["id"]
                    break
            if not _who:
                _who = str(s.get("_chaser") or "") or _who
                if not _who:
                    _who = "line|" + str(option.get("id", ""))
            s.setdefault("_met_people", set())
            if _who not in s["_met_people"]:
                s["_met_people"].add(_who)
                s["shiren"] = s.get("shiren", 0) + 1
    for axis, key in (("开盒", "kaibox"), ("板子", "banzi"), ("炎上", "enjou")):
        v = option.get(axis)
        if isinstance(v, (int, float)):
            s[key] = s.get(key, 0) + v
    # 舞台上那一下：卡库用 stage 写「这一场唱得更好/更差」，
    # 但它不是演出分（演出分只由舞/唱/live/体力/关系算），
    # 所以这里把它记成一笔本季累计，结局层的「最高单场」要用它。
    v = (option.get("immediate") or {}).get("stage")
    if isinstance(v, (int, float)) and card_type in STAGE_TYPES:
        s["gorshou"] = s.get("gorshou", 0) + v


# 事件的放大系数：卡库写的是「一张卡的数额」（1~6 点），
# 但它代表的是「这一周发生了什么」。不放大，整季下来炎上到不了 20、
# 关系坏不到 30，所有靠近态度的结局就只能是摆设。
class _EventMult:
    MULT = {"enjou": 2.5, "kaibox": 1.2, "banzi": 2.5, "shiroi": 2.0,
            "psyche": 1.4, "stamina": 1.2, "fame": 1.5}

    @classmethod
    def apply(cls, s, eff):
        for k in ("enjou", "kaibox", "banzi"):
            v = (eff or {}).get(k)
            if isinstance(v, (int, float)) and k in s:
                s[k] = s.get(k, 0) + v * (cls.MULT[k] - 1)


_EVENT_MULT = _EventMult()


def _rel(v):
    """关系往坏处掉得比往好处涨快：一次伤人的话，比十次好话记得久。"""
    return v * (1.6 if v < 0 else 1.0)


FAME_CAP = 100.0    # 人气上限（2026-11-19 用户拍板：每次加固定数值，不半路衰减）
FAME_SOFT = 100.0   # 软顶并到硬顶：加人气全程足额，到 100 才停


def add_fame(s, delta):
    """给人气加/减一点，返回实际变动量。

    软上限只压「这一帧新增的那一截」，绝不回缩存量。旧版把整个累计值反复
    往 40 拽（60→46.67→42.22…），于是任何一张跟人气无关的卡都会让人气
    莫名往下掉。现在：减益照数扣；增益在 40 以下全额、40 以上每点算 1/3；
    全程足额累加，收在 FAME_CAP=100；到顶就停在 100。
    """
    cur = float(s.get("fame", 0))
    if delta <= 0:
        s["fame"] = max(0.0, cur + delta)
    elif cur >= FAME_SOFT:
        s["fame"] = min(FAME_CAP, cur + delta / 3.0)
    elif cur + delta > FAME_SOFT:
        s["fame"] = min(FAME_CAP, FAME_SOFT + (cur + delta - FAME_SOFT) / 3.0)
    else:
        s["fame"] = min(FAME_CAP, cur + delta)
    return s["fame"] - cur


def apply_effect(s, eff, slots=None, card=None):
    slots = slots or {}
    for k, v in (eff or {}).items():
        if k.startswith("@"):
            o = slots.get(k[1:])
            if o is None:
                continue
            if k == "@speaker":
                o["stick"] += v * 1.0     # 对着谁说话，那个人对她的印象就动多少
            continue
        if k == "ota_all":
            for o in s["ota"]:
                o["stick"] += v * 0.5
            if v > 0:
                add_fame(s, v * 0.6)      # 黏性涨=有人更常来、带人来，人气跟着走
            continue
        if k == "fame" and isinstance(v, (int, float)):
            add_fame(s, v * _EVENT_MULT.MULT.get("fame", 1.0))
            continue
        if k == "relation_all":
            for r in ("relation_A", "relation_B", "relation_C"):
                s[r] += _rel(v)
            continue
        if k in ("relation_A", "relation_B", "relation_C") and isinstance(v, (int, float)):
            s[k] += _rel(v)
        elif k in s and isinstance(s[k], (int, float)) and k != "psyche":
            _m = _EVENT_MULT.MULT.get(k, 1.0)
            # 环境卡是「渐渐积累」的量，不该跟一次性事件卡用同一个倍率
            if (card or {}).get("type") == "ambient" and k in ("banzi", "enjou", "kaibox"):
                _m = 1.0
            s[k] += v * _m
        elif k == "psyche":
            s[k] += v * 0.6 * _EVENT_MULT.MULT["psyche"]   # 卡上的心理收益打六折再按事件放大
        elif isinstance(v, (int, float)):
            s[k] = s.get(k, 0) + v    # zhong / zhongs 这类剧情线专属量：按需建键
    if s.get("template", 0) >= 0.8:
        s["psyche"] -= 2      # 一直说同一套话，心里会空
    clamp(s)
    s["stage"] = stage_score(s)
    # 人气不再在这里被反复回缩：所有增减都在 add_fame 里按本帧增量算一次软上限


def apply_stance(s, stance):
    """二周目开局姿态：只加一点起始倾向，不锁任何线或结局。"""
    if not stance:
        return
    sid = stance.get("id") or ""
    for k, v in (stance.get("bonus") or {}).items():
        if k == "relation_all":
            for r in ("relation_A", "relation_B", "relation_C"):
                s[r] = s.get(r, 50) + v
        elif k == "ota_all":
            for o in s["ota"]:
                o["stick"] = o.get("stick", 50) + v
        elif k in ("psyche", "money", "dance", "sing", "mc"):
            s[k] = s.get(k, 0) + v
        elif isinstance(v, (int, float)):
            s[k] = s.get(k, 0) + v
    if sid and sid != "none":
        s["stance"] = sid
        s["stance_name"] = stance.get("name") or sid
    clamp(s)
    s["stage"] = stage_score(s)


def apply_option(s, option, rng, slots=None, card=None):
    """应用一个选项：立即效果、flag、延迟、线索。返回事件描述列表。"""
    ev = []
    apply_effect(s, option.get("immediate"), slots)
    # 选项自重：一张卡上「有人看到我」的代价是固定的，跟文案写多少点无关。
    # 卡库是「一两句话」的量级（1~6 点），结局门槛却是 20~90，
    # 所以公开的、留痕的选择要在这里一次性记账，不然整季下来什么也没发生。
    _seethe_cost(s, option, (card or {}).get("type"), slots)
    fl = option.get("flags") or []
    for f in fl:
        s["flags"].add(f)
        _lf = f.lower()
    # 「真话率」只数带语气标记的选项：说真话 / 说场面话。
    # 这里必须放在 flag 循环外——一个选项可能挂多个 flag，放里面会重复计数。
    _tone = option.get("tone")
    if _tone == "truth":
        s["truth_pick"] = int(s.get("truth_pick") or 0) + 1
        s["true_talk"] = int(s.get("true_talk") or 0) + 1
    elif _tone == "safe":
        s["safe_pick"] = int(s.get("safe_pick") or 0) + 1
    if fl:
        ev.append(("flag", ",".join(fl)))
    for dl in option.get("delayed") or []:
        rec = {"when": dl.get("when"), "cond": dl.get("condition"),
               "effect": dl.get("effect"), "note": dl.get("note"),
               "slots": {k: v.get("id") for k, v in slots.items() if v and v.get("id")}}
        # card_id：这张卡的延迟后果到期时，把一张「兑现卡」排进下周事件位
        for extra_key in ("hatch_friend", "base_stick", "card_id"):
            if dl.get(extra_key) is not None:
                rec[extra_key] = dl[extra_key]
        s["delayed"].append(rec)
    # 回考：锁定真值 / 用三选一
    if fl:
        s.setdefault("_fired", set()).update(fl)
    if option.get("rq_lock"):
        cid = None
        rl = option.get("rq_lock")
        if isinstance(rl, dict):
            cid = rl.get("clue")
        if cid and cid not in s["clues"] and s["clues_said"] < s.get("max_clues", 6):
            spk = {}
            if isinstance(rl, dict):
                spk = (slots or {}).get(rl.get("slot") or "speaker") or {}
            s["clues"][cid] = {"state": "said", "asked": False,
                                "said_week": s["week"], "who": spk.get("id"),
                                # 用 ensure_truth 而不是再掷一次：她说那句话的时候
                                # 真值就已经定了，这里重掷会得到和屏幕上不一样的那一个
                                "truth": ensure_truth(s, cid, rng)}
            s["clues_said"] += 1
            ev.append(("clue_said", cid))
    if "zhong_boundary" in (fl or []):
        # 把她挡在门外（重线安静两周）。这个冷却只归重线自己的挡回选项，
        # 不再跟回考的「岔开话题」绑在一起——对谁的水果偏好岔开话题，
        # 都不该让重线主角安静两周。
        line_cool(s, "zhong", 2)
    if option.get("rq_drop"):
        # 岔开话题：只作废这张卡自己说的那条线索（rq_lock 里带着 clue），
        # 不再把所有「已说未考」的线索一起作废。
        cid_d = None
        rl_d = option.get("rq_lock")
        if isinstance(rl_d, dict):
            cid_d = rl_d.get("clue")
        if cid_d:
            info_d = (s.get("clues") or {}).get(cid_d)
            if info_d is not None and info_d["state"] == "said":
                info_d["state"] = "dropped"
                s["clues_said"] = max(0, s["clues_said"] - 1)
                ev.append(("clue_dropped", cid_d))
    if option.get("rq_pick"):
        pick = option["rq_pick"]
        cid = pick.get("clue")
        # 答对与否只看「这一项是不是本局锁定的那个词」。
        # 以前认的是卡上写死的 choice=="true"（恒为选项 0），
        # 真值一随机就变成「记得对也判错」。
        truth = ensure_truth(s, cid, rng)
        correct = bool(truth) and (option.get("label") or "").strip() == truth
        who = pick.get("slot") or "speaker"
        # 卡面 immediate 已经带了一次 "@speaker" 的加减，这里补齐「记住/忘掉」的余量：
        # 答对 = 她更黏；答错 = 她往下掉，而且这一季不会再有第二次。
        o = (slots or {}).get(who)
        if o is not None:
            o["stick"] = max(0.0, min(100.0, o["stick"] + (4 if correct else -6)))
        info = (s.get("clues") or {}).get(cid)
        if info is not None:
            info["asked"] = True
            info["state"] = "known" if correct else "wrong"
            info["result"] = "ok" if correct else "bad"
        s.setdefault("rq_log", []).append({"clue": cid, "ok": correct, "week": s["week"]})
        if correct:
            s["recall_ok"] = int(s.get("recall_ok") or 0) + 1     # 记得住 = 回考答对，不是「说过真话」
        ev.append(("rq", "ok" if correct else "bad", cid))
    return ev


# ---------------------------------------------------------------- gate 表达式
_NUM = {"钱": "money", "体力": "stamina", "心理": "psyche", "人气": "fame", "炎上": "enjou",
        "开盒": "kaibox", "板子关注度": "banzi", "板子": "banzi",
        "私生": "shiroi", "私联人数": "shiren",
        # 「下次体力」是卡面里的写法，指的仍是 stamina；
        #「队友关系均值」要走 relavg，单独在 eval_clause 里算。
        "下次体力": "stamina", "队友关系均值": "relavg", "zhongs": "zhongs",
        "周": "week", "认识周数": "weeks_known", "阿棠关系": "relation_A",
        "露露关系": "relation_B", "小满关系": "relation_C", "舞台": "stage",
        "重线进度": "zhong", "heat": "heat", "热": "heat", "心动": "relation_A", "heart": "heart"}


def _ota_cond(s, desc):
    """任一 X OTA 黏性 ≥ N"""
    m = re.match(r"任一(.*?)OTA 黏性\s*([≥<=]+)\s*([\d.]+)", desc)
    if not m:
        return None
    kind, op, val = m.group(1).strip(), m.group(2), float(m.group(3))
    pool = s["ota"]
    if kind == "女友粉":
        pool = [o for o in pool if o["fan_type"] == "女友粉"]
    elif kind == "男性":
        pool = [o for o in pool if o["gender"] == "男"]
    elif kind:
        return None
    if not pool:
        return False
    best = max(o["stick"] for o in pool)
    return best >= val if "≥" in op or ">" in op else best <= val


def _tokens(a, b):
    return a if a in b else b


def eval_clause(s, text, stick_floor=None):
    text = text.strip()
    if not text or text == "无":
        return True
    if text in ("手头紧",):
        return s["money"] < 800
    if text in ("有一点余钱",):
        return s["money"] >= 500
    if text in ("不足两周房租",):
        return s["money"] < 1200
    # 这几种「曾经发生过」的状态，引擎其实一直在记，别再当 False：
    # blew_it = 冷场/翻车留档（engine.py:1749 / loop.py:872）
    # owe_team = 把队友推出去顶罪（engine.py:536，flag owe_team）
    # 「曾冷场或翻车」是整句落进来的（eval_gate 先按「且」拆，不再拆内部的「或」）。
    if text in ("曾冷场或翻车", "曾冷场", "翻车", "舞台翻车"):
        return int(s.get("blew_it") or 0) >= 1
    if text == "曾欠队友人情":
        return int(s.get("owe_team") or 0) >= 1
    if text in s["flags"] or text in ("crossed_line", "romance_started", "final_cautioned",
                                      "final_intimate", "played_safe"):
        return text in s["flags"]
    if "本周已选" in text:
        # 书不书名号都认；中文动作名映射到 do_act 落库的 id（s["acted"] 存的是 id）
        m = re.search(r"『(.+?)』", text)
        name = m.group(1) if m else text.replace("本周已选", "").strip(" 　（）()")
        alias = {"练舞": "dance", "练唱": "sing", "练营业": "mc", "练话术": "mc",
                 "拍内容": "content", "拍内容发微博": "content",
                 "开直播": "work", "直播": "work", "打工": "work", "躺": "rest"}
        return s.get("acted") == alias.get(name, name)
    # 资源别名（「钱」vs「money」、「开盒风险」vs「kaibox」等）
    for cn, en in (("开盒风险", "开盒"), ("私生跟踪", "私生"), ("舞台稳定", "舞台"),
                   ("板子关注度", "板子")):
        text = text.replace(cn, en)
    # 剧本里同义不同写法：OTA黏性/OTA 黏性、私生跟踪/私生、舞台稳定/舞台
    t = text.replace("私生跟踪", "私生").replace("舞台稳定", "舞台").replace("开盒风险", "开盒")
    t = re.sub(r"\s*OTA\s*黏性", " OTA黏性 ", t).replace("OTA黏性", "@OTA")
    t = re.sub(r"\s+", " ", t).strip()
    if re.match(r"^任一.*@OTA", t):
        kind = t.replace("任一", "").split("@OTA")[0].strip()
        op, val = _cmp(t)
        if op is None:
            return False
        pool = s["ota"]
        if kind == "女友粉":
            pool = [o for o in pool if o["fan_type"] == "女友粉"]
        elif kind == "男性":
            pool = [o for o in pool if o["gender"] == "男"]
        elif kind:
            return False
        if not pool:
            return False
        best = max(o["stick"] for o in pool)
        return best >= val if "≥" in op else best <= val
    m_mate = re.match(r"^任一队友关系\s*(≥|≤|>|<)\s*([\d.]+)$", t)
    if m_mate:
        # 「任一队友关系」：三个队友里关系最好的那个达不达标（truth_team_doubt 用）。
        # 以前解析不了这句，兜底 return False，整卡死。
        best = max(float(s.get("relation_A") or 0), float(s.get("relation_B") or 0),
                   float(s.get("relation_C") or 0))
        val = float(m_mate.group(2))
        return best >= val if m_mate.group(1) in ("≥", ">") else best <= val
    m = re.match(r"^(.+?)\s*(≥|≤|=|>|<)\s*([\d.]+)$", t)
    if m:
        key = _NUM.get(m.group(1).strip())
        if key is None:
            return False
        if key == "weeks_known":
            # 「认识周数」在带「任一OTA黏性 ≥ X」的闸门里，指的是「那位黏性达标的
            # OTA」认识多久（取其中最久者），不是全队最年轻的人——否则孵化一个
            # 新人就把 10 张重档回考卡全锁两周。
            if stick_floor:
                cand = [o["weeks_known"] for o in s["ota"]
                        if (o.get("stick") or 0) >= stick_floor]
                cur = max(cand) if cand else 0
            else:
                cur = min([o["weeks_known"] for o in s["ota"]] or [6])
        elif key == "shiren":
            cur = s["shiren"]
        elif key == "stage":
            cur = stage_score(s)
        elif key == "relavg":
            cur = relavg(s)
        else:
            cur = s.get(key, 0)
        val = float(m.group(3))
        op = m.group(2)
        if op in ("=",):
            return abs(cur - val) < 1e-6
        return cur >= val if op in ("≥", ">") else cur <= val
    return False


def _cmp(t):
    """从文本里抠出比较符与数值，如 '≥ 45' -> ('≥', 45.0)"""
    m = re.search(r"(≥|≤|=|>|<)\s*([\d.]+)", t)
    return (m.group(1), float(m.group(2))) if m else (None, 0.0)


def _gate_stick_floor(parts):
    """闸门里「任一OTA黏性 ≥ X」给出的门槛。同一个闸门里的「认识周数」
    要按这个门槛取人，别拿全队最小值。"""
    floor = None
    for x in parts:
        m = re.search(r"任一\s*OTA\s*黏性\s*(≥|>)\s*([\d.]+)", x)
        if m:
            v = float(m.group(2))
            floor = v if floor is None else max(floor, v)
    return floor


def eval_gate(s, gate):
    """支持：无 / 单条 / 「A 且 B」/「A 或 B」/ 带中文括号注释 / 不带空格的比较。"""
    if not gate:
        return True
    g = re.sub(r"（[^）]*）", "", gate)
    if "且" in g:
        parts = g.split("且")
        floor = _gate_stick_floor(parts)
        return all(eval_clause(s, x, floor) for x in parts)
    if "或" in g:
        return any(eval_clause(s, x) for x in g.split("或"))
    return eval_clause(s, g)


# ---------------------------------------------------------------- 抽卡
def _rq_ready(s, c):
    """回考两张卡的先后关系：没听过的事不能考，听过的事不用再「第一次听说」。

    以前 42 张回考卡（每类线索 say/ask 各一张）全靠 gate 的「黏性 ≥ 45」拦，
    于是玩家会在她还没说过的时候被问「我上次说想吃什么来着」——
    答对也是瞎蒙，答错还扣黏性，纯坑。
    """
    rq = (c.get("_meta") or {}).get("rq_stage")
    if not rq:
        return True
    cid = (c.get("_meta") or {}).get("clue")
    info = (s.get("clues") or {}).get(cid)
    if rq == "ask":
        # 只有「说过了、还没考过」的细节才考
        return bool(info) and info.get("state") == "said" and not info.get("asked")
    if rq == "say":
        # 已经听过（锁定过 / 考过 / 岔开）的，不再重演「第一次跟我说」
        return not info
    return True


def _memory_boost(s):
    """「她说过的那些小事」攒得太少，收场就只剩一道题。

    42 张回考卡被 0.15 的权重压着（不压的话一周里它会把别的卡全挤掉），
    代价是一季下来常常只锁到一两条线索——实测 20 局里 10 局只有 2 条、
    5 局只有 1 条，于是「收场」的三连问变成一问一答，答对就成『唯一』。
    这里按还差几条补权重：越到季末、缺得越多，就越该让她的日常占掉一个位置。
    """
    total = int(s.get("weeks_total") or 8)
    left = total - int(s.get("week") or 1)
    if left <= 0:
        return TYPE_WEIGHT["OTA记忆"]
    have = len(finale_clue_pool(s))
    want = 5                     # 收场要 3 道题，留两条余量
    gap = want - have
    if gap <= 0:
        return TYPE_WEIGHT["OTA记忆"]
    return min(1.1, TYPE_WEIGHT["OTA记忆"] + 0.32 * gap)


def stance_weight(s, c):
    """二周目姿态的抽卡偏向：只把「这张卡最像哪条线」算出来，匹配就 ×1.3。

    看的是卡面所有选项的正面增量，不读 gate；所以不会让某类卡变成必出，
    只是略微把这一季的选择递到更靠近姿态的方向。
    一周目 s["stance"] 为空，返回值恒 1.0，分布不变。
    """
    st = s.get("stance")
    if not st:
        return 1.0
    aff = {"stage": 0.0, "money": 0.0, "self": 0.0, "bond": 0.0}
    for o in c.get("options") or []:
        if o.get("tone") == "truth":
            aff["self"] += 3
        effs = [o.get("immediate") or {}, o.get("effect") or {}]
        for dl in o.get("delayed") or []:
            effs.append(dl.get("effect") or {})
        for eff in effs:
            if not isinstance(eff, dict):
                continue
            for k, v in eff.items():
                if not isinstance(v, (int, float)) or v <= 0:
                    continue
                if k in ("dance", "sing", "mc", "stage"):
                    aff["stage"] += v
                elif k in ("money", "fame"):
                    aff["money"] += v
                elif k == "psyche":
                    aff["self"] += v
                elif (k == "relation_all" or k.startswith("relation_")
                      or k.startswith("@") or k.startswith("ota")
                      or k in ("heart", "zhong")):
                    aff["bond"] += v
    best = max(aff, key=aff.get)
    if aff[best] <= 0:
        return 1.0
    return 1.3 if best == st else 1.0


def draw(s, world, rng, kind=None, pool_ids=None, kinds=None):
    """三层抽卡：硬闸门 → 权重 → cooldown。kind 过滤单个 type，kinds 过滤一组。"""
    cands = []
    for c in world["cards"]:
        # 兑现卡（due_）不参与普通抽卡：它们由 loop._draw_week_events 到点插队
        if c["id"].startswith("due_"):
            continue
        if kind and c.get("type") != kind:
            continue
        if kinds and c.get("type") not in kinds:
            continue
        if pool_ids is not None and c["id"] not in pool_ids:
            continue
        if s["cooldown"].get(c["id"], 0) > 0:
            continue
        if not _rq_ready(s, c):
            continue
        if not eval_gate(s, c.get("gate")):
            continue
        cands.append(c)
    if not cands:
        return None
    weights = [max(0.05, float(c.get("weight", 1.0))) for c in cands]
    # 42 张 OTA 记忆卡数量远多于别的类型，不压权重的话一周里它会把别的卡全挤掉
    mem_w = _memory_boost(s)
    # 这一季已经上过屏的卡降权（不硬禁）：3 周冷却只管短期，过几周同一张
    # 低门槛卡又能抽回来，一季下来玩家翻来覆去只见那三十来张。s["seen"] 由
    # loop.py 的 _render_card 在上屏时登记；沙盒 do_week 不写它，故不影响自动模拟。
    seen = set(s.get("seen") or [])
    weights = [w * (mem_w if c.get("type") == "OTA记忆"
                    else TYPE_WEIGHT.get(c.get("type"), 1.0))
               * (0.25 if c["id"] in seen else 1.0)
               * stance_weight(s, c)
               for w, c in zip(weights, cands)]
    return rng.choices(cands, weights=weights, k=1)[0]


TYPE_WEIGHT = {"OTA记忆": 0.15, "OTA相处的瞬间": 0.6, "ambient": 0.35,
               "日常": 2.0, "团内": 1.6, "团内关系": 1.3, "外部": 1.4,
               "外部舆论": 1.2, "私生": 0.8, "私生跟踪": 1.0, "private": 1.0,
               "positive": 0.35, "舞台事故": 1.0, "私联恋爱": 1.0, "OTA互动": 1.0,
               "同行": 1.05}


OTA_TYPES = ["OTA互动", "OTA记忆", "私联恋爱", "私生"]


def _is_ota_card(c):
    return c.get("type") in OTA_TYPES


def warm_ota(s):
    """周末谁会来：黏性越高越可能到场；黏性低到 30 以下的人直接不再来。"""
    pool, wts = [], []
    for o in s["ota"]:
        p = max(0.0, (o["stick"] - 30) / 55.0)
        p = min(p, 0.95)
        if p <= 0:
            continue
        pool.append(o); wts.append(p)
    if not pool:
        return []
    n = 3 if s["fame"] >= 40 else (2 if s["fame"] >= 20 else 1)
    out = []
    for _ in range(min(n, len(pool))):
        pick = random_pick(s, pool, wts)
        if pick is None:
            break
        if pick in out:
            continue
        out.append(pick)
    # 买券的人不等于说上话的人：铁杆会自己来，跟人气无关
    for o in sorted(s["ota"], key=lambda x: -x["stick"]):
        if o["stick"] < 72:
            break
        if o not in out:
            out.append(o)
    return out


def everyone_gone(s):
    """所有种子 OTA 都不再来了：这个团只剩我自己在台上。"""
    return all(o["stick"] < 30 for o in s["ota"])


def random_pick(s, pool, wts):
    if not pool:
        return None
    r = s.get("_rng")
    if r is None:
        return pool[0]
    i = r.choices(range(len(pool)), weights=wts, k=1)[0]
    return pool[i]


def ota_pick(s, world, rng, chosens, allow_newbie=False):
    """周日的特典会：先看今天会不会开出一张 OTA 卡（她来了才算），
    再决定『她今天想说什么』。同一个人一周只出现一次。

    四桶：
      ask   —— 本局已经说过的线索，她隔场拿来考一下（回考第二拍）
      say   —— 还没说过的线索，她随口说出细节（回考第一拍）
      ota   —— 别的 OTA 互动卡（她带来什么、她怎么样）
      other —— 相处日常那一类
    ask 给 20%、say 给 12%，其余八成留给别的卡：一季特典会只有五六次，
    全用来考同一件事，剧情就只剩考试了。"""
    if not chosens:
        return None, None

    def pick(pool):
        return rng.choices(pool, weights=[max(0.05, float(c.get("weight", 1.0))) for c in pool], k=1)[0]

    by_id = {c["id"]: c for c in world["cards"]}
    cool = s.setdefault("clue_cool", {})

    asks, says = [], []
    for cid, info in (s.get("clues") or {}).items():
        if info.get("state") != "said":
            continue
        if cool.get(cid, 0) > 0:
            continue
        c = by_id.get("ota_ask_" + cid)
        if c and eval_gate(s, c.get("gate")):
            asks.append(c)

    if s.get("clues_said", 0) < s.get("max_clues", 6):
        for c in world["cards"]:
            if not c["id"].startswith("ota_say_"):
                continue
            cid = c["id"][len("ota_say_"):]
            if cid in (s.get("clues") or {}):
                continue
            if cool.get(cid, 0) > 0:
                continue
            if eval_gate(s, c.get("gate")):
                says.append(c)

    # 已经冷却的线索也检查一下（只用来回收）
    for cid in list(cool):
        if cool[cid] > 0:
            cool[cid] -= 1
        else:
            del cool[cid]

    rest = [c for c in world["cards"]
            if _is_ota_card(c)
            and not c["id"].startswith(("ota_say_", "ota_ask_"))
            and s.get("cooldown", {}).get(c["id"], 0) <= 0
            and eval_gate(s, c.get("gate"))]

    r = rng.random()
    # 「她说」这一桶得能自己长：收场要三题，一季只有八次特典，
    # 硬给 12% 的话平均只说得上两件事，收场就退成「一问一答」，
    # 答对一题就成『唯一』、答错一题就成『用完』。
    have = len(finale_clue_pool(s))
    need = max(0, 5 - have)
    say_share = min(0.58, 0.14 + 0.09 * need)
    card = None
    if asks and r < 0.20:
        card = pick(asks)
    elif says and r < 0.20 + say_share:
        card = pick(says)
    elif rest and r < 0.92:
        card = pick(rest)
    elif asks or says or rest:
        pool = rest or (asks + says)
        card = pick(pool)
    if card is None:
        return None, None

    # 抽到的如果是回考卡，记住她是谁、并把这条线索压一周
    who = chosens[0]
    if card["id"].startswith("ota_ask_"):
        cid = card["id"][len("ota_ask_"):]
        cool[cid] = int(s.get("ask_cooldown", 2))
        info = (s.get("clues") or {}).get(cid)
        if info is not None:
            info["asked"] = True
    return card, who


# 舆论会淡：只要这周没继续加，板子和炎上每周回落一点。
# 2026-11-14：炎上原来每周 −4，把全库「炎上 ≥ N」的卡全锁死了（gate_report 实测整季恒 0）。
# 改成：炎上只按比例慢慢退（每周 8%），一旦烧起来就得自己扛几周；板子还是按点退。
FADE = {"banzi": 6.0}
ENJOU_FADE_RATE = 0.08


def settle_delayed(s, world, rng):
    """到点的延迟后果：效果生效，顺便看看有没有「带朋友来」。

    返回新生的 OTA 名字列表，界面拿来写一句回执。
    """
    born = []
    for d in list(s.get("delayed") or []):
        when = d.get("when")
        fire = False
        if when in ("本场结束", "下周"):
            fire = True
        elif when == "条件":
            # 落进 s["delayed"] 的键叫 "cond"（见 apply_option），
            # 这里兼容一下原始写法 "condition"，免得手塞数据时静默不触发。
            cond = d.get("cond") or d.get("condition")
            fire = bool(cond) and bool(eval_gate(s, cond))
        if not fire:
            continue
        if d.get("effect"):
            apply_effect(s, d["effect"])
        # 兑现卡：这件事下周会回来找你（由 loop._draw_week_events 优先排进事件位）
        if d.get("card_id"):
            s.setdefault("_due_cards", []).append(d["card_id"])
        if d.get("hatch_friend"):
            sel = {"any_archetype": True, "notes": "她带来的朋友。"}
            an = hatch(s, world, sel, rng, ignore_cap=True,
                       base_stick=d.get("base_stick"))
            if an is not None:
                born.append(an["name"])
        s["delayed"].remove(d)
    return born


def cool_down(s):
    for k, v in FADE.items():
        if k in s and s.get(k):
            s[k] = max(0.0, float(s[k]) - v)
    if s.get("enjou"):
        s["enjou"] = max(0.0, float(s["enjou"]) * (1.0 - ENJOU_FADE_RATE))
    for k in list(s["cooldown"]):
        s["cooldown"][k] -= 1
        if s["cooldown"][k] <= 0:
            del s["cooldown"][k]


# ---------------------------------------------------------------- 剧情线
def _enter_value(s, line, st):
    """剧情线的「投入量」：私联=heat(用 shiren 承接)、恋爱=心动(relation_A)、重线=zhong。
    拍0 的 enter 恒为 0，不看。"""
    key = st.get("key", "")
    n = st["stage"]
    if line["_meta"]["id"] == "romance":
        return s["relation_A"] - 60 if n else 0
    if line["_meta"]["id"] == "zhong":
        return s.get("zhong", 0)
    return s.get("heat", 0)


def _gate_ok(s, line, st):
    """gate 里出现「热」「心动」「重线进度」时，用剧情线自己的进度而不是通用资源。

    但拍 0（第一拍）例外：它写的是「阿棠关系 ≥ 60」这种真实数值门槛，
    不是心跳计数器——以前一律按 enter_heat(relation_A-60) 比，
    结果阿棠关系涨到 79 都开不了第一拍。"""
    lid = line["_meta"]["id"]
    if lid == "romance" and st["stage"] == 0:
        return (s.get("relation_A") or 0) >= 50 and s["week"] >= 2
    g = st.get("gate") or ""
    if not eval_gate(s, g):
        return False
    need = st.get("enter_heat")
    if need is None:
        return True
    return _enter_value(s, line, st) >= need


def _remember_chaser(s, line, v=None, rng=None):
    """记住「她」是谁：重线每一拍都跟着同一个人走。

    不再固定选黏性最大的——私联对象黏性天然最高（越线门槛 75），每次都她
    当 chaser 会让两条线串台。改成从黏性靠前的几位里随机挑一个，挑完定
    死、整线不换。rng 由调用方传进来，和 TS 侧消耗同一条随机序列。
    """
    if not ((line.get("_meta") or {}).get("chaser_schema") or (v or {}).get("select_chaser")):
        return
    if not s.get("_chaser") and s.get("ota"):
        pool = [o for o in s["ota"] if not o.get("is_storyline")]
        pool = sorted(pool, key=lambda o: -float(o.get("stick") or 0))[:3]
        if pool:
            chosen = rng.choice(pool) if rng is not None else pool[0]
            s["_chaser"] = chosen["id"]


def line_stage(s, line):
    """返回该线当前可进入的拍（stage dict）或 None。
    只认「下一拍」不许跳拍；同一周同一条线最多推一拍；
    玩家在某条线上已表明不打算走之后，这条线会安静两拍（line_cool）。"""
    lid = line["_meta"]["id"]
    _derive(s)
    if s.get("_line_cool", {}).get(lid, 0) > s["week"]:
        return None
    prog = s["story"].get(lid)
    nxt = 0 if prog is None else prog["stage"] + 1
    for st in line["stages"]:
        if st["stage"] == nxt:
            return st if (_gate_ok(s, line, st) and not _this_week(s, lid)) else None
    return None


def line_cool(s, lid, weeks=2):
    s.setdefault("_line_cool", {})[lid] = s["week"] + weeks


def _this_week(s, lid):
    """同一周同一条线只推一拍。

    注意这里不能直接比 s["week"]：`do_week` 中途会结算/换周（收入、advance），
    要用显式的「本次推线周期号」，否则同一条线在同一次 do_week 里会被抽两次，
    met_alone 之类的「人数」就会被重复计数。"""
    # 注意：`.get("_line_week", {})` 在键存在但值是 None 时返回的是 None，后面 .get() 会炸，
    # 所以必须 `or {}`；同理 _line_tick 是 None 时不能和 None 比（否则「都没推过」会被判成
    # 「这周推过了」，所有剧情线永远开不了）。
    tick = s.get("_line_tick")
    if tick is None:
        return False
    return ((s.get("_line_week") or {}).get(lid) == tick)


def MAINLINE_FALLBACK_WEEK(s):
    """到这一周还没人主动锁主线，就由已经在走的那条线接手。"""
    return max(3, int(s.get("weeks_total") or 8) - 3)


def _line_shut(s, lid):
    """按 flag 判断这条线是不是已经被玩家关掉了（不走 world 也能判）。"""
    fl = s.get("flags") or set()
    if lid == "shiren":
        return "line_closed" in fl
    if lid == "romance":
        return "kept_wall" in fl
    return False


def _mainline_pick(s):
    """算出「这一季该走哪条线」，None 表示还没定。

    三条线一季只能走一条。私联和恋爱是玩家伸手选的（`crossed_line` 那个选项、
    恋爱那条 `advance=1` 的选项），重线是她压过来——它每一条选项都 +1，
    玩家没有「不推进」这个动作，所以重线不能去跟另两条抢，只能兜底：
    到 MAINLINE_FALLBACK_WEEK 还什么都没发生，就让已经在走的那条接任；
    一条都没在走，就重线上场（她一直站在那儿，只是你之前没往那边看）。
    """
    fl = s.get("flags") or set()
    if "crossed_line" in fl:
        return "shiren"
    if (s.get("heart") or 0) >= 1:
        return "romance"
    if int(s.get("week") or 1) < MAINLINE_FALLBACK_WEEK(s):
        return None
    story = s.get("story") or {}
    best, bn = None, -1
    for lid in ("shiren", "romance", "zhong"):
        # 只认「真的出过场」的线（story 里有记录）。以前把没出场的线也当候选、
        # stage 记成 -1 一起比大小，兜底周就会把主线锁给排在最前面的私联——
        # 而私联没越过线根本不会出现，`draw_line_all` 又按主线把另外两条挡掉，
        # 于是整季一条剧情线都没有（200 局实测中撞到 1 次）。
        if lid not in story or _line_shut(s, lid):
            continue
        # 被关掉的线不能当主线：玩家在 stage0 拒过一次就永久封锁，
        # 要是它只是因为「拒之前进过那一拍」而进度最高，主线会锁死在一条死线上，
        # 这一季从此一条线都不出现。
        n = (story.get(lid) or {}).get("stage", -1)
        if n > bn:
            best, bn = lid, n
    if best is not None:
        return best
    # 一条都没走过：重线上场。她一直在那儿，只要黏性够高她就压过来，
    # 是三条线里唯一不需要玩家先伸手的，所以兜底只能是她。
    return "zhong" if not _line_shut(s, "zhong") else None


def mainline(s):
    """这一季已经走上的那条线。定了就不再改——后面再越线也不算数了。

    写成落盘字段（`_mainline`）而不是每次现算：不然第 5 周重线兜底接了主线，
    第 6 周玩家又越了线，现算就会当场把主线换成私联，两条线同时活着。
    """
    lid = s.get("_mainline")
    if lid:
        return lid
    lid = _mainline_pick(s)
    if lid:
        s["_mainline"] = lid
        s["_mainline_week"] = s.get("week")
    return lid


def line_locked(s, line):
    """这条线是否因为『不想走』而被玩家关掉（flag line_closed / romance_giveup 之类）。"""
    fl = s["flags"]
    lid = line["_meta"]["id"]
    if lid == "shiren" and "line_closed" in fl:
        return True
    if lid == "romance" and "kept_wall" in fl:
        return True
    return False


# ---------------------------------------------------------------- 私联终局
def shiren_line(world):
    for ln in world["lines"]:
        if ln["_meta"]["id"] == "shiren":
            return ln
    return None


def romance_line(world):
    for ln in world["lines"]:
        if ln["_meta"]["id"] == "romance":
            return ln
    return None


def FINALE_WEEK(s):
    """『决赛前一晚』：季末那一周的开头，必到，不等 stage4。

    storyline_shiren 的设计说明写的是「唯一钉死的日历」——拍 5 收场不看投入度，
    只看越没越线。8 周一季就从末周（W8）开头触发，玩家前七周都已经走完。
    """
    return int(s.get("weeks_total") or 8)


def shiren_finale_ready(s, world):
    """该不该进收场：越了线、还没收过、也没被玩家关掉，而且这一季走的就是私联。"""
    if "crossed_line" not in s["flags"]:
        return False
    if "finale_done" in s["flags"]:
        return False
    # 一季只走一条线：越线发生在主线已经定给别人之后（例如前五周一直没人伸手、
    # 重线接了主线，第 7 周才越线），这条就不算这一季的路，不再排收场。
    if mainline(s) != "shiren":
        return False
    ln = shiren_line(world)
    if ln is None or line_locked(s, ln):
        return False
    return int(s.get("week") or 1) >= FINALE_WEEK(s)


def finale_clue_pool(s):
    """终局能考哪些：她这一季说过、而且系统里锁着一个真值的细节。"""
    mem = _memory()
    out = []
    for cid, info in (s.get("clues") or {}).items():
        if cid not in mem:
            continue
        # dropped = 玩家岔开话题作废的线索：按 _meta 的承诺「彻底消失」，
        # 不进收场拷问池，也不再占 have 的额度。
        if info.get("state") in ("said", "known", "wrong"):
            out.append(cid)
    return out


def finale_quiz_cards(s, world, rng, n=3):
    """从解锁的记忆点里抽 n 道拷问，做成可以直接上屏的卡。

    题目直接复用 ota_memory 的 ask[] 与 set[]——这套台词本来就是为「你还记得吗」
    写的，不用另造题库。选项顺序按本局固定洗牌，正确项的位置跟 ota_ask_* 卡一致。
    """
    mem = _memory()
    pool = finale_clue_pool(s)
    if not pool:
        return []
    rng.shuffle(pool)
    picks = pool[:n]
    cards = []
    for cid in picks:
        c = mem.get(cid) or {}
        vals = list(c.get("set") or [])
        if len(vals) < 2:
            continue
        truth = ensure_truth(s, cid, rng)
        if truth not in vals:
            continue
        # 三选一：真值 + 两个干扰项（与 shiren 拷问同一口径）
        wrong = [v for v in vals if v != truth]
        rng.shuffle(wrong)
        opts = [truth] + wrong[:2]
        # 题干用 ask_q（一句天然的问法），不用 ask[]——ask[] 是「我上次说的那个
        # 是{truth}来着」这种陈述句挖空，真值一填进去答案就印在问句上，
        # 抹成「那个」又读成「今天又拖到那个，午饭都省了」这种别扭话。
        say = c.get("ask_q") or rng.choice(c.get("ask") or ["『你还记得我之前说过的那个吗？』"])
        cards.append({
            "id": "finale_quiz_%s" % cid,
            "type": "OTA记忆",
            "title": "收场",
            "no": None,  # 动态卡没有全池序号；显式 None 与 TS 对齐
            "_meta": {"rq_stage": "ask", "clue": cid,
                      "react_good": c.get("react_good") or {},
                      "react_bad": c.get("react_bad") or {},
                      "finale": True},
            "narrative": say.replace("{truth}", "那个"),
            # 选项按 set 原序排，上屏时由 loop._ask_options 按本局顺序重排——
            # 这里再洗一次就洗两遍了，位置会和真值对不上。
            "options": [{"id": "pick_%d" % i, "label": v, "desc": "",
                         "rq_pick": {"clue": cid, "slot": "speaker",
                                     "choice": "true" if v == truth else "false"}}
                        for i, v in enumerate(opts)],
        })
    return cards


def shiren_finale_quiz_cards(s, world, rng, n=3):
    """私联收场拷问的独立出题通道（方案A）。

    只从私联对象「自己随口说过的小事」出题——即 memory_key 里 kind=choice
    的项。这些值在 protagonist() 里已预锁进 s['_truth']（键名加 shiren_ 前缀
    与普通回考隔离），所以：她叙事里说的 = 这里问的 = 判题认的对答案，是同一个
    值。不再走 s['clues'] 那套 ota_memory 题库，避免两套真值错位——玩家越认真
    记、越被判错的割裂。
    """
    ln = shiren_line(world) or {}
    mem_def = ln.get("memory_key") or {}
    keys = [k for k, item in mem_def.items()
            if (item or {}).get("kind") == "choice"
            and list((item or {}).get("pool") or [])]
    if not keys:
        return []
    # 公平性：她「真的在叙事里说出口过」的细节排前面（loop._fill 渲染时登记进
    # s["_prota_revealed"]）。以前全凭 6 项随机抽，她从没说过的花/老家也会被考——
    # 认真玩也会被判「用完」。没说过的只拿来兜底凑数。
    revealed = s.get("_prota_revealed") or []
    rev = [k for k in keys if k in revealed]
    rng.shuffle(rev)
    # 没说出口的细节不再兜底凑数：她从没提过的老家/花也会被考，
    # 认真玩反而被判「用完」。全面没线索就少出几道，出几道算几道。
    cards = []
    for cid in rev[:n]:
        item = mem_def[cid] or {}
        vals = list(item.get("pool") or [])
        truth = s.get("_truth", {}).get("shiren_" + cid)
        if not truth or truth not in vals:
            continue
        # 三选一：真值 + 两个随机干扰项（pool 有 4~8 个值，全摆出来不成回考）。
        wrong = [v for v in vals if v != truth]
        rng.shuffle(wrong)
        opts = [truth] + wrong[:2]
        say = item.get("ask_q") or "『我说过的那件小事，你还记得吗？』"
        cards.append({
            "id": "finale_quiz_shiren_%s" % cid,
            "type": "OTA记忆",
            "title": "收场",
            "no": None,  # 同上
            "_meta": {"rq_stage": "ask", "clue": "shiren_" + cid,
                      "react_good": item.get("react_good") or {},
                      "react_bad": item.get("react_bad") or {},
                      "finale": True},
            "narrative": say.replace("{truth}", "那个"),
            "options": [{"id": "pick_%d" % i, "label": v, "desc": "",
                         "rq_pick": {"clue": "shiren_" + cid, "slot": "speaker",
                                     "choice": "true" if v == truth else "false"}}
                        for i, v in enumerate(opts)],
        })
    return cards


def finale_pass_n(n_cards):
    """答对几道才算「真的看见过她」：三题要对两题，两题就得全对。

    以前两题也只要求答对一题，等于 50% 就能拿到「唯一」，
    比三题的 2/3 门槛还松——题目越少门槛反而越低，说不过去。
    """
    if n_cards <= 0:
        return 0
    if n_cards <= 2:
        return n_cards
    return 2


def apply_finale_outcome(s, n_ok, n_all):
    """按拷问成绩分岔：答不上来直接是「用完」，答上了才有得选。

    以前这里一次把两条路都写死（truly_seen / used_as_tool），于是后面
    那张四选一卡片选什么都改不了结局——玩家看着四个选项，结局早定了。
    现在答对只记「答上了」，走哪条路由玩家自己选（见他选完的那一步，
    loop.choose_card 里写 truly_seen 或 final_collapse）。
    """
    need = finale_pass_n(n_all)
    ok = n_all > 0 and n_ok >= need
    apply_effect(s, {"psyche": 10 if ok else -8})
    if not ok:
        # 答不上来：这些深夜你记得的是「有人陪我」，不是「她是谁」。
        s["flags"].add("used_as_tool")
        s.setdefault("_fired", set()).add("used_as_tool")
    s["flags"].add("finale_done")
    s.setdefault("_fired", set()).add("finale_done")
    clamp(s)
    return ("real_seen" if ok else "fake_tool"), ok


def draw_line(s, world, rng):
    opts = draw_line_all(s, world)
    if not opts:
        return None
    # 每条线每周都各自有机会推动（不按 stage 序号排队，否则一条线会把别的饿死）
    # 玩家已经走进的那条线权重高一档：一季六周，线一慢就永远走不到收口那一拍。
    wts = []
    for line, st in opts:
        lid = line["_meta"]["id"]
        base = 1.0 + 0.35 * st["stage"]
        if lid in s["story"]:
            base += 1.2                      # 已经在这条线里了
        if lid == "zhong":
            # 重线每出现一次就自动 +1 stage，若再按 stage 加权就会滚雪球：
            # 第一次被她撞上以后，私联/恋爱几乎再也抽不到（实测 8 周 4 张全重线）。
            # 她本来就「一直在那儿」，不需要用权重去抢；封住成长加成即可。
            base = 1.0 + (0.45 if lid in s["story"] else 0.0)
        if lid == "shiren" and "crossed_line" not in s["flags"]:
            # 还没越线时，给私联一点「可能被搭话」的底量；
            # 否则玩家还没看见她就被重线挡在门外，如影随形只能靠运气。
            base += 0.6
        if lid == "shiren" and "crossed_line" in s["flags"]:
            # 越了线就是真的在过另一种日子：这条线每一拍都得往前走，
            # 否则八周里只轮得到两三次，永远停在「刚加微信」那一拍。
            base *= 2.6
        if lid == "romance" and (s.get("relation_A") or 0) >= 50:
            base *= 2.4                      # 阿棠关系够了就该轮到她，别被重线永远压着
        wts.append(base)
    return rng.choices(opts, weights=wts, k=1)[0]


def draw_line_all(s, world):
    """这一周有哪条线能往前推。

    一季只走一条线：主线一旦定下，另外两条不再出现（哪怕它们本身还开着）。
    主线没定之前三条都能出现——玩家就是在这几周里挑。
    """
    main = mainline(s)
    opts = []
    for line in world["lines"]:
        lid = line["_meta"]["id"]
        if main and lid != main:
            continue
        if line_locked(s, line):
            continue
        st = line_stage(s, line)
        if st:
            opts.append((line, st))
    return opts


# ---------------------------------------------------------------- 一周三拍
#  平日（3 个动作，各花一点体力/时间）→ 版聊（微博：可选）→ 周末（Live + 特典会）
ACTS = {
    "dance": {"name": "练舞", "stamina": -18, "dance": 6.0, "money": -40, "weibo": "练舞"},
    "sing": {"name": "练唱", "stamina": -18, "sing": 6.0, "money": -40, "weibo": "练唱"},
    "mc": {"name": "对着镜子练营业的话", "stamina": -10, "mc": 5.0, "money": -20, "weibo": "练话"},
    "content": {"name": "拍内容发微博", "stamina": -8, "fame": 1.5, "psyche": -1.5, "money": 0, "weibo": "拍"},
    "work": {"name": "开直播", "stamina": -22, "money": 380, "fame": 2.0, "weibo": ""},
    "rest": {"name": "躺一整天", "stamina": 28, "psyche": 2.0, "weibo": ""},
}


RENT = 900
FEE = 620          # 一周的场租+分成（和 loop.py 里那一份保持一致）
FEE_FIRST = 160    # 场地第一次给新人便宜
SKILL_CAP = 100     # 舞/唱/live 话术的上限：每次练都足额加，到 100 才停
ACT_REPEAT = {"dance": 0.5, "sing": 0.5, "mc": 0.5, "content": 0.8,
              "work": 1.6, "rest": 1.8}


def do_act(s, act, rng):
    """一天做一件事。一周六个晚上可排（周末那场自带），体力按「一天一件」算。

    连续做同一件事会递减，但递减只削增益、不削体力消耗——
    连着练三晚舞，第二晚开始涨得少，累是一样累。
    """
    a = ACTS.get(act)
    if not a:
        return
    last = s.get("_last_act")
    mult = ACT_REPEAT.get(act, 1.0) if last == act else 1.0
    for k in ("stamina", "money", "dance", "sing", "mc", "fame", "psyche"):
        if k not in a:
            continue
        v = a[k] * (1.0 if k == "stamina" else mult)
        if k == "fame":
            add_fame(s, v)
        else:
            s[k] += v
    if a.get("weibo"):
        s["weibo_posts"] = s.get("weibo_posts", 0) + 1
    s["acted"] = act
    s["_last_act"] = act
    # 硬上：体力已经见底还去练、还开播，这一下是从心理那里借的
    if s["stamina"] <= 0 and act in ("dance", "sing", "mc", "work"):
        s["psyche"] -= 5
        s["pushed_while_spent"] = s.get("pushed_while_spent", 0) + 1
        s["_last_act_spent"] = True          # 给界面用：这一下是硬上的
    # 态度会走样：为了流量连着开播、或者靠拍内容维持热度，台上那套话就越说越像模板
    if act == "work":
        s["template"] = min(1.0, s["template"] + 0.018)
    elif act in ("dance", "sing", "mc"):
        s["template"] = max(0.0, s["template"] - 0.015)
    elif act == "content":
        s["template"] = min(1.0, s["template"] + 0.008)
    s.setdefault("_acts_week", []).append(act)
    clamp(s)


def policy_tone(s, policy):
    """这一周开口的调子：说算数的实话，还是把话说好。"""
    if hasattr(policy, "tone"):
        return policy.tone(s)
    return "truth" if s.get("true_talk", 0) == 0 and s["template"] < 0.35 else "safe"


TALKS = [
    ("tired", "下班的路上", "今天排完舞我坐在排练室的地上没起来，脚背磨破了。"),
    ("scared", "收工以后", "今天有一场我上台前一直在数拍子，怕忘。"),
    ("lonely", "回家的地铁上", "有时候我觉得这半年跟我说话的人很少。"),
    ("money", "算账的时候", "房租这次是勉强凑上的，还差一点。"),
    ("why", "睡不着的时候", "我也不知道我为什么要一直跳下去，可停下来我不知道做什么。"),
]


def _pick_talk(s, rng, tone, report):
    """版聊里发出去的那条：说真话，或者发一张好看的照片。"""
    s["talk_seen"] = s.get("talk_seen", 0) + 1
    if tone == "truth":
        key, where, line = TALKS[(s["talk_seen"] - 1) % len(TALKS)]
        s["true_talk"] = int(s.get("true_talk") or 0) + 1
        s["true_talks"] = s.get("true_talks", 0)
        s["true_talks"] = s.get("true_talks", 0)
        s["true_streak"] = s.get("true_streak", 0) + 1
        s["template"] = max(0.0, s["template"] - 0.03)
        # 说得太难听，会有人不喜欢：说真话不是免费的
        add_fame(s, -1)
        s["psyche"] = s.get("psyche", 0) + 3
        report.append(("talk", key))
        return where, line
    s["true_streak"] = 0
    s["weibo_posts"] = s.get("weibo_posts", 0) + 1
    s["template"] = min(1.0, s["template"] + 0.02)
    add_fame(s, 1.5)
    report.append(("talk", "photo"))
    return "配图发出去以后", "今天也谢谢大家，明天见。"


def do_week(s, world, rng, policy=None):
    """跑一周：平日 3 个动作 → 版聊 → 组内/剧情线 → OTA 互动 → 周末 Live + 特典会。
    policy(s, card, options) -> option_index"""
    policy = policy or (lambda s, c, o: rng.randrange(len(o)))
    s["_acts_week"] = []
    report = []
    s["beat"] = 0

    # ---- 平日：三个动作（真玩家不会天天三份工；钱够就先练）
    rest_n = 0
    for _ in range(3):
        act = policy.act(s) if hasattr(policy, "act") else rng.choice(list(ACTS))
        do_act(s, act, rng)
        report.append(("act", act))
        if act == "rest":
            rest_n += 1
    # 最后一季的「躺」不是偷懒，是放手：一周里躺过两拍以上的人，
    # 很可能已经决定这季跳完就不跳了（现生快乐 / 散场走这条路）
    if s["week"] >= s.get("weeks_total", 8) and rest_n >= 2 and s["psyche"] >= 50:
        s["chose_leave"] = True
        report.append(("leave", "这季跳完就不跳了"))
    # 一周排满、身体一直空着：这周是从心理里借出来的
    if s["stamina"] < 15:
        s["psyche"] -= 5
        s["spent_weeks"] = s.get("spent_weeks", 0) + 1
        clamp(s)
        report.append(("spent", "这一周身体一直是空的"))
    s["_rng"] = rng
    if s["stamina"] < 25:
        s["nights_stamina_low"] = s.get("nights_stamina_low", 0) + 1
    # 没钱睡不好：体力清零的后半夜是拿心理换的（原来这里叠着扣 8+12，等于一周掏空 20）
    if s["stamina"] < 10:
        s["psyche"] -= 6
        clamp(s)
        report.append(("burnout", "体力见底"))
    # 房租：第八天要交。交得起就真扣；交不上才是原来那套惩罚。
    # 以前只有惩罚分支、没有扣款行——每周念着要交 900，钱包永远不减。
    if s["week"] % 2 == 1:
        if s["money"] >= RENT:
            s["money"] -= RENT
            report.append(("rent", "房租交了"))
        else:
            s["psyche"] -= 18
            s["stamina"] -= 10
            s["rent_missed"] = True
            clamp(s)
            report.append(("rent_due", "房租没交上"))

    # ---- 版聊：顺手发一条，回/不回
    r = rng.uniform(0, 1)
    if r < 0.6:
        c = draw(s, world, rng, kinds=["OTA互动", "OTA相处的瞬间"])
        if c and c.get("options"):
            slots = cast(s, c, rng, world) or {}
            oi = policy(s, c, c["options"]); oi = 0 if oi is None else oi
            apply_option(s, c["options"][oi], rng, slots, card=c)
            s["cooldown"][c["id"]] = int(c.get("cooldown", 3))
            report.append(("bbs", c["id"], c["options"][oi]["id"]))
        else:
            c = None
    else:
        c = None

    # ---- 剧情线（优先）否则抽一张团内/日常
    # 剧情线是一周三拍的其中一拍，不能接连两周霸占同一个位置：
    # 上周推过、这周也还是同一条线在可推状态时，先让位一次。
    o_line = None
    s["_line_tick"] = s["week"]
    lr = draw_line(s, world, rng)
    if lr and rng.random() < 0.45:
        line, st = lr
        v = rng.choice(st["variants"])
        oi = policy(s, {"_line": line, "_stage": st}, v["options"]); oi = 0 if oi is None else oi
        o = v["options"][oi]
        _snap = {k: s.get(k, 0) for k in ("zhong", "zhongs", "heat", "heart")}
        _remember_chaser(s, line, v, rng)
        apply_option(s, o, rng, slots={})
        # 剧情线的推进量以前靠选项自己写 immediate.zhong，但那些选项绝大多数只写 zhongs，
        # 结果是重线永远停在 stage 0。推进量在引擎这一层补，选项只管写「她攒下的」。
        _lid = line["_meta"]["id"]
        if (_snap["zhong"] or 0) >= (s.get("zhong") or 0):
            s["zhong"] = (_snap["zhong"] or 0) + 1
        if _lid == "shiren" and (_snap["heat"] or 0) >= (s.get("heat") or 0):
            s["heat"] = (_snap["heat"] or 0) + 1
        if _lid == "romance" and (_snap["heart"] or 0) >= (s.get("heart") or 0) and o.get("advance"):
            s["heart"] = (_snap["heart"] or 0) + 1
        if _lid == "romance" and st["stage"] == 0 and (s.get("heart") or 0) == 0:
            s["heart"] = 1          # 她主动靠近这件事本身就是第一次心动
        # 数值链（2026-11-14）：重线是「被一个人缠上」，它每推进一拍，
        # 「私生」这条线也会跟着往前一点——原先没有任何东西给 shiroi 加数，
        # 导致 shiroi 那 8 张卡整季一次都开不了。私联则一点一点把开盒风险垫高。
        if _lid == "zhong":
            _add = 12 if st["stage"] >= 3 else 8
            s["shiroi"] = float(s.get("shiroi") or 0) + _add
        if _lid == "shiren":
            s["kaibox"] = float(s.get("kaibox") or 0) + 4
        o_line = _lid
        s["story"][_lid] = {"stage": st["stage"]}
        s["_last_line"] = _lid
        s["_line_week"] = s.get("_line_week", {})
        s["_line_week"][_lid] = s.get("_line_tick", s["week"])
        report.append(("story", _lid, st["stage"], o["id"]))
    elif draw_line(s, world, rng) is not None and rng.random() < 0.55:
        # 这周有剧情线能推，但这一轮没落下来（45% 才落）：给点「正在发生」的份量。
        # 不给的话，一季里「私生/板子/开盒」这些量几乎是零——被一个人的事正在酝酿，
        # 但玩家还没被拉到台前，就是这么一种感觉：日子一天天过去，风在别处起。
        line, st = draw_line(s, world, rng)
        _lid = line["_meta"]["id"]
        if _lid == "zhong":
            s["shiroi"] = float(s.get("shiroi") or 0) + 4
        elif _lid == "shiren":
            s["kaibox"] = float(s.get("kaibox") or 0) + 3
            s["heat"] = float(s.get("heat") or 0) + 0.5
        report.append(("line_simmer", _lid, st["stage"]))
    if not o_line and s["week"] >= 2 and rng.random() < 0.55:
        # 剧情线没落下来的那一周，这一拍的重量给「一句算数的实话」：
        # 说真话这个行为在卡库里几乎没有位置（285 个选项没有语气标记），
        # 不在这里给一次机会，空心就是人人都会掉进去的坑。
        _tone = "truth" if policy_tone(s, policy) == "truth" else "safe"
        _pick_talk(s, rng, _tone, report)
    # 环境/日常是「这一周的天」，不该跟一张要我做选择的卡抢同一个位置：
    # 每种类型各给一次独立机会，让十天里至少有几件是天气和小事。
    for _kinds in (["ambient"], ["日常"], ["private", "私联恋爱", "私生", "私生跟踪"]):
        a = draw(s, world, rng, kinds=_kinds)
        if a is not None and a.get("effect"):
            apply_effect(s, a["effect"])
            s["cooldown"][a["id"]] = int(a.get("cooldown", 3))
            report.append(("ambient", a["id"]))
    # 团内的事 / 外部的压力 / 半夜的小事，各给一次独立机会：
    # 以前全挤在「中段那一抽」里，一周只有一张要我做选择的卡，队友关系几乎刷不动。
    for _kinds in (["团内", "团内关系"], ["外部", "external", "外部舆论", "舞台事故"],
                   ["daily"], ["团内", "团内关系", "positive", "ota"], ["external", "外部", "外部舆论"]):
        d = draw(s, world, rng, kinds=_kinds)
        if d is None:
            continue
        if d.get("effect"):
            apply_effect(s, d["effect"])
            report.append(("ambient", d["id"]))
        elif d.get("options"):
            _slots = cast(s, d, rng, world) or {}
            _oi = policy(s, d, d["options"]); _oi = 0 if _oi is None else _oi
            apply_option(s, d["options"][_oi], rng, _slots, card=d)
            report.append(("card", d["id"], d["options"][_oi]["id"]))
        s["cooldown"][d["id"]] = int(d.get("cooldown", 3))
    # 「外面在说我」：板子和炎上原来只能靠卡面那零点几，玩家很难感觉到风向。
    # 人气上来了就一定会被讨论——每过一周按人气涨一点，被骂的那部分才累积成炎上。
    # 2026-11-15 收紧：原来每张外部/私生卡都走一遍加上 ×0.04，八周一季能磨到 90；
    # 现在只在这一周「真的出了外部的事」时才起风，而且按人气分档。
    if any(r and r[0] == "card" and isinstance(r[1], str) and r[1].startswith("ext_") for r in report):
        _f = float(s.get("fame") or 0)
        if _f > 0:
            s["banzi"] = float(s.get("banzi") or 0) + min(6.0, _f * 0.06)
            if s.get("bold") or s.get("weibo_posts"):
                s["enjou"] = float(s.get("enjou") or 0) + min(4.0, _f * 0.04)
    if True:
        c = draw(s, world, rng, kinds=["daily", "external", "ambient", "positive", "团内", "团内关系", "外部舆论", "舞台事故", "私生", "私生跟踪"])
        if c is not None:
            if c.get("effect"):
                apply_effect(s, c["effect"])
                report.append(("ambient", c["id"]))
            elif c.get("options"):
                slots = cast(s, c, rng, world) or {}
                oi = policy(s, c, c["options"]); oi = 0 if oi is None else oi
                apply_option(s, c["options"][oi], rng, slots, card=c)
                report.append(("card", c["id"], c["options"][oi]["id"]))
            s["cooldown"][c["id"]] = int(c.get("cooldown", 3))

    # ---- 特典会：她来了、她坐下、她开口（OTA 互动 / 回考）
    s["beat"] = 1
    chosens = warm_ota(s)
    used = set()
    day = 0
    while day < 2:
        c, who = ota_pick(s, world, rng, [o for o in chosens if o["id"] not in used])
        if c is None or who is None:
            break
        used.add(who["id"])
        day += 1
        slots = cast(s, c, rng, world) or {}
        if not slots:
            slots = {"speaker": who}
        opts = c["options"]
        # 回考第二拍：按「记性」蒙对
        oi = policy(s, c, opts); oi = 0 if oi is None else oi
        apply_option(s, opts[oi], rng, slots, card=c)
        s["cooldown"][c["id"]] = int(c.get("cooldown", 3))
        report.append(("ota", c["id"], opts[oi]["id"], who["name"]))

    # ---- Live 结算
    s["beat"] = 2
    # 今晚还剩多少力气：体力归零扣 8 分，满体力加 2 分
    fatigue = (s["stamina"] - 50) / 50 * 5.0
    sc = stage_score(s) + fatigue + rng.uniform(-5, 5)
    if sc >= 64:
        tier = "神场"
        add_fame(s, 8); s["psyche"] += 3; s["gorshou"] = s.get("gorshou", 0) + 1
        for o in s["ota"]:
            o["stick"] += 3
    elif sc >= 54:
        tier = "好场"
        add_fame(s, 5); s["psyche"] += 1
        for o in s["ota"]:
            o["stick"] += 2
    elif sc >= 44:
        tier = "平场"
        add_fame(s, 2)
    elif sc >= 34:
        tier = "冷场"
        s["psyche"] -= 4
        for o in s["ota"]:
            o["stick"] -= 1.5
    else:
        tier = "翻车"
        s["psyche"] -= 8; s["enjou"] += 3
        for o in s["ota"]:
            o["stick"] -= 2.5
    s["max_single"] = max(s["max_single"], sc)
    # 冷场/翻车要留档：外部卡「翻车那一下被拍下来了」就是靠这个开门的
    if tier in ("冷场", "翻车"):
        s["blew_it"] = int(s.get("blew_it") or 0) + 1
    # 心气塌了还上台：一晚算一次，攒够两次就是「台上那十分钟」
    if s["psyche"] < 20:
        s["played_while_collapsing"] = True
    clamp(s)
    # 特典收入
    income = weekly_income(s)
    s["money"] += income - (FEE_FIRST if s["week"] == 1 else FEE)
    if s["money"] < 0:   # 欠款不能靠余额挡住：直接判「这一周撑不下去」
        s["psyche"] -= 10
        s["stamina"] -= 5
        s["money"] = 0
    s["_income_last"] = income
    if income >= 560:
        s["psyche"] += 2          # 台下坐满的时候，人是会高兴的
    # 一条线的推进靠「钱/心理」这些共用资源表达不了，必须显式加一步：关掉一整季
    # 才发现三条线永远卡在第一拍，是因为没人给 heat/心动/进度加过数
    if o_line == "shiren":
        s["heat"] = s.get("heat", 0) + 1
    elif o_line == "romance":
        s["heart"] = s.get("heart", 0) + 1
    elif o_line == "zhong":
        s["zhong"] = s.get("zhong", 0) + 1
    if income < 240:
        s["low_income_weeks"] = s.get("low_income_weeks", 0) + 1
        s["psyche"] -= 6          # 台下空着回家的那个晚上
    # 收入走势：骂声带来新人还是赶走老人，就看最后两周比峰值掉了多少
    _prev_peak = s.get("income_peak", 0)
    s["income_now"] = income
    if income > _prev_peak:
        s["income_peak"] = income
    elif s["week"] >= 4 and _prev_peak and income < _prev_peak * 0.85:
        s["income_falling"] = True   # 季末在掉：人正在走
    if everyone_gone(s):          # 所有人的黏性都掉到 30 以下：这一季不会再有别人了
        s["psyche"] -= 10
    # 「你是不是有点累」：模板化够高、又被黏着的那个人逮住问了一句的时候，
    # 这段话是不是真心，当场就要我表态。选「继续照这套说」= 空心（当季结束）。
    # 但只有「这一季一次真话都没说过」才会被问——空心与守住本心是同一把尺的两头。
    if ((not s.get("empty_asked")) and s["week"] >= 3
            and int(s.get("truth_pick") or 0) + int(s.get("safe_pick") or 0) >= 2
            and truth_rate(s) <= 0.25):
        _warm = [o for o in s["ota"] if o["stick"] >= 45]
        if _warm:
            s["empty_asked"] = True
            s["empty_asked_who"] = _warm[0]["name"]
            report.append(("empty_asked", "%s：「你是不是有点累。」" % _warm[0]["name"]))
    # 运营递过来的那条会火的路：第一次是明确的拒绝时刻（「守住本心」的入口），
    # 之后还会再来提——再来时答应它，就转去「你第一天知道我的恶劣吗」。
    if (not s.get("offer_seen")) and s["week"] >= 4:
        s["offer_seen"] = True
        _offers = ["炒 CP"]
        s["offer_kind"] = _offers[(s["week"] - 3) % 1]
        report.append(("offer", "运营：%s 这条能火，做不做？" % s["offer_kind"]))
    # 延迟队列：本场结束的先结，本周末发生的全部结
    # （「下周」是相对**下一场 live**说的，不是「下个月」——
    #   以前只结「下周」，一季下来能积压 30 条没兑现的效果）
    settle_delayed(s, world, rng)
    cool_down(s)
    clamp(s)                      # 这一拍里所有散装加法都要收口，别把心理算到 102
    # 最后一周，人已经累了，还是站上去把这一场跳完 = 「再跳一场」。
    # 选了离开的人不算（彗星是「留在台上的人」的结局）。
    if s["week"] >= s.get("weeks_total", 8) and not s.get("chose_leave"):
        s["last_live_choice"] = True
    s["week"] += 1
    for o in s["ota"]:
        o["weeks_known"] += 1
    return {"tier": tier, "score": sc, "report": report}


def _ids(world, types):
    return set(c["id"] for c in world["cards"] if c.get("type") in types)


# ---------------------------------------------------------------- 结局
def baoshou(s, true_talk):
    """「还没塌」。季末体力永远是 0（六天排满、一周一场），所以这里不看体力，
    体力只在平时按周给惩罚。说真话也不再是门槛：它属于守住本心的入口，
    不该顺手把散场也发给不开口的人。"""
    return (s["psyche"] >= 45 and relavg(s) >= 40
            and sum(1 for o in s["ota"] if o["stick"] >= 40) >= 3)


def _num_of(cond):
    """从 {'>=': 40} 这种单键字典里取值。"""
    for k, v in cond.items():
        return float(v)
    return 0.0


def _cmp_with(v, op, x):
    return v >= x if op == ">=" else (v <= x if op == "<=" else (v > x if op == ">" else v < x))


def truth_rate(s):
    """这一季开口的「真话率」：带 tone 标记的选项里，说实话占多少。

    分母只数玩家真的做过选择的语气点（卡面/空场回答），不把版聊和回考算进去——
    版聊是自动生成的，回考答对是「记得住」，两者都不是「我肯不肯说真话」。
    """
    t = int(s.get("truth_pick") or 0)
    f = int(s.get("safe_pick") or 0)
    n = t + f
    return (t / n) if n else 0.0


def _extra(key, s, true_talk):
    if key == "truth_rate":
        return truth_rate(s)
    if key == "shiren_stage":
        # 私联线走到第几拍：-1 = 这一季根本没见过她。
        # 「如影随形」不能只靠开盒数字高——没真正私联过，被开盒也只是普通的风险。
        return int(((s.get("story") or {}).get("shiren") or {}).get("stage", -1))
    if key == "truth_pick":
        return int(s.get("truth_pick") or 0)
    if key == "tone_choices":
        return int(s.get("truth_pick") or 0) + int(s.get("safe_pick") or 0)
    if key == "empty_choice":
        # 「你是不是有点累」那一下我怎么回的：reply=还是用那套话（空心），truth=说了真的
        return s.get("empty_choice") or ""
    if key == "relavg":
        return relavg(s)
    if key == "max_share":
        return max_share(s)
    if key == "beibao":
        # 「被包养」只认显式的 flag：苦养计数（kuyang_count）数的是「欠了几次人情」，
        # 那是关系走远的记账，不等于有人把我包了。
        return "beibao" in s["flags"]
    if key == "true_cog":
        return true_talk >= 1
    if key == "true_talk":
        return true_talk
    if key == "offer_refused":
        # 运营递来那条会火的路，我当面拒了：这是「守住本心」的入口，不是心理分能替代的东西
        return s.get("offer_choice") == "refuse"
    if key == "template":
        return s["template"]
    if key == "chose_leave":
        return s["chose_leave"]
    if key == "rent_missed":
        return s.get("rent_missed", False)
    if key == "ota_ge40_count":
        return sum(1 for o in s["ota"] if o["stick"] >= 40)
    if key == "max_single":
        return s["max_single"]
    if key == "relavg":
        return relavg(s)
    if key == "min_rel":
        # 任一队友关系很差（残局）：三人里最低的那个
        return min(s["relation_A"], s["relation_B"], s["relation_C"])
    if key == "last_live":
        return bool(s["last_live_choice"])
    if key == "played_while_collapsing":
        return bool(s.get("played_while_collapsing"))
    if key == "money_drop":
        # 结局文档的定义：这一季特典收入在掉——季末最后两周明显低于本季峰值，
        # 或者至少两周连最低线都够不着
        return bool(s.get("income_falling")) or s.get("low_income_weeks", 0) >= 2
    if key == "money_kept":
        # 「恶劣」要的是钱没掉：被骂出来的热度真的换成了人和钱
        return not (bool(s.get("income_falling")) or s.get("low_income_weeks", 0) >= 2)
    if key == "not_baoshou":
        return not baoshou(s, true_talk)
    if key == "no_rent_missed":
        return not s.get("rent_missed", False)
    if key == "pushed":
        # 「硬上」次数：体力见底还在练/还开播
        return int(s.get("pushed_while_spent") or 0)
    return s.get(key, 0)


def check_cond(cond, s, true_talk):
    """求值 endings.json 的 cond 结构：
    {'field': {'>=':x}} / {'any':[{...}]} / {'all':[...]} / {'not_baoshou': True}"""
    if not isinstance(cond, dict):
        return True
    for k, v in cond.items():
        if k == "any":
            if not any(check_cond(x, s, true_talk) for x in v):
                return False
        elif k == "all":
            if not all(check_cond(x, s, true_talk) for x in v):
                return False
        elif k in ("not_baoshou", "no_rent_missed"):
            # 写 true = 要求成立；写 false = 这一项不做约束（不是「要求它为假」）
            val = (not baoshou(s, true_talk)) if k == "not_baoshou" else (not s.get("rent_missed", False))
            if bool(v) and not val:
                return False
        elif isinstance(v, dict):
            cur = _extra(k, s, true_talk)
            for op, x in v.items():
                if op in (">=", "<=", ">", "<", "=="):
                    if not _cmp_with(cur, op, float(x)):
                        return False
        elif isinstance(v, (bool, str)):
            # 字符串型条件（如 "empty_choice": "reply"）直接比；布尔照旧
            # 写 false = 这一项不做约束，继续看后面的键（不能直接 return True，
            # 否则它后面的条件全被跳过）
            if not bool(v):
                continue
            if not bool(_extra(k, s, true_talk) == (v if isinstance(v, str) else True)):
                return False
        else:
            return True
    return True


def judge(s, world, true_talk=None):
    """按 data/endings.json 的判决表判定。提前结束先判。"""
    if true_talk is None:
        true_talk = int(s.get("true_talk") or 0)
    fl = s["flags"]
    for e in world["endings"]["early"]:
        if e["trigger"]["flag"] in fl:
            return e["name"], True
    for f in world["endings"]["flow"]:
        if check_cond(f.get("cond"), s, true_talk):
            return f["name"], False
    return "散场", False


def run_season(world, seed=0, policy=None, verbose=False, empty_choice="reply", offer_choice="refuse", weeks=None):
    """empty_choice="reply" = 继续照那套话回（空心）；"truth" = 说一句真话。"""
    rng = random.Random(seed)
    s = new_state(world, rng=rng)
    for _ in range(int(weeks or s["weeks_total"])):
        do_week(s, world, rng, policy)
        if s.get("empty_asked") and s.get("empty_choice") is None:
            s["empty_choice"] = empty_choice
        if s.get("offer_seen") and s.get("offer_choice") is None:
            s["offer_choice"] = offer_choice
            if offer_choice == "take":
                s["enjou"] = min(100.0, s["enjou"] + 30)   # 那条路真的会火，也真的会烧
                add_fame(s, 12)
    name, early = judge(s, world, s.get("true_talk", 0))
    s["ended"] = name
    return s, name, early


if __name__ == "__main__":
    w = load_world()
    print("cards:", len(w["cards"]), "lines:", len(w["lines"]))
    s, name, early = run_season(w, seed=1)
    print("seed 1 ->", name, "| psyche", s["psyche"], "| stage", round(stage_score(s), 1),
          "| money", round(s["money"]), "| enjou", s["enjou"])


# ---------------------------------------------------------------- 进度（给界面显示）


def soft_cap_psyche(v, cap=85.0):
    """心理的软上限：过了 85 以后每加一点只算四分之一。
    这一行练习和钱一样是会边际递减的，不该到季末人人 100。"""
    if v <= cap:
        return v
    return cap + (v - cap) * 0.25


def weekly_income(s):
    """这一场卖券的钱。人数由 warm_ota 定（人气决定来几个人，铁杆必到），
    每张 80 块——和界面账单用的是同一份 bill.py，不能各算各的。"""
    import bill as _B
    who = warm_ota(s)
    return float(_B.weekly_bill(s, who)["yen"])


def tier_name(v):
    """舞/唱/话术的统一档位：给玩家一个「现在算什么水平」。"""
    if v >= 70:
        return "压得住整场"
    if v >= 60:
        return "站得住"
    if v >= 50:
        return "像样了"
    if v >= 40:
        return "能看"
    if v >= 30:
        return "生疏"
    return "不会"


def next_tier(v):
    """离下一档还差多少（0 表示已经是最高档）。"""
    for t in (30, 40, 50, 60, 70):
        if v < t:
            return t - v
    return 0


def act_gain(s, act):
    """这个动作这一次会涨多少（连做就减半），给界面标「+4 / +2」用。"""
    a = ACTS.get(act) or {}
    mult = ACT_REPEAT.get(act, 1.0) if s.get("_last_act") == act else 1.0
    return int(round(float(a.get(act, 0)) * mult)) if a.get(act) else 0
