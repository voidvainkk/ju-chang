# -*- coding: utf-8 -*-
"""全库复验：卡片 + 剧情线。
1) JSON 合法 2) narrative POV(剥离引号内对白后不应出现"你") 3) 纯赚检查
   4) 残留写死真名(种子里允许的五个 OTA 名不应出现在 narrative) 5) @槽位键无漏网
非游戏代码，保留。"""
import json, os, re, glob

BASE = r"C:\Users\kk\Documents\deepseek-harness\default-workspace\聚场\data"
CARDS = os.path.join(BASE, "cards")
STORY = os.path.join(BASE, "storylines")

BAD = {"enjou", "kaibox", "shiroi", "banzi"}           # 越高越糟
SEED_NAMES = ["盐渍水母", "第零排", "今天也不困", "蓝色耳机线", "过期胶卷"]
QUOTE_RE = re.compile(r"『[^』]*』|「[^」]*」|「[^」]*」|\"[^\"]*\"|'[^']*'|“[^”]*”")

def strip_quotes(s):
    return QUOTE_RE.sub("", s)

def check_pov(text):
    return "你" in strip_quotes(text)

def is_pure_profit(immediate, delayed):
    # 纯赚 = 所有即时变化都是"好"的，且没有任何延迟负面（正反两面都要有代价）
    if not immediate:
        return False
    for k, v in immediate.items():
        if k.startswith("@"):
            continue                  # 指定某一个人的黏性：不是全局资源，不按纯赚判
        if k in BAD:
            if v > 0:
                return False          # 即时让 BAD 涨 = 有代价
        else:
            if v < 0:
                return False          # 即时让好资源跌 = 有代价
    # 即时全好；只要有任何一条延迟负面，就不是纯赚
    for dl in (delayed or []):
        for k, v in (dl.get("effect") or {}).items():
            if (k in BAD and v > 0) or (k not in BAD and v < 0):
                return False
    return True

problems = []
total_cards = 0
for fn in sorted(glob.glob(os.path.join(CARDS, "*.json"))):
    try:
        d = json.load(open(fn, encoding="utf-8"))
    except Exception as e:
        problems.append(("BADJSON", fn, str(e))); continue
    for c in d.get("cards", []):
        total_cards += 1
        cid = c.get("id", "?")
        nar = c.get("narrative", "")
        if check_pov(nar):
            problems.append(("POV", fn, cid))
        for sn in SEED_NAMES:
            if sn in nar:
                problems.append(("HARDNAME", fn, cid, sn))
        if "options" in c:
            for o in c["options"]:
                # 记忆回考的正确值选项只给正分，那是设计意图（答错的那两个才是代价），不按纯赚判
                if o.get("rq_pick"):
                    continue
                if is_pure_profit(o.get("immediate", {}), o.get("delayed", [])):
                    problems.append(("PUREPROFIT", fn, cid, o.get("id")))
        # @键漏网：effect 键不应直接等于种子 id
        effs = []
        if c.get("effect"): effs.append(c["effect"])
        for o in c.get("options", []):
            if o.get("immediate"): effs.append(o["immediate"])
            for dl in o.get("delayed", []):
                if dl.get("effect"): effs.append(dl["effect"])
        for e in effs:
            for k in e:
                if k in ("ota_jelly","ota_row0","ota_sleepy","ota_earphone","ota_film"):
                    problems.append(("LITERALKEY", fn, cid, k))

print("CARD FILES OK, total_cards =", total_cards)

# ---- storyline ----
story_files = sorted(glob.glob(os.path.join(STORY, "*.json")))
st_problems = []
_story_docs = []
for fn in story_files:
    try:
        _story_docs.append((fn, json.load(open(fn, encoding="utf-8"))))
    except Exception as e:
        st_problems.append(("BADJSON", fn, str(e)))
# 记忆点池 = 所有剧情线登记的 key 并集（私联线的 key 可被其他线复用）
KNOWN_MEM = set()
for _fn, _d in _story_docs:
    KNOWN_MEM |= set((_d.get("memory_key") or {}).keys())
    KNOWN_MEM |= set(((_d.get("_meta") or {}).get("memory_key") or {}).keys())
for fn, d in _story_docs:
    for st in d.get("stages", []):
        for var in st.get("variants", []):
            if check_pov(var.get("narrative", "")):
                st_problems.append(("POV", st["key"], var["id"]))
            if check_pov(var.get("title", "")):
                st_problems.append(("POV_TITLE", st["key"], var["id"]))
            for o in var.get("options", []):
                if is_pure_profit(o.get("immediate", {}), o.get("delayed", [])):
                    st_problems.append(("PUREPROFIT", st["key"], var["id"], o["id"]))
                if check_pov(o.get("label", "")) or check_pov(o.get("desc", "")):
                    st_problems.append(("POV_OPT", st["key"], var["id"], o["id"]))
                # learns 的 key 必须在任一剧情线的 memory_key 池里登记过
                lk = o.get("learns")
                if lk:
                    for k in ([lk] if isinstance(lk, str) else lk):
                        if k not in KNOWN_MEM:
                            st_problems.append(("UNKNOWN_LEARN", st["key"], var["id"], o["id"], k))
    fin = d.get("finale", {})
    for fc in fin.get("final_choices", []):
        if is_pure_profit(fc.get("immediate", {}), fc.get("delayed", [])):
            st_problems.append(("PUREPROFIT_FINALE", fin["key"], fc["id"]))
print("STORY FILES:", [os.path.basename(x) for x in story_files])
print("STORY stages:", sum(len(json.load(open(x, encoding='utf-8')).get('stages', [])) for x in story_files))

# ---- ota_memory 线索池（记忆回考） ----
mem_problems = []
mem_path = os.path.join(BASE, "ota_memory.json")
mem_keys = set()
if os.path.exists(mem_path):
    md = json.load(open(mem_path, encoding="utf-8"))
    PROTO = set(md["_meta"]["archetypes"].keys())
    # ota_memory 自带登记表（个人线砍掉后线索的登记处在这里）
    KNOWN_MEM |= set((md.get("_meta") or {}).get("memory_key") or {})
    for c in md.get("clues", []):
        ck = c.get("key")
        mem_keys.add(ck)
        if ck not in KNOWN_MEM:
            mem_problems.append(("UNREGISTERED_CLUE", ck))
        if c.get("level") not in ("light", "mid", "heavy"):
            mem_problems.append(("BAD_LEVEL", ck, c.get("level")))
        if len(c.get("set") or []) != 3 or len(set(c["set"])) != 3:
            mem_problems.append(("BAD_SET", ck, c.get("set")))
        if len(c.get("ask") or []) != 3:
            mem_problems.append(("BAD_ASK", ck, len(c.get("ask") or [])))
        for fld in ("react_good", "react_bad"):
            got = set((c.get(fld) or {}).keys())
            if got != PROTO:
                mem_problems.append((fld.upper(), ck, sorted(PROTO - got)))
        body = " ".join([c.get("say", "")] + list(c.get("ask") or [])
                        + list((c.get("react_good") or {}).values())
                        + list((c.get("react_bad") or {}).values()))
        if "{truth}" not in c.get("say", ""):
            mem_problems.append(("NO_TRUTH_IN_SAY", ck))
        for ph in re.findall(r"\{(\w+)\}", body):
            if ph not in ("truth", "wrong"):
                mem_problems.append(("BAD_PLACEHOLDER", ck, ph))
        if check_pov(body):
            mem_problems.append(("POV_CLUE", ck))
    print("MEMORY clues:", len(md.get("clues", [])))

# 剧情线里引用的回考 clue 必须真实存在
for fn, d in _story_docs:
    for st in d.get("stages", []):
        for var in st.get("variants", []):
            for o in var.get("options", []):
                r = o.get("rq")
                if r and r.get("clue") not in mem_keys:
                    mem_problems.append(("UNKNOWN_CLUE_REF", st["key"], var["id"], o["id"], r.get("clue")))

# ---- OTA 选角选择器：casting.select 里的 archetype / fan_type 必须真实存在 ----
pool_path = os.path.join(BASE, "ota_pool.json")
sel_problems = []
if os.path.exists(pool_path):
    _pool = json.load(open(pool_path, encoding="utf-8"))
    VALID_ARCH = set(a["id"] for a in _pool.get("archetypes", []))
    VALID_FT = set()
    for _a in _pool.get("archetypes", []):
        VALID_FT |= set(_a.get("fan_types") or [])
    for fn in sorted(glob.glob(os.path.join(CARDS, "*.json"))):
        _d = json.load(open(fn, encoding="utf-8"))
        for _c in _d.get("cards", []):
            for _cs in (_c.get("casting") or []):
                _sel = _cs.get("select") or {}
                _ar = _sel.get("archetype")
                _ft = _sel.get("fan_type")
                if _ar and _ar not in VALID_ARCH:
                    sel_problems.append(("BAD_CAST_ARCH", _c["id"], _cs.get("slot"), _ar))
                if _ft and _ft not in VALID_FT:
                    sel_problems.append(("BAD_CAST_FAN_TYPE", _c["id"], _cs.get("slot"), _ft))

# ---- 回考两拍卡组的结构校验（rq_lock / rq_pick / rq_drop / max_clues_per_run）----
recall_path = os.path.join(CARDS, "ota_recall.json")
recall_problems = []
if os.path.exists(recall_path):
    _rd = json.load(open(recall_path, encoding="utf-8"))
    _rmeta = _rd.get("_meta") or {}
    if not isinstance(_rmeta.get("max_clues_per_run"), int):
        recall_problems.append(("NO_MAX_CLUES", _rmeta.get("max_clues_per_run")))
    for _c in _rd.get("cards", []):
        _stage = (_c.get("_meta") or {}).get("rq_stage")
        _k = (_c.get("_meta") or {}).get("clue")
        if _stage not in ("say", "ask"):
            recall_problems.append(("BAD_RQ_STAGE", _c["id"], _stage))
        if _k not in mem_keys:
            recall_problems.append(("RECALL_BAD_CLUE", _c["id"], _k))
        if _stage == "say":
            _locks = [o for o in _c["options"] if o.get("rq_lock")]
            if len(_locks) != len(_c["options"]):
                recall_problems.append(("SAY_NOT_ALL_LOCK", _c["id"], len(_locks), len(_c["options"])))
            _drops = [o for o in _c["options"] if o.get("rq_drop")]
            if len(_drops) != 1:
                recall_problems.append(("SAY_DROP_COUNT", _c["id"], len(_drops)))
            elif not _drops[0].get("delayed"):
                recall_problems.append(("DROP_NO_PENALTY", _c["id"]))
        elif _stage == "ask":
            _picks = [o for o in _c["options"] if o.get("rq_pick")]
            if len(_picks) != 3:
                recall_problems.append(("ASK_PICK_COUNT", _c["id"], len(_picks)))
            _trues = [o for o in _picks if (o["rq_pick"] or {}).get("choice") == "true"]
            if len(_trues) != 1:
                recall_problems.append(("ASK_TRUE_COUNT", _c["id"], len(_trues)))

# ---- 序章 data/intro.json ----
intro_problems = []
intro_path = os.path.join(BASE, "intro.json")
if not os.path.exists(intro_path):
    intro_problems.append(("MISSING_INTRO", intro_path))
else:
    _intro = json.load(open(intro_path, encoding="utf-8"))
    _ib = _intro.get("base_state") or {}
    for _k in ("money", "stamina", "psyche", "fame", "dance", "sing", "mc"):
        if not isinstance(_ib.get(_k), int):
            intro_problems.append(("INTRO_BAD_BASE", _k, _ib.get(_k)))
    _chs = _intro.get("choices") or []
    if len(_chs) != 3:
        intro_problems.append(("INTRO_CHOICE_COUNT", len(_chs)))
    if len(_intro.get("text") or []) < 3:
        intro_problems.append(("INTRO_TEXT_SHORT", len(_intro.get("text") or [])))
    for _c in _chs:
        if check_pov(_c.get("label", "") + _c.get("desc", "") + _c.get("after", "")):
            intro_problems.append(("INTRO_POV", _c.get("id")))
        if not (_c.get("effect") or {}):
            intro_problems.append(("INTRO_NO_EFFECT", _c.get("id")))
    for _t in (_intro.get("text") or []) + (_intro.get("after_quote") or []):
        if check_pov(_t):
            intro_problems.append(("INTRO_TEXT_POV", _t[:14]))

# ---- 判决表 data/endings.json ----
end_problems = []
end_path = os.path.join(BASE, "endings.json")
if not os.path.exists(end_path):
    end_problems.append(("MISSING_ENDINGS", end_path))
else:
    _ed = json.load(open(end_path, encoding="utf-8"))
    _fields = set(_ed.get("fields") or {})
    _flow = _ed.get("flow") or []
    _early = _ed.get("early") or []
    _meta = _ed.get("_meta") or {}
    _counts = _meta.get("counts") or {}
    # 结局条数以 _meta.counts 为准：11 季末 + N 提前。
    # 提前结局会随着新写的路线增加（2026-11-15 加了第 17 个「控制不了」），
    # 所以这里不再写死 11/5，只核对两张表内部是否自洽。
    if _counts.get("season") != len(_flow) or _counts.get("early") != len(_early):
        end_problems.append(("END_COUNT_MISMATCH", _counts, len(_flow), len(_early)))
    if _counts.get("total") not in (None, len(_flow) + len(_early)):
        end_problems.append(("END_TOTAL_MISMATCH", _counts.get("total"),
                             len(_flow) + len(_early)))
    if not _flow or not _early:
        end_problems.append(("END_TABLE_EMPTY", len(_flow), len(_early)))
    if _flow and _flow[-1].get("name") != "散场":
        end_problems.append(("END_NO_FALLBACK", _flow[-1].get("name")))
    _ns = [e.get("n") for e in _flow] + [e.get("n") for e in _early]
    if _ns != list(range(1, len(_ns) + 1)):
        end_problems.append(("END_BAD_NUMBERING", _ns))
    _names = [e.get("name") for e in _flow] + [e.get("name") for e in _early]
    if len(set(_names)) != len(_names):
        end_problems.append(("END_DUP_NAME", _names))
    # 图鉴文案：每个结局都要有 core/style/hint，且不能有野键
    lore_path = os.path.join(BASE, "endings_lore.json")
    if not os.path.exists(lore_path):
        end_problems.append(("MISSING_LORE", lore_path))
    else:
        _lore = json.load(open(lore_path, encoding="utf-8"))
        _lkeys = set(_lore) - {"_meta"}
        for _n in _names:
            if _n not in _lkeys:
                end_problems.append(("LORE_MISSING", _n))
                continue
            for _k in ("core", "style", "hint"):
                if not str((_lore.get(_n) or {}).get(_k) or "").strip():
                    end_problems.append(("LORE_FIELD_EMPTY", _n, _k))
        for _n in sorted(_lkeys - set(_names)):
            end_problems.append(("LORE_UNKNOWN", _n))
    for _e in _flow:
        if not _e.get("why"):
            end_problems.append(("END_NO_WHY", _e.get("name")))
        for _f in (_e.get("cond") or {}):
            if _f in ("any", "all", "not_baoshou", "no_rent_missed"):
                continue
            if _f not in _fields:
                end_problems.append(("END_UNKNOWN_FIELD", _e.get("name"), _f))
        for _alt in ((_e.get("cond") or {}).get("any") or []):
            for _f in _alt:
                if _f not in _fields:
                    end_problems.append(("END_UNKNOWN_FIELD_ANY", _e.get("name"), _f))
    for _e in _early:
        if not (_e.get("trigger") or {}).get("flag"):
            end_problems.append(("END_EARLY_NO_FLAG", _e.get("name")))
    _pc = _ed.get("panel_counts") or []
    if len(_pc) != 6:
        end_problems.append(("END_PANEL_COUNT", len(_pc)))

# ---- 艺名库 data/idol_names.json ----
name_problems = []
names_path = os.path.join(BASE, "idol_names.json")
if not os.path.exists(names_path):
    name_problems.append(("MISSING_IDOL_NAMES", names_path))
else:
    _nd = json.load(open(names_path, encoding="utf-8"))
    _styles = _nd.get("styles") or []
    if len(_styles) < 3:
        name_problems.append(("TOO_FEW_STYLES", len(_styles)))
    _all = []
    for _s in _styles:
        _ns = _s.get("names") or []
        if len(_ns) < 10:
            name_problems.append(("STYLE_TOO_FEW", _s.get("id"), len(_ns)))
        for _x in _ns:
            if len(_x) > 4:
                name_problems.append(("NAME_TOO_LONG", _s.get("id"), _x))
            if _x in _all:
                name_problems.append(("NAME_DUP", _x))
            _all.append(_x)
        for _f in ("id", "name", "desc"):
            if not _s.get(_f):
                name_problems.append(("STYLE_MISSING", _s.get("id"), _f))
    # 主角名不能撞队友名（团里只有阿棠/露露/小满三个人）
    for _team in ("阿棠", "露露", "小满"):
        if _team in _all:
            name_problems.append(("NAME_HITS_TEAMMATE", _team))

print("\n== CARD PROBLEMS ==", len(problems))
for p in problems: print("  ", p)
print("== STORY PROBLEMS ==", len(st_problems))
for p in st_problems: print("  ", p)
print("== MEMORY PROBLEMS ==", len(mem_problems))
for p in mem_problems: print("  ", p)
print("== RECALL PROBLEMS ==", len(recall_problems))
for p in recall_problems: print("  ", p)
print("== CASTING PROBLEMS ==", len(sel_problems))
for p in sel_problems: print("  ", p)
print("== INTRO PROBLEMS ==", len(intro_problems))
for p in intro_problems: print("  ", p)
# ---- 结局正文：endings.json 里每个结局都要在 结局.md 有章节、且抠得出非空正文 ----
# 对齐 game/loop.py:1676 ending_text()：正文夹在 **正文**（散场是 **内核** 后面）与 **结算面板** 之间。
# 2026-11-15 收进常驻校验：此前改写 16 篇正文后一直靠临时脚本核验，容易漏。
_md_path = os.path.join(BASE, "..", "结局.md")
if not os.path.isfile(_md_path):
    end_problems.append(("END_NO_TEXT_FILE", _md_path))
else:
    _et_ed = json.load(open(end_path, encoding="utf-8"))
    _all_end = (_et_ed.get("flow") or []) + (_et_ed.get("early") or [])
    with open(_md_path, encoding="utf-8") as _f:
        _src = _f.read()
    _chapters = {}
    for _ch in _src.split("## ")[1:]:
        _lines = _ch.splitlines()
        if _lines:
            _chapters[_lines[0]] = _ch
    for _e in _all_end:
        _nm = _e.get("name")
        _hit = [v for k, v in _chapters.items() if _nm and _nm in k]
        if not _hit:
            end_problems.append(("END_NO_CHAPTER", _nm))
            continue
        _b = _hit[0]
        _start = _b.find("**正文**")
        if _start >= 0:
            _start += len("**正文**")
        else:
            _k = _b.find("**内核**")
            _start = _b.find(chr(10) + chr(10), _k) if _k >= 0 else -1
        _tail = _b.find("**结算面板**", _start if _start > 0 else 0)
        _body = _b[_start:_tail if _tail > 0 else len(_b)].strip() if _start > 0 else ""
        if len(_body) < 80:
            end_problems.append(("END_NO_BODY", _nm, len(_body)))
    _numbered = [k for k in _chapters if k and k[0].isdigit()]
    if len(_numbered) != len(_all_end):
        end_problems.append(("END_CHAPTER_COUNT", len(_numbered), len(_all_end)))
print("== ENDINGS PROBLEMS ==", len(end_problems))
for p in end_problems: print("  ", p)
print("== NAMES PROBLEMS ==", len(name_problems))
for p in name_problems: print("  ", p)
