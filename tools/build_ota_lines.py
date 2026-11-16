# -*- coding: utf-8 -*-
"""构建种子 OTA 个人线（A 档）：data/storylines/storyline_ota_<id>.json。
先做「盐渍水母」(ota_jelly, 重力系/女友粉/拉拉) 一条给用户看味道，认可后再加其余四条。

与私联线的区别（DESIGN §6.5 待做条目）：
- 不赌开盒、不交拷问；重在『人设纵深化』——把一个网名做成一个人。
- 三拍：被选中(名字有主了) → 摊开(她敢给我看她到底是谁) → 定位(我到底把她放在哪个位置)。
- 对象固定（种子 OTA），不选角槽；数值打固定键 ota_jelly。
- 推进条 heat（贴合度），语义=她离『安全的距离』有多近；越高越危险，但不直接判结局，只写 flag 交结局系统。
- 每个越界选项必须同时给 money / 黏性，并加 kaibox / shiroi / enjou —— 不许把『给联系方式』写成纯赚。
- learns = 『人设记忆点』，二周目『回指』用；本期不做拷问。

非游戏代码，内容构建脚本，保留。改文案改这里再跑，别手改 json。
"""
import json, os

BASE = r"C:\Users\kk\Documents\deepseek-harness\default-workspace\聚场\data\storylines"
os.makedirs(BASE, exist_ok=True)


def opt(oid, label, desc, immediate, advance, learns=None, flags=None, delayed=None,
        rq=None, note=None):
    o = {"id": oid, "label": label, "desc": desc, "immediate": immediate,
         "advance": advance, "learns": learns, "flags": flags or [], "delayed": delayed or []}
    if rq:
        o["rq"] = rq
    if note:
        o["note"] = note
    return o


def dl(when, effect, note, condition=None):
    d = {"when": when, "effect": effect, "note": note}
    if condition:
        d["condition"] = condition
    return d


def rq(cid, why):
    """回考：在这道选项之后，插入一次『她提了一句、我三选一』的记忆考核。

    题面与选项全部来自 data/ota_memory.json（按 cid 取），这里只写『为什么在这一刻考』
    与『考的是哪一条』。运行时：若本局尚未刷出该 cid 的线索（她还没说过），则静默跳过。
    """
    return {"clue": cid, "reason": why}


# ============================================================
# 盐渍水母 · 三拍
# ============================================================

jelly = {
    "_meta": {
        "kind": "storyline",
        "id": "ota_jelly",
        "name": "盐渍水母 · 个人线",
        "category": "种子 OTA 个人线（A 档）",
        "subject": {"ota_id": "ota_jelly", "name": "盐渍水母", "archetype": "重力系",
                    "fan_type": "女友粉", "tags": ["拉拉", "社恐", "重力系"]},
        "design_note": (
            "种子专属个人线。和私联线不同：不赌开盒、不交拷问、**不越出站姐与偶像的关系边界**，"
            "重在『人设纵深化』——把一个网名做成一个人。"
            "三拍 = 被选中（从『全团都爱的人』变成『某一个人的』）→ 摊开（她敢给我看她到底是谁、怕什么）"
            "→ 定位（我到底把她放在哪个位置）。由 heat（贴合度）推进：越高，她离『安全的距离』越近，"
            "但不直接判结局，只写 flag（jelly_goddess / jelly_crossline / jelly_demoted）交结局系统。"
            "关键立场：把一个人留在心里，不需要走到她的生活里去——第三条分歧必须是真的出口，不是坏选项。"
        ),
        "resource_keys": {
            "money": "钱", "stamina": "体力", "psyche": "心理", "fame": "人气", "stage": "舞台稳定",
            "ota_all": "全体OTA黏性", "ota_jelly": "盐渍水母",
            "relation_A": "阿棠", "relation_B": "露露", "relation_C": "小满", "relation_all": "团内关系整体",
            "shiren": "私联人数", "enjou": "炎上", "kaibox": "开盒风险", "shiroi": "私生跟踪", "banzi": "板子关注度",
        },
        "advance_metric": "heat",
        "advance_name": "贴合度",
        "subject_schema": "固定对象 ota_jelly（不选角、不孵化）。数值键 ota_jelly 直接作用；文案写死她的网名「盐渍水母」是允许的（她本人就是这条线的主角）。",
        "memory_key": {
            "jelly_birthday": {"kind": "fact", "label": "她生日那天被落在幼儿园"},
            "jelly_insect": {"kind": "fact", "label": "她怕虫子，怕到会假笑"},
            "jelly_grandma": {"kind": "fact", "label": "外婆走后，她把想说的话都放进糖罐和贴纸里"},
            "jelly_lockscreen": {"kind": "fact", "label": "她锁屏是一张糊掉的live照"},
            "jelly_third_row": {"kind": "fact", "label": "她每场都坐第三排左边，说那儿灯不刺眼"},
            "jelly_notebook": {"kind": "fact", "label": "她有一本写满没发出去的话的本子"},
            "jelly_my_name": {"kind": "fact", "label": "我把自己的名字写在了她那本子的最后一页"},
            "jelly_opened": {"kind": "fact", "label": "她开始给我看她不发光的那一面"},
            "jelly_answered_in_kind": {"kind": "fact", "label": "我回给她的是一张同样手写的东西"},
            "jelly_kept_distance": {"kind": "fact", "label": "我拿工作关系把她挡回去了"},
            "jelly_manager": {"kind": "fact", "label": "我把糖罐交给了运营"},
            "jelly_used": {"kind": "fact", "label": "我用了她的力气，用了她的喜欢"},
            "jelly_misread": {"kind": "fact", "label": "我用一句客气话把她的真心盖住了"},
            "jelly_not_lonely": {"kind": "fact", "label": "她说从没喜欢过男生，等着一件很坏的事落下"},
            "jelly_boundary_talk": {"kind": "fact", "label": "我告诉她有些距离是我要给自己留的"},
            "food_hate": {"kind": "choice", "q": "她不吃什么", "pool": ["香菜", "折耳根", "葱"]},
            # ---- 记忆回考线索（题面/选项/反应见 data/ota_memory.json，这里只登记她说过哪些细节）----
            "fruit_craving": {"kind": "fact", "label": "她念叨过想吃的水果"},
            "daily_drink": {"kind": "fact", "label": "她下午三点续命的那一杯"},
            "pet_dream": {"kind": "fact", "label": "她壁纸上看两年的那只"},
            "weather_hate": {"kind": "fact", "label": "她最受不了的天气"},
            "loop_song": {"kind": "fact", "label": "她单曲循环的那首歌"},
            "commute": {"kind": "fact", "label": "她每天最不想醒的那趟车"},
            "snack": {"kind": "fact", "label": "她包里常年那包零食"},
            "phone_app": {"kind": "fact", "label": "她手机里最常打开的那个"},
            "work_file": {"kind": "fact", "label": "她这周一直在改的东西"},
            "off_work": {"kind": "fact", "label": "她几点才下班"},
            "pet_type": {"kind": "fact", "label": "她家养的那只"},
            "dream_place": {"kind": "fact", "label": "她一直没去成的地方"},
            "family_pressure": {"kind": "fact", "label": "她家里一直在催的那件事"},
            "money_habit": {"kind": "fact", "label": "她最舍得的那个花钱去处"},
            "commuter_route": {"kind": "fact", "label": "她来一趟要怎么折腾"},
            "first_visit": {"kind": "fact", "label": "她第一次来看 live 的原因"},
            "spare_thing": {"kind": "fact", "label": "她没在追团的话会去做的事"},
            "alone_reason": {"kind": "fact", "label": "她这么常来的真正原因"},
            "what_keeps": {"kind": "fact", "label": "她说会一直来的理由"},
            "prev_group": {"kind": "fact", "label": "她上一个团是怎么散场的"},
        },
        "schema": (
            "stages[i] = {stage:int, key, title, gate, enter_heat, variants[3], note?}；"
            "variant = {id, title, narrative, options[2-4]}；"
            "option = {id, label, desc, immediate:{res:delta}, advance:int(贴合度增量), "
            "learns:'记忆点key'|list|None, flags:[...], delayed:[{when,condition?,effect,note}], note?}。"
        ),
    },
    "stages": [
        # ================= 拍0 被选中 =================
        {
            "stage": 0, "key": "chosen", "title": "被选中",
            "gate": "周 ≥ 1 且 盐渍水母黏性 ≥ 75（追了半年，第一次收到她的『神对应』宣言）",
            "enter_heat": 0,
            "note": "这一拍只写一件事：网名有了主人。所有选项都不会结束线，只有『收下这份表白』才会真正开线并让她开始追踪。",
            "variants": [
                {
                    "id": "chosen_sticker",
                    "title": "贴纸和她自己的手算",
                    "narrative": (
                        "第二轮特典，她排到我的列。递过来一只没封口的牛皮纸袋，我抽出来，是一沓贴纸——"
                        "每一张都手写了日期和场次，从半年前那场没人来的开始。最上面一张，是我的名字后面画了一颗水母。"
                        "『水母触手是朝外收的。』她盯着桌沿小声说，『收紧了，才抓得住。』"
                        "她的手在抖，券的边角被捏得起毛。"
                    ),
                    "options": [
                        opt("ch_thank", "把贴纸一张张翻完，说『原来你都在』", "接住这份记了半年的东西",
                            {"ota_jelly": 6, "psyche": 5, "stamina": -2}, 1, ["jelly_birthday"],
                            ["jelly_chosen"],
                            None, rq('first_visit', '她肯把半年的贴纸翻给我看，顺口就说起了第一场'), note="她愣了半拍，笑得很大声，又立刻捂住嘴，眼睛亮得像刚哭过"),
                        opt("ch_hurry", "道谢，说下一位在排队", "把时间还给队伍",
                            {"ota_jelly": -6, "psyche": -3}, 0, None, ["jelly_kept_distance"],
                            note="她「哦」了一声，把贴纸收回袋子时动作很轻，像收一件易碎品"),
                        opt("ch_joke", "开玩笑说水母蜇人吗", "用玩笑试探她到底想说到几分",
                            {"ota_jelly": 3, "psyche": 2, "stamina": -2}, 1, None, ["jelly_chosen"],
                            note="她想了想：『蜇人的那种，是叫海月水母吧。我不是。』"),
                    ],
                },
                {
                    "id": "chosen_umbrella",
                    "title": "雨里那把伞是歪的",
                    "narrative": (
                        "散场的时候下大雨，场馆门口挤成一片，staff在喊别淋湿了。我没带伞，站在雨棚下等雨小。"
                        "她把伞收着走过来，另一只手攥着一把没打开的伞，隔着雨棚递过来：『我多带了一把。』"
                        "递的时候伞把一直往我这边歪，她半个肩膀露在雨里，头发贴在脸上，还是站得很直。"
                        "后面还有人排着队等她签完那几张券，她也没催，就那样等着。"
                    ),
                    "options": [
                        opt("cu_share", "把自己的外套给她披上，说冷的话换我淋", "第一次主动朝她伸手",
                            {"ota_jelly": 8, "psyche": 4, "stamina": -3}, 1, ["jelly_insect"],
                            ["jelly_chosen"],
                            None, rq('weather_hate', '雨里站了这么久，她抱怨了一句天气'), note="她抓着外套领子不敢动，说『我怕虫子进了衣服里』，声音闷在袖子里"),
                        opt("cu_awkward", "把伞推回去，说这样两个人都要感冒", "把关系拉回『工作人员与客人』",
                            {"ota_jelly": -4, "psyche": 2}, 0, None, ["jelly_kept_distance"],
                            note="她点头说好的，收伞收得很慢，像在等一句话，可我只说了谢谢"),
                        opt("cu_text", "说『下次雨天别站着等了』，说这话时看着她的伞", "把一件小事变成一句限定在特典会里的话",
                            {"ota_jelly": 5, "psyche": 3, "stamina": -2}, 1, ["jelly_lockscreen"],
                            ["jelly_chosen"],
                            note="她愣了一下，忽然很用力地点头：『好。』——好得像是答应了另一件事"),
                    ],
                },
                {
                    "id": "chosen_third_row",
                    "title": "她永远坐在第三排左边",
                    "narrative": (
                        "我数明白了：每场她都坐第三排，靠左，正好能看见侧台我补妆的镜子。"
                        "灯光扫过去的时候，全场的脸都是黑的，只有那一小块永远有反光——她在擦脸上的汗，"
                        "擦得很小声，怕影响别人。可轮到我对着台下说完最后一句 live 的时候，她永远是第一个抬手，"
                        "举了很久才放下来，像怕举早了不算数。"
                    ),
                    "options": [
                        opt("ct_look", "live 收尾的时候，正好看向那个方向", "让她知道我看见她了",
                            {"ota_jelly": 7, "psyche": 4, "stamina": -2}, 1, ["jelly_lockscreen"],
                            ["jelly_chosen", "jelly_has_a_place"],
                            note="她把手在膝盖上按了一下，才跟着别人一起把手举起来"),
                        opt("ct_ignore", "把视线收回来，对着全场说话", "别让一个人独占我的眼睛",
                            {"ota_jelly": -5, "fame": 2, "psyche": 3}, 0, None, ["jelly_kept_distance"],
                            note="散场她买了券，排到一半又转身走了，券留下了，人没留下"),
                        opt("ct_ask", "下场后在自己的特典列问她，为什么总坐那个位置", "把这件事当面问出来",
                            {"ota_jelly": 5, "psyche": -2, "stamina": -4}, 1, ["jelly_third_row"],
                            ["jelly_chosen"],
                            None, rq('alone_reason', '她刚说了坐第三排的理由，话说开了就停不下来'), note="她别过头：『因为那儿的灯不刺眼。』——可那一块明明是最晃眼的"),
                    ],
                },
            ],
        },
        # ================= 拍1 摊开 =================
        {
            "stage": 1, "key": "spill", "title": "摊开",
            "gate": "贴合度 ≥ 1（线已开，且她开始比别的粉丝更靠近）",
            "enter_heat": 1,
            "note": "这一拍的核心是『她敢给我看她到底是谁』——本子里那些没发出去的话。**本线不越出站姐边界**：不私下见面、不换联系方式、不加开盒/私生。把关系推出去的事全部交给私联线。",
            "variants": [
                {
                    "id": "spill_notebook",
                    "title": "三十条没发出去的消息",
                    "narrative": (
                        "她从托特包里掏出一个线装本，摊开给我看。每一页都是一条没发出去的话，"
                        "写了日期，写了又划掉。最新的一条是昨晚：「今天咳嗽了三次，第二声的时候我差点冲上台」。"
                        "她手压着纸边：『我知道这样很怪。但我没地方放这些话——微博上发出去，就是所有人都能看见的了。』"
                        "托特包侧袋露出半板药盒——标签被撕掉了，只剩边缘一点自己手写的字。"
                        "后面还有人排着队，她把本子翻到最新那页就停住，没有再往后翻。"
                    ),
                    "options": [
                        opt("sn_accept", "把本子合上，说这些话以后可以当面说", "把她从纸里拉到人前",
                            {"ota_jelly": 8, "psyche": 5, "stamina": -2}, 1, ["jelly_notebook"],
                            ["jelly_opened"],
                            None, rq('off_work', '她收起本子，随口抱怨了一句下班时间'), note="她翻回自己最新那一页，看了很久，然后拿起笔，在那行字后面画了一个小小的勾",),
                        opt("sn_quiz", "一条条读下去，问她为什么划掉", "把她的秘密变成一场『看得见』的游戏",
                            {"ota_jelly": 6, "psyche": -4, "stamina": -3}, 2, ["food_hate"],
                            ["jelly_opened", "jelly_leaning"],
                            None, rq('work_file', '她越说越快，说到自己一天怎么过的'), note="她越说越快，说到『我晚上不吃香菜，怕嘴里有味道』的时候，自己笑了，像在承认一件很重要的罪",),
                        opt("sn_recoil", "说这样会让我很怕", "先划出一条线",
                            {"ota_jelly": -7, "psyche": 6}, 0, None, ["jelly_kept_distance"],
                            note="她把本子塞回包里，说抱歉，抱歉，就那样走了，背影很直"),
                        opt("sn_reply_name", "在本子最后一页写：『我叫——』，然后是自己的名字", "让她知道那行字后面是个真人",
                            {"ota_jelly": 8, "fame": 2, "psyche": -3, "stamina": -2}, 1,
                            ["jelly_my_name"], ["jelly_opened", "jelly_answered_in_kind"],
                            [dl("条件", {"enjou": 3}, "她把那一页拍了照，配了一句话发到超话，底下一片『好羡慕』跟一串问号", condition="炎上 ≥ 40")],
                            rq('commute', '她看我写下名字，话头松了，说起自己怎么来的'), note="她看着那三个字看了很久，说：『原来你写字的时候，最后一笔会往上挑。』"),
                    ],
                },
                {
                    "id": "spill_rain_bench",
                    "title": "两把伞，一把没用",
                    "narrative": (
                        "特典结束，她在门口没走。站在我对面，另一只手一直攥着一把没打开的伞。"
                        "『我想说件事，说完就走。』她说得很慢，像在每个字上面铺一层砖。"
                        "『我从没喜欢过男生。以前开不了这个口，现在也不想再编一个出来。』"
                        "雨砸在雨棚上，她说完就低下头，等着一件很坏的事落下。"
                    ),
                    "options": [
                        opt("sb_hold", "说：『我也是这里的人，你不用跟我解释』", "先把位置平了，再听她说完",
                            {"ota_jelly": 9, "psyche": 6, "stamina": -2}, 1, ["jelly_not_lonely"],
                            ["jelly_opened"],
                            None, rq('spare_thing', '她说完最重的一句，反而敢说轻的'), note="她抬起头，眼睛里全是雨。『真的？』她问了两次，第二次几乎没声音",),
                        opt("sb_redirect", "说：这跟团的事无关，但别在门口说", "保护她，也保护自己",
                            {"ota_jelly": -3, "psyche": 4}, 0, None, ["jelly_kept_distance"],
                            note="她说好，把伞收进包里，走的时候很稳，比来的时候还稳"),
                        opt("sb_cliche", "说『没关系，我不介意』", "用一句客气话把话盖过去",
                            {"ota_jelly": -5, "psyche": -3}, 0, None, ["jelly_misread"],
                            note="她笑了一下，那种笑我心见过很多次，在营业的时候也用"),
                    ],
                },
                {
                    "id": "spill_stage_door",
                    "title": "后台门缝里的一罐糖",
                    "narrative": (
                        "后台门缝里塞进来一罐水果糖，罐子上有一段手写的字：「你说过上台前会嗓子干。」"
                        "罐底贴着便利贴：『我外婆走那年，我学会把想说的话都放在东西里，因为放嘴上会被说矫情。』"
                        "糖罐里有一张对折的纸，上面写着：『我不是要你回什么。就是想让你知道，我没有把偶像当成许愿池。』"
                    ),
                    "options": [
                        opt("sd_keep", "把纸折好，放进口袋里，上台前又把糖罐的位置记住", "把这句话收下，它够勇敢了",
                            {"ota_jelly": 7, "psyche": 6, "stamina": -2}, 1, ["jelly_grandma"],
                            ["jelly_opened"],
                            None, rq('snack', '糖罐收下了，她开始说别的零食'), note="演出结束她没出现。罐子在后台台子上放了两天，没人敢动"),
                        opt("sd_reply", "在纸上回一句：『我也有话，等哪天没人排队了说』", "把一本正经的甜变成一场暗战",
                            {"ota_jelly": 8, "psyche": 3, "stamina": -3}, 2, ["jelly_grandma"],
                            ["jelly_opened", "jelly_leaning"],
                            [dl("条件", {"enjou": 4}, "后台门被staff拍下来了，有人说『给粉丝塞东西的人原来在里面』", condition="炎上 ≥ 40")],
                            rq('loop_song', '两个人开始有一搭没一搭地聊歌'), note="下一场她排到最后，只剩两分钟。她把糖罐放在桌上，说了三个字：「我等你。」后面没有句号"),
                        opt("sd_manager", "把糖交给运营处理", "让机构替我做决定",
                            {"ota_jelly": -8, "psyche": -4, "fame": 1}, 0, None, ["jelly_manager"],
                            note="运营把糖罐扔进垃圾桶，说这些东西不能进后台。我说我知道。"),
                    ],
                },
            ],
        },
        # ================= 拍2 定位 =================
        {
            "stage": 2, "key": "placement", "title": "定位",
            "gate": "贴合度 ≥ 2（她离得够近了，这一季必须给她一个位置）",
            "enter_heat": 2,
            "note": "收场拍：三个分歧，都不直接判结局。第三个『把她放回第三排』必须是真的出口——不是坏选项，而且只有它能让下赛季她还留着。本线不出现私下见面 / 换联系方式，把关系推出站姐边界的事一律交给私联线。",
            "variants": [
                {
                    "id": "placement_dm",
                    "title": "她在等一个答案",
                    "narrative": (
                         "她递应援卡的时候，卡背面写满了一页，最后一句单独成行：『你有没有想过，你对我，其实一点都不了解。』"
                         "我捏着那张卡，忽然想起我确实不知道她做什么，不知道她几点上班，不知道她为什么总在第三排。"
                         "我只知道她买几张券、排几次队。后面还有三个人在等，她大概也在等我一个答案。"
                    ),
                    "options": [
                        opt("pl_give", "把卡翻到正面，说：『那你多告诉我一点，我想记住的是你这个人』", "把关系从『买票的人』改成『一个具体的人』",
                            {"ota_jelly": 9, "psyche": 4, "stamina": -3}, 1,
                            ["food_hate", "jelly_insect"], ["jelly_goddess", "jelly_leaning"],
                            [dl("下周", {"enjou": 4}, "她在超话说起我发现她怕虫子，底下一片『连这个都记得』，也有人在问我是怎么知道的", condition="炎上 ≥ 30")],
                            note="她说你问吧，问三句，我答三句，答完就不许再说了解我。她答得比谁都慢，每个字都挑过"),
                        opt("pl_boundary", "说：我不知道，但有些距离是我要给自己的", "坦白这份关系有上限",
                            {"ota_jelly": -4, "psyche": 8}, 0, None, ["jelly_demoted"],
                            note="她点了下头，去旁边等着，过了两轮才回来，回来时补了一句：『你这样说，我心里反而踏实。』"),
                        opt("pl_use", "把她往应援的方向引，说『你是我最强的后援』", "把她的用力变成台上的力气",
                            {"ota_jelly": 6, "fame": 4, "money": 200, "psyche": -5}, 1, ["jelly_boundary_talk"],
                            ["jelly_goddess", "jelly_used"],
                            [dl("下周", {"enjou": 6}, "她包下了我全部的应援物，粉丝群开始有人讨论『那个人是谁』")],
                            note="她立刻说要加钱做板，语气像在领一个任务，很快乐，又空"),
                        opt("pl_honest", "说：『我只把你当重要的人，但不能是那样』", "把话说得难听，但是真的",
                            {"ota_jelly": -10, "psyche": -6, "stage": 3}, 0, None,
                            ["jelly_demoted", "jelly_hurt_honest"],
                            [dl("条件", {"ota_jelly": -10}, "她的第三排空了很久，每场都空", condition="她黏性 ≤ 40")],
                            note="她把卡收回包里，说了声『好的』。那个字很轻，像早就准备好了"),
                    ],
                },
                {
                    "id": "placement_ledger",
                    "title": "墙上那本她订的人",
                    "narrative": (
                        "后台墙上一本『会员档案』，她的那一页我翻了很久：满页都是购票记录、应援物、"
                        "连着六场都到场。最后写着一行小字，是她自己填的：「想被记住的理由：没有。」"
                        "她推门进来的时候，正看到我在翻那一页，站在门口没动，很轻地笑了一下："
                        "『这就是我全部的值钱了，对吧。』"
                    ),
                    "options": [
                        opt("pg_rewrite", "拿起笔在她的那一页上写：『这个人爱吃糖，怕虫子，说不喜欢香菜』", "把她从一本账里拽出来",
                            {"ota_jelly": 9, "psyche": 7, "stamina": -2}, 1, ["food_hate"],
                            ["jelly_goddess"],
                            None, rq('daily_drink', '借本子的时候她在旁边等，随口要一杯'), note="她没说话，走过来看了很久，最后把那行字拍下来换成锁屏",),
                        opt("pg_close", "合上本子，说这本不该让人看见", "把一段关系关回它应该在的抽屉里",
                            {"ota_jelly": -5, "psyche": 5}, 0, None, ["jelly_demoted"],
                            note="她点头说：『那我不打扰你翻这一页了。』，退出去很轻"),
                        opt("pg_borrow", "问她能不能把这本借我，我想记住每个人的理由", "把她的页变成全体的页",
                            {"ota_jelly": 5, "fame": 3, "psyche": -3, "stamina": -2}, 1, None, ["jelly_goddess", "jelly_used"],
                            note="她笑着把笔递给我，笑得很配合，眼睛却不在笑"),
                    ],
                },
                {
                    "id": "placement_before_final",
                    "title": "最后一场之前",
                    "narrative": (
                         "这一季最后一场之前的那次特典会，她排到最后，把一张票放在桌上，票夹里夹着一张纸条："
                         "『我坐在第三排看了半年，从来没敢问你要一个答案。我知道偶像不该给答案，但我不是来许愿的。』"
                         "纸条背面还有几行被划掉的字，划得很用力，纸都破了。她把手收回去，说票是买给自己的。"
                         "后面已经没有人了，staff 在收桌子，我忽然分不清，我到底是不想负责，还是从来没有被这么认真地对待过。"
                    ),
                    "options": [
                        opt("pf_answer_stage", "下一场开场前，对着第三排把话说完：『我记得你是你，不是一个答案』", "把回答放在所有人在的地方",
                            {"ota_jelly": 8, "fame": 3, "psyche": -2, "stamina": -2}, 1,
                            ["jelly_insect"], ["jelly_goddess", "jelly_answer_given"],
                            [dl("下周", {"enjou": 5}, "那段发言被人剪出来，标题是『她对着台下说记得你是你』，底下吵得厉害")],
                            rq('family_pressure', '她说完重的话，事后再来提一句家里的催促'), note="我说完看了一眼第三排，她低着头，肩在抖，没有抬头"),
                        opt("pf_answer", "在那张票的票夹上写一句：『你对我来说很重要，但重要不代表要在一起』", "把答案给回去，但不是她要的那个",
                            {"ota_jelly": -6, "psyche": 5}, 0, None, ["jelly_demoted", "jelly_answer_given"],
                            None, rq('pet_type', '她把票夹收回去，重新变得客气，说起家里的猫狗'), note="她把票夹夹回包里，说了声谢谢，走时背影很直，像已经得到答案"),
                        opt("pf_promise", "把票收好，说：『这一季最后一场的安可，我留一句话在第三排那个位置』", "把决定推到一个还看得见的日期",
                            {"ota_jelly": 5, "psyche": 3, "stamina": -2}, 1, None, ["jelly_third_row", "jelly_goddess"],
                            [dl("下周", {"ota_jelly": 4}, "她真的来了，坐在原处，安可那一刻把手举得很高")],
                            rq('fruit_craving', '她把决定往后推，两人都在找别的话说'), note="她问：『那句话，是写给第三排的，还是写给我的？』我没敢回这一句"),
                    ],
                },
            ],
        },
    ],
}


def write(doc, suffix):
    out = os.path.join(BASE, "storyline_ota_%s.json" % suffix)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)
        f.write("\n")
    stages = doc["stages"]
    print("WROTE", os.path.basename(out))
    print("  stages:", len(stages), "| variants:", [len(s["variants"]) for s in stages],
          "| options:", [len(v["options"]) for s in stages for v in s["variants"]])


if __name__ == "__main__":
    write(jelly, "jelly")