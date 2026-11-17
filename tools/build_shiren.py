# -*- coding: utf-8 -*-
"""构建私联线性剧情线 storyline_shiren.json。
一条线 = 6 拍（0 越线 / 1 深夜 / 2 见面 / 3 上头 / 4 裂痕 / 5 收场），
每拍 3 个剧情变体随机上 1；每局生成一个全新专属私联 OTA（非五种子）。
触发按条件不按日历（越线门槛=某 OTA 黏性≥75 且 周≥2）；无固定周间隔，由 heat(玩家投入)驱动快慢。
只有私联线有"还记不记得 TA"终局拷问。非游戏代码，内容构建脚本，保留。"""
import json, os

OUT = r"C:\Users\kk\Documents\deepseek-harness\default-workspace\聚场\data\storylines\storyline_shiren.json"
os.makedirs(os.path.dirname(OUT), exist_ok=True)

doc = {
    "_meta": {
        "kind": "storyline",
        "id": "shiren",
        "name": "私联线",
        "category": "线性剧情线",
        "design_note": (
            "私联线是唯一的『深主线』：每局生成一个全新专属 OTA（名字/性别/原型从 name_pools 与 archetypes 抽），"
            "不是五个种子、也不是随机孵化。触发按条件不按日历——越线门槛=某 OTA 黏性≥75 且 周≥2（第一周绝不私联）。"
            "此后每一拍都要 heat（玩家投入：回消息/见面/答应）达标才推进，冷淡则卡住甚至断线。"
            "每一拍有 3 个剧情变体随机上 1，复玩会遇上完全不同的 TA 与情节。"
            "唯一钉死的日历是拍5『收场』在 W6 决赛前必到；收场是面对面拷问：她当面问『我随口说过的那些小事，你还记得吗』，"
            "只从她自己说过的小事（protagonist.memory 的 choice 项）抽 3 道——她说的=拷问问的=判对的，同一个值，"
            "答对≥2=真·被看见，答错=假·工具；答对后做最后选择：就这么下去（唯一）/说清楚以后别来（失控）。"
        ),
        "resource_keys": {
            "money": "钱", "stamina": "体力", "psyche": "心理", "fame": "人气", "stage": "舞台稳定",
            "ota_all": "全体OTA黏性", "relation_A": "阿棠", "relation_B": "露露", "relation_C": "小满",
            "relation_all": "团内关系整体", "shiren": "私联人数", "enjou": "炎上", "kaibox": "开盒风险",
            "shiroi": "私生跟踪", "banzi": "板子关注度",
        },
        "protagonist_schema": (
            "进入拍0时生成：{id:'shiren_'+rand, name(从name_pools按gender抽), gender, archetype(从archetypes抽), "
            "fan_type(取archetype.fan_types之一), is_seed:false, is_storyline:true, stickiness:75(bootstrap), memory:{}}。"
            "同时为 memory_key 里 kind=choice 的项各从 pool 随机锁定一个值，写入 memory.preset（整局固定、复玩不同），"
            "剧情文案用 {{cat_name}}/{{drink}}/{{food_hate}}/{{song}}/{{hometown}}/{{flower}} 取该局锁定值填进叙事；"
            "kind=fact 项不预设，由具体剧情变体 learns 时写入 memory。"
            "剧情文案用 {{ta}} 显示名字、{{ta.ta}} 显示他/她、{{ta.arche}} 显示原型标签。"
        ),
        "schema": (
            "stages[i] = {stage:int, key, title, gate, enter_heat, variants[3]}；"
            "variant = {id, title, narrative, options[2-3]}；"
            "option = {id, label, desc, immediate:{res:delta}, advance:int(heat增量), learns:'记忆点key'|['key',...]|null, "
            "flags:[...], delayed:[{when,condition?,effect,note}], note?}；"
            "learns 的记忆点写入 protagonist.memory，供 finale 拷问抽取（一局可解锁 6~9 个记忆点，拷问从已解锁里抽）。"
            "收场出题走私联独立通道：只取 choice 类记忆点，题干用下方 ask_q、选项用 pool、真值取她这一局实际说过的值"
            "（开局预锁进 _truth，键名加 shiren_ 前缀与普通回考隔离），不再走普通 OTA 记忆卡那套 s.clues。"
        ),
    },
    # 结局判定用到的记忆点题库（key -> 问题/答案阈值无关，只用于文案）
    # 拷问题库：记忆点越多越杂，越考验玩家是否真的"看见"了这个人。
    # kind=fact 由剧情固定写入；kind=choice 每次开局从 pool 里随机取一个值（同一局内固定，复玩不同）。
    # 收场拷问只从 choice 类里出：开局预锁的值、剧情占位符填的值、判对的真值
    # 都是同一个。ask_q 是她当面问的那句，react_good/bad 是答完她那一下的反应。
    # 题干与反应里的「你」全部包在引号内（叙述正文不出现第二人称）。
    "memory_key": {
        "job_pain":  {"q": "TA 工作上最憋屈的一件事", "kind": "fact"},
        "fear":      {"q": "TA 最怕的东西", "kind": "fact"},
        "home":      {"q": "TA 住在什么样的地方", "kind": "fact"},
        "hometown":  {"q": "TA 老家是哪里的", "kind": "choice",
                      "pool": ["江西的一个小县城", "东北的矿区", "云南的山里", "福建的海边", "川南的小城"],
                      "ask_q": "『我老家在哪儿来着，你说说。』",
                      "react_good": {"gravity": "她眼睛亮了一下：『你居然记得。』"},
                      "react_bad": {"gravity": "她笑了笑，没接话：『也是，那么久以前的事。』"}},
        "cat_name":  {"q": "TA 的猫叫什么", "kind": "choice",
                      "pool": ["团子", "年糕", "布丁", "芝麻", "豆花", "橘子", "汤圆", "煤球"],
                      "ask_q": "『我家那只叫什么，你应该记得吧。』",
                      "react_good": {"gravity": "她轻声重复了一遍那个名字，像怕说大声了会碎。"},
                      "react_bad": {"gravity": "她垂下眼：『忘了啊。它倒是还记得你。』"}},
        "family":    {"q": "TA 老家还有什么人", "kind": "fact"},
        "drink":     {"q": "TA 每次点同一杯什么", "kind": "choice",
                      "pool": ["酸梅汤", "冰美式", "温豆浆", "柠檬水", "大麦茶", "无糖乌龙"],
                      "ask_q": "『我每次都点同一杯，是什么来着？』",
                      "react_good": {"gravity": "她把杯子往我这边推了推：『对，就是那杯。』"},
                      "react_bad": {"gravity": "她低头搅着杯子：『没事，下次告诉你。』"}},
        "food_hate": {"q": "TA 最讨厌吃的东西", "kind": "choice",
                      "pool": ["香菜", "肥肉", "苦瓜", "折耳根", "榴莲", "海带"],
                      "ask_q": "『我最见不得吃什么，你记得吗？』",
                      "react_good": {"gravity": "她皱着鼻子笑：『你连这个都记得，太过分了。』"},
                      "react_bad": {"gravity": "她把那样的东西夹到我碗里：『现在知道也不晚。』"}},
        "wish":      {"q": "TA 随口说过的一个愿望", "kind": "fact"},
        "song":      {"q": "TA 说最喜欢你们哪首歌", "kind": "choice",
                      "pool": ["《还没学会告别》", "《周五的雨》", "《把灯留着》", "《散场以后》"],
                      "ask_q": "『我说过最喜欢哪一首，你哼给我听。』",
                      "react_good": {"gravity": "她跟着哼了半句，声音很轻：『就是这首。』"},
                      "react_bad": {"gravity": "她按掉播放器：『算啦，不考你了。』"}},
        "promise":   {"q": "你被 TA 逼着答应过的那件事", "kind": "fact"},
        "flower":    {"q": "TA 每次送你的花是什么", "kind": "choice",
                      "pool": ["洋桔梗", "小雏菊", "向日葵", "满天星", "白玫瑰"],
                      "ask_q": "『我送你的那个花，叫什么名字来着？』",
                      "react_good": {"gravity": "她低头笑：『你连花名都记着，我是真的高兴。』"},
                      "react_bad": {"gravity": "她摸了摸空着的手心：『下次我写在卡片上。』"}},
    },
    "stages": [
        # ---------------- 拍0 越线 ----------------
        {
            "stage": 0, "key": "cross_line", "title": "越线",
            "gate": "任一 OTA 黏性 ≥ 75 且 周 ≥ 2 且 私联人数 = 0",
            "enter_heat": 0,
            "generate_protagonist": True,
            "note": "进入即生成全新专属私联 OTA。此拍没有失败，只有『要不要给这条线开门』。",
            "variants": [
                {
                    "id": "cross_wechat_red",
                    "title": "红着脸问加微信",
                    "narrative": "特典会排到最后，{{ta}}把签好的拍立得递回来，忽然没走。手指在桌沿上蹭了半天，才很小声地开口：『那个……能不能，加个微信？就、就平时也不知道去哪看你。』说完脸一下红到耳朵根，眼睛却还盯着我，一眨不眨，像在等一个判决。",
                    "options": [
                        {"id": "give_personal", "label": "把私人号给 TA", "desc": "越过那条线的第一步，我自己跨的",
                         "immediate": {"shiren": 1, "kaibox": 6, "psyche": 6}, "advance": 1,
                         "flags": ["crossed_line"], "delayed": [], "note": "你们的对话框亮了，第一句是『真的是你吗』"},
                        {"id": "give_work", "label": "给工作号，说这里都能找到我", "desc": "半开一扇门，既留了人，也没全给",
                         "immediate": {"kaibox": 2, "ota_all": 2, "psyche": 1}, "advance": 0,
                         "flags": ["work_only"], "delayed": [], "note": "TA 有点失落，但还是认真地加了"},
                        {"id": "decline", "label": "笑着说『我只有工作号，见谅』", "desc": "把线收在台面上，安全，也凉",
                         "immediate": {"psyche": -3, "ota_all": 2}, "advance": 0,
                         "flags": ["line_closed"], "delayed": [], "note": "TA 低头说了句『好』，转身进了散场的人群"},
                    ],
                },
                {
                    "id": "cross_phone_offer",
                    "title": "递过来的手机",
                    "narrative": "散场人快走空了，{{ta}}却绕到台边，把手机屏幕朝我一递——微信二维码已经调好，就那么举着，也不说话。TA 好像排练过很多遍这个动作，此刻却紧张得手有点抖。我看着那个亮着的屏幕，忽然明白过来：TA 把所有的勇气都押在这一递上了。",
                    "options": [
                        {"id": "scan", "label": "扫了，说『你赢了』", "desc": "一句话，把自己也逗笑了，却知道回不了头",
                         "immediate": {"shiren": 1, "kaibox": 6, "psyche": 5}, "advance": 1,
                         "flags": ["crossed_line"], "delayed": [], "note": "手机震了一下，好友申请上写着：『终于』"},
                        {"id": "push_back", "label": "把手机轻轻推回去", "desc": "『这个我不能给』",
                         "immediate": {"psyche": -2, "ota_all": 2}, "advance": 0,
                         "flags": ["line_closed"], "delayed": [], "note": "TA 收回手机，扯了扯嘴角：『没事，我就试试』"},
                    ],
                },
                {
                    "id": "cross_note",
                    "title": "花束里的纸条",
                    "narrative": "回到后台，我把今天收到的花一枝枝插进桶里。插到最底下那一束{{flower}}时，指尖碰到一点硬邦邦的东西——拨开花瓣，是一张对折的纸条。上面是一串微信号，字写得工工整整，末尾一句：『如果不行，就当没看到，别为难。』没有署名，可我知道是谁。我捏着那张纸站在后台，忽然想起自己刚来这座城市时，也是这样小心翼翼地把心意，藏在某个不敢被拆穿的地方。",
                    "options": [
                        {"id": "add_note", "label": "回去就加上", "desc": "那份小心翼翼，我不忍心装作没看到",
                         "immediate": {"shiren": 1, "kaibox": 5, "psyche": 6}, "advance": 1,
                         "flags": ["crossed_line"], "delayed": [], "note": "通过的一瞬间，对方打了很长一段话又删掉，只发来一个『嗨』"},
                        {"id": "burn_note", "label": "把纸条收进抽屉，不加", "desc": "心意我收下了，人不能要",
                         "immediate": {"psyche": 2}, "advance": 0,
                         "flags": ["line_closed"], "delayed": [{"when": "下周", "effect": {"ota_all": -2},
                                                                  "note": "那个总排到最后的 ID，再没出现在特典队里；你少了一个愿意为你留到最后的人"}],
                         "note": "纸条锁进抽屉。后来你路过几次特典会，那个位置一直空着"},
                    ],
                },
            ],
        },
        # ---------------- 拍1 深夜 ----------------
        {
            "stage": 1, "key": "late_night", "title": "深夜",
            "gate": "crossed_line 且 heat ≥ 1",
            "enter_heat": 1,
            "variants": [
                {
                    "id": "night_boss",
                    "title": "她说今天被领导骂了",
                    "narrative": "夜里十二点，{{ta}}发来一长串：今天被领导当众骂了，明明不是TA的错。我一条条读下去，能想象TA蜷在被子里打字的样子。TA 说：『不好意思，跟你说这些干嘛。』又补一句：『你别管我，早点睡。』可我知道，那句『别管我』，其实是『管管我』。",
                    "options": [
                        {"id": "comfort_deep", "label": "陪 TA 骂回去，聊到手机发烫", "desc": "这点暖，我舍不得断",
                         "immediate": {"psyche": 8, "kaibox": 4, "stamina": -5}, "advance": 1, "learns": ["job_pain", "fear"],
                         "flags": [], "delayed": [{"when": "条件", "condition": "开盒风险 ≥ 55", "effect": {"enjou": 8},
                                                  "note": "TA 开始习惯这个点找你，有天你没回，TA 发了条只有半句话的朋友圈"}],
                         "note": "原来 TA 在一个很压抑的地方上班，天天被当众数落；TA 说最怕的就是有天被裁掉，一个人在这座城市连房租都交不起"},
                        {"id": "sleep_early", "label": "说太晚了，先睡吧", "desc": "把线轻轻拉回来一点",
                         "immediate": {"psyche": -3, "ota_all": -2, "kaibox": -3}, "advance": 0, "learns": None,
                         "flags": [], "delayed": [], "note": "『嗯，晚安。』——那个句号，比平时冷"},
                    ],
                },
                {
                    "id": "night_empty_room",
                    "title": "空出租屋的照片",
                    "narrative": "{{ta}}发来一张照片：一间很空的出租屋，只有一张床、一个纸箱当桌子，窗帘还没装。TA 说：『搬来第三天，还是觉得像住旅馆。』我盯着那张照片，忽然有点喘不过气——那不是我的房间吗。我们都在别人的城市里，把一间屋子住成了临时的样子。",
                    "options": [
                        {"id": "my_room_too", "label": "拍一张自己的房间发给 TA", "desc": "两个临时的人，凑一起好像就没那么临时",
                         "immediate": {"psyche": 9, "kaibox": 4, "stamina": -3}, "advance": 1, "learns": ["home", "hometown"],
                         "flags": [], "delayed": [{"when": "下周", "effect": {"kaibox": 3},
                                                   "note": "那张照片她留着，说两个人住得都不像家，倒像是同一座城市里的两个临时工"}],
                         "note": "TA 住城东那片，每天通勤要一个多小时；TA 说自己是{{hometown}}人，一个人来这儿闯"},
                        {"id": "pity_distance", "label": "回一句『都会好的』，不深聊", "desc": "我怕聊深了收不住",
                         "immediate": {"psyche": -2, "kaibox": -2}, "advance": 0, "learns": None,
                         "flags": [], "delayed": [], "note": "TA 回了个笑脸，那照片 TA 再没发过第二张"},
                    ],
                },
                {
                    "id": "night_cat_sick",
                    "title": "猫病了",
                    "narrative": "凌晨一点，{{ta}}的消息带着哭腔：『我猫好像不行了，我抱着它在打车，可司机说不载宠物。』后面跟着一张模糊的照片，一只橘猫软软地瘫在TA怀里。我盯着屏幕，手心全是汗——一个在这座城市里，连只猫都留不住的人。我忽然想，今晚要是能陪TA就好了。",
                    "options": [
                        {"id": "go_help", "label": "披上外套出门，去陪 TA", "desc": "我知道这越过线了，可我做不到不管",
                         "immediate": {"psyche": 8, "kaibox": 12, "stamina": -10}, "advance": 1, "learns": "cat_name",
                         "flags": ["met_at_night"], "delayed": [{"when": "条件", "condition": "开盒风险 ≥ 50", "effect": {"shiroi": 10},
                                                                  "note": "深夜一起出现的身影，被楼下便利店的监控记住了"}],
                         "note": "猫叫『{{cat_name}}』，是TA从老家带来的唯一念想"},
                        {"id": "voice_call", "label": "打语音陪着，一起等结果", "desc": "人不到，声音到",
                         "immediate": {"psyche": 6, "kaibox": 6, "stamina": -4}, "advance": 1, "learns": "cat_name",
                         "flags": [], "delayed": [], "note": "猫叫『{{cat_name}}』，后来救回来了，TA 发消息说『谢谢你没挂』"},
                        {"id": "text_only", "label": "回句『别急，会好的』", "desc": "我不敢更深地卷进去",
                         "immediate": {"psyche": -3, "kaibox": -2}, "advance": 0, "learns": None,
                         "flags": [], "delayed": [], "note": "第二天 TA 只字未提那晚，好像从没开口求过人"},
                    ],
                },
            ],
        },
        # ---------------- 拍2 见面 ----------------
        {
            "stage": 2, "key": "meet", "title": "见面",
            "gate": "crossed_line 且 heat ≥ 2",
            "enter_heat": 2,
            "variants": [
                {
                    "id": "meet_noodle",
                    "title": "场馆外的那杯热的",
                    "narrative": "散场侧门，{{ta}}拎着两杯热的站在那儿，看见我就递过来一杯。指尖碰到我手背，她像被烫到一样缩回去，又红着脸递了一次：『这个……给你暖手。』我接过那杯的时候，心里那道线已经被我亲手踩在脚下了。",
                    "options": [
                        {"id": "go", "label": "接过来，多站一会", "desc": "『你手这么凉，喝口热的再走。』她连我每次点的{{drink}}都记得",
                         "immediate": {"psyche": 10, "kaibox": 10, "stamina": -6}, "advance": 1, "learns": ["drink", "food_hate"],
                         "flags": ["met_alone"], "delayed": [{"when": "条件", "condition": "开盒风险 ≥ 45", "effect": {"shiroi": 12},
                                                              "note": "TA 记住了你常去的方向，之后散场总能在路口『碰见』你"}],
                         "note": "她握着杯子说，我就爱喝{{drink}}，太甜的不碰；又把{{food_hate}}一样样挑到一边，说这辈子最受不了这个"},
                        {"id": "decline", "label": "说太晚了，转身进楼", "desc": "把这份暖推回去，自己走",
                         "immediate": {"psyche": -4, "kaibox": -4}, "advance": 0, "learns": None,
                         "flags": [], "delayed": [], "note": "TA 说『好』，把两杯热的一起拎着，站在原地没走"},
                    ],
                },
                {
                    "id": "meet_station",
                    "title": "顺路的那一段",
                    "narrative": "散场出来，{{ta}}说跟我家同一个方向，就这么并排走了一段。谁也没提台下的事，只有路灯把我们两个的影子拉得老大，挨在一起。走到岔路口，她停下来看我，像在等我先开口。这一段路不长，可我心里清楚，走完就再也退不回去了。",
                    "options": [
                        {"id": "wave_back", "label": "放慢脚步，陪她走完这段", "desc": "『你最大的愿望是什么，路上说给我听。』——我想多知道一点",
                         "immediate": {"psyche": 8, "kaibox": 8, "stamina": -4}, "advance": 1, "learns": ["wish", "family"],
                         "flags": ["met_alone"], "delayed": [{"when": "条件", "condition": "开盒风险 ≥ 50", "effect": {"kaibox": 6},
                                                              "note": "这段路她后来反复提起，说那天的路灯把两个人的影子挨在了一起"}],
                         "note": "她说，最大的愿望是有一天能坐在台下正中间听我唱一次；又提起老家有个常年吃药的妈妈，每个月工资一大半寄回去"},
                        {"id": "just_wave", "label": "在岔路口停住，摆摆手走开", "desc": "留一点余地",
                         "immediate": {"psyche": 4, "kaibox": 3}, "advance": 1, "learns": "wish",
                         "flags": [], "delayed": [], "note": "TA 在微信里说，那天在岔路口站了好久，看我走远"},
                    ],
                },
                {
                    "id": "meet_walk_home",
                    "title": "就剩她一个人",
                    "narrative": "我从后台出来，队友早被接走了。喊我同走，我说『你们先走，我落了东西』——其实什么都没落。台阶上就剩我和{{ta}}。她先回头看那群人拐过街角、确认走远了，才转回来靠近我，声音轻得像怕被第三个人听见：『就你了。就现在。』",
                    "options": [
                        {"id": "walk_all_way", "label": "走近一步，多待一会", "desc": "『就你了。就现在。』——我点头，往她那边走了一步",
                         "immediate": {"psyche": 8, "kaibox": 14, "stamina": -8}, "advance": 1, "learns": ["home", "song"],
                         "flags": ["met_alone"], "delayed": [{"when": "条件", "condition": "开盒风险 ≥ 60", "effect": {"shiroi": 14},
                                                                             "note": "那天之后，她总在散场时往后台这边多望两眼"}],
                         "note": "她把手机里录的最后那首歌递给我听，我跟着清唱了一遍；她说『这个是我的了』，然后一路哼着{{song}}走远"},
                        {"id": "call_cab", "label": "说谢谢，快步走开", "desc": "趁还能回头，先走",
                         "immediate": {"psyche": 3, "kaibox": 4, "stamina": -3}, "advance": 0, "learns": None,
                         "flags": [], "delayed": [], "note": "走出几步我才敢回头，她还站在那道台阶上，看着我"},
                    ],
                },
            ],
        },
        # ---------------- 拍3 上头 ----------------
        {
            "stage": 3, "key": "obsession", "title": "上头",
            "gate": "crossed_line 且 heat ≥ 3",
            "enter_heat": 3,
            "note": "这一拍删掉了『借钱』——私联的人不会张口借钱，TA 要的是比钱更贵的东西：一个承诺、一个身份。",
            "variants": [
                {
                    "id": "obs_only_one",
                    "title": "『我是不是你唯一』",
                    "narrative": "{{ta}}忽然问我：『你私下里，是不是也这样对别人？』我愣了一下。TA 接着说，语气很轻，却一个字一个字往我心里钉：『你答应我，我是唯一那个，好不好？』屏幕的光照在脸上，我打的字删了又打——这个问题，一旦答错，前面那些暖就全变成债了。",
                    "options": [
                        {"id": "promise_yes", "label": "答应 TA：『你是唯一』", "desc": "一句谎话，换来今晚的安稳",
                         "immediate": {"psyche": 6, "kaibox": 8}, "advance": 1, "learns": "promise",
                         "flags": ["promised_exclusive"], "delayed": [{"when": "条件", "condition": "私联人数 ≥ 2", "effect": {"enjou": 12, "psyche": -8},
                                                                       "note": "『唯一』这两个字，被TA截图存了下来"}],
                         "note": "你答应过 TA：私下里只有TA一个人"},
                        {"id": "honest_no", "label": "老实说：我给不了这个承诺", "desc": "诚实，可能会失去 TA",
                         "immediate": {"psyche": -6, "kaibox": -4}, "advance": 0, "learns": None,
                         "flags": ["refused_promise"], "delayed": [], "note": "TA 沉默了很久，回了一句：『我知道了』——那晚你们谁也没再说话"},
                        {"id": "dodge", "label": "打个哈哈：『你怎么这么可爱』", "desc": "绕过去，装作没听懂",
                         "immediate": {"psyche": 2, "kaibox": 4}, "advance": 1, "learns": "promise",
                         "flags": ["dodged"], "delayed": [{"when": "条件", "condition": "心理 < 30", "effect": {"psyche": -6},
                                                          "note": "TA 后来又问了一次，这次你没躲开，也只能含糊地应下"}],
                         "note": "你没有正面答应，但 TA 自己默认了一个『是』"},
                    ],
                },
                {
                    "id": "obs_off_duty",
                    "title": "什么时候能不当偶像见我",
                    "narrative": "{{ta}}说：『我想见见不当偶像的你。不是台上那个，是下楼买菜、会穿拖鞋那个。』我盯着这句话，心里又软又慌。TA 要的不是签名、不是合照，是那个连我自己都快忘了的、普通的人。可我知道，一旦把那个人交出去，我们就再也回不到『偶像和粉丝』了。",
                    "options": [
                        {"id": "meet_as_self", "label": "答应 TA，下次素颜见", "desc": "我也想当一次普通人",
                         "immediate": {"psyche": 8, "kaibox": 10, "stamina": -3}, "advance": 1, "learns": "wish",
                         "flags": ["promised_offduty"], "delayed": [{"when": "条件", "condition": "开盒风险 ≥ 55", "effect": {"enjou": 8},
                                                                      "note": "素颜的样子，后来出现在了一个你意想不到的地方"}],
                         "note": "TA 说，最想看你穿拖鞋在菜市场挑菜的样子"},
                        {"id": "keep_idol", "label": "说『台上那个也是真的我』", "desc": "守住那条线，也守住自己",
                         "immediate": {"psyche": -3, "kaibox": -3}, "advance": 0, "learns": None,
                         "flags": [], "delayed": [], "note": "TA 有点失望：『可我想看的是台下那个』"},
                    ],
                },
                {
                    "id": "obs_remember",
                    "title": "『你答应过会记得我』",
                    "narrative": "{{ta}}翻出很早以前的聊天记录，是我随口回的一句『不会忘了你的』。TA 说：『你看，你自己说的。那我以后要是一直在，你是不是就永远不会忘了我？』这话听着像撒娇，落在我心里却沉甸甸的——TA 在拿一句我早忘了的话，往我身上系一根绳子。",
                    "options": [
                        {"id": "reaffirm", "label": "认真应下：我记着", "desc": "一句话而已，说了就说了",
                         "immediate": {"psyche": 5, "kaibox": 6}, "advance": 1, "learns": "promise",
                         "flags": ["promised_remember"], "delayed": [], "note": "你确认了那个承诺：你会一直记得TA"},
                        {"id": "deflect", "label": "笑笑说『那时候的话你还当真』", "desc": "轻描淡写地卸下来",
                         "immediate": {"psyche": -4, "kaibox": -2}, "advance": 0, "learns": None,
                         "flags": [], "delayed": [], "note": "TA 没再说什么，可那晚的『晚安』隔了很久才来"},
                    ],
                },
            ],
        },
        # ---------------- 拍4 裂痕 ----------------
        {
            "stage": 4, "key": "crack", "title": "裂痕",
            "gate": "crossed_line 且 heat ≥ 4",
            "enter_heat": 4,
            "variants": [
                {
                    "id": "crack_teammate",
                    "title": "只跟我说这一句",
                    "narrative": "她把我约到一家很偏的店，这个点只剩我们一桌。进门我就紧张起来，帽檐压得低低的——这家店太偏，万一被人认出来，我连句像样的解释都编不及。她刚坐下就把手伸过桌面，掌心朝上，放在那儿等我。我手心全是汗，心跳快得怕她听见，又不敢往回缩。脑子里有个声音一直在喊『到此为止』，可我的手完全不听话，一根一根扣进了她的指缝，攥得死紧。她绕过桌子坐到我身边，肩膀贴过来，凑近看我，呼吸落在嘴唇边，抬着眼不说话。我不敢往门口再看第二眼——剩下那一步，她留给我。",
                    "options": [
                        {"id": "confide_C", "label": "低头吻住她", "desc": "『那我整个人都是你的』——紧张到脑子空白，可我就是想吻她。",
                         "immediate": {"relation_C": 4, "psyche": 4, "kaibox": 3}, "advance": 1, "learns": None,
                         "flags": ["team_knows"], "delayed": [{"when": "条件", "condition": "心理 < 30", "effect": {"relation_all": -5},
                                                               "note": "我谁也没告诉，可藏不住了——看她的时候，眼睛和看别人不一样"}],
                         "note": "她愣了一下，随即靠进我怀里，回吻得很用力，那一晚我们谁都没提『回去』两个字"},
                        {"id": "deny_C", "label": "吻在她额头上，把她往怀里带", "desc": "『这是我们两个的事』——手在抖，我把它藏进她头发里。",
                         "immediate": {"relation_C": -5, "psyche": -4, "kaibox": 2}, "advance": 1, "learns": None,
                         "flags": ["denied"], "delayed": [], "note": "她没挣，脸埋进我颈窝，耳朵红透了"},
                        {"id": "stop_here", "label": "松开手，推开她坐好", "desc": "『我们再也不能这样了，以后都不要』——我怕了，真的怕了。",
                         "immediate": {"psyche": -8, "kaibox": -6, "shiren": 0}, "advance": 0, "learns": None,
                         "flags": ["cut_early"], "delayed": [], "note": "她盯着我很久，才说『好』"},
                    ],
                },
                {
                    "id": "crack_fans",
                    "title": "共听一副耳机",
                    "narrative": "她把我约到河堤边，这个点没人，只有路灯和很远的车声。我挨着她坐下，整个人绷得很紧——这条路偶尔有夜跑的经过，我每听见一点动静就往灯暗处缩一下，生怕被谁认出来。她摸出一副耳机分我一只，点开那首{{song}}：『这首，我想跟你一起听。』她一点一点把头靠过来，轻轻搁在我肩上。我当场僵住，手抬到半空又停住，连呼吸都不敢放重，怕她听出我有多紧张。过了很久她抬起脸看我，嘴唇离得很近，眼睛里映着路灯，什么都没说。",
                    "options": [
                        {"id": "public_deny", "label": "低头吻上去，一只手揽住她的腰", "desc": "『这个位置，只给你』——我豁出去了，手抖得厉害。",
                         "immediate": {"enjou": -6, "fame": -3, "psyche": -4}, "advance": 1, "learns": None,
                         "flags": ["official_denial"], "delayed": [{"when": "条件", "condition": "板子关注度 ≥ 40", "effect": {"banzi": 10},
                                                                      "note": "后来她把那只耳机留着，谁都不让碰"}],
                         "note": "她闭上眼，回吻得比我还认真"},
                        {"id": "stay_silent", "label": "吻在她头顶，把她搂得更紧", "desc": "紧张得说不出话，只能抱紧一点再抱紧一点。",
                         "immediate": {"enjou": 4, "psyche": -6, "banzi": 6}, "advance": 1, "learns": None,
                         "flags": [], "delayed": [], "note": "那首歌循环了很久，久到我们一句话都没说"},
                        {"id": "step_back", "label": "站起来，往后退开半步", "desc": "『我们再也不能这样了，别再找我』——我再待一秒就要失控了。",
                         "immediate": {"psyche": -8, "kaibox": -6, "shiren": 0}, "advance": 0, "learns": None,
                         "flags": ["cut_early"], "delayed": [], "note": "她愣在原地，喊了我一声，我没回头"},
                    ],
                },
                {
                    "id": "crack_manager",
                    "title": "指尖停在脸侧",
                    "narrative": "她把我约到她那片没人的旧街区。见了面，她不说要给我看什么，只是一直凑近了看我。这条街太静，我紧张得能听见自己砰砰的心跳，手心全是冷汗——我明明该后退一步的，可脚像钉在地上，喉咙发紧，一个字都挤不出来。风把我额前的头发吹乱，她抬手替我拢开，指尖顺着我的眉骨、眼角滑下来，最后停在我嘴角旁边，没再往下。她自己凑到跟前，鼻尖几乎碰着我的，睫毛近得看得清，唇微微张着：『我想看看，不上台的时候，你是什么样子。』我几乎喘不上气，怕先失守的那个人是我。",
                    "options": [
                        {"id": "beg_once", "label": "捧住她的脸吻上去", "desc": "『那你看吧，只看我』——管不了那么多了。",
                         "immediate": {"psyche": -4, "fame": -2, "enjou": 3}, "advance": 1, "learns": None,
                         "flags": ["manager_leverage"], "delayed": [{"when": "条件", "condition": "炎上 ≥ 40", "effect": {"fame": -5},
                                                                      "note": "后来她总提起那天：『你说过只让我看。』我无从反驳"}],
                         "note": "她愣了一下，然后笑了，回吻很轻，指尖却攥紧了我背后的衣料"},
                        {"id": "keep_it", "label": "吻在她眼角，把她拉近到额头相抵", "desc": "紧张得眼眶发热，我闭着眼凑过去。",
                         "immediate": {"psyche": 2, "kaibox": 8}, "advance": 1, "learns": None,
                         "flags": ["double_life"], "delayed": [{"when": "下周", "effect": {"enjou": 6},
                                                                  "note": "我开始学着撒谎，对一个真心待我的人撒谎，越来越熟练"}],
                         "note": "我开始明白，有些谎是从这一刻开始的——对自己说的『就这一次』"},
                        {"id": "promise_stop", "label": "把她的手从脸上拿开，转身走出那条街", "desc": "『我们再也不能这样了，以后别再见了』——我怕自己再不走就真的走不了了。",
                         "immediate": {"psyche": -10, "kaibox": -8, "shiren": 0, "fame": 3}, "advance": 0, "learns": None,
                         "flags": ["deleted_ta", "cut_early"], "delayed": [], "note": "身后很安静，她没有追上来"},
                    ],
                },
            ],
        },
    ],
    # ---------------- 拍5 收场（W6 决赛前必到） ----------------
    "finale": {
        "stage": 5, "key": "finale", "title": "收场",
        "gate": "crossed_line 且 周 = 6（决赛前必触发，唯一钉死的日历）",
        "enter_heat": 0,
        "intro": "从那晚加上微信算起，我们这样已经走了很久。散场后的侧门、河堤的夜路、没人的旧街区——只剩我们两个的时刻一次接一次，多到我自己都数不清。到后来，在一起几乎不用说话，一个眼神就知道对方在想什么。我一直以为，我们之间已经深到不必再确认什么。决赛前一晚，灯只开了一半。{{ta}}没有像往常那样先发消息，等我到了，才从半明半暗的灯里走过来——空场馆里只剩我们两个，近得能听见彼此的呼吸。{{ta}}抬手替我理了理被风吹乱的头发，指尖顺着我的脸颊滑下来，停在耳边，才慢慢收回去。然后{{ta}}看着我，眼神比哪一次都认真：『我问你几件事，都是我说过的、很小很小的事。你要是都记得，我就信——你记住的是我这个人。』",
        "quiz": {
            "note": "当面拷问 3 道：只从她自己随口说过的小事里抽（猫的名字/家乡/讨厌的食物/喜欢的歌等，同一局锁定、复玩不同）。她说的=拷问问的=判对的，同一个值。答对≥2 → 真·被看见；答对≤1 → 假·工具。",
            "draw": 3, "pass_threshold": 2,
        },
        "outcomes": [
            {"id": "real_seen", "label": "真·被看见", "condition": "答对 ≥ 2",
             "effect": {"psyche": 10}, "flag": "truly_seen",
             "note": "我一件件答上来，{{ta}}听着，眼神一点点软下来，最后轻轻靠过来，额头抵在我肩上。那些随口的琐碎，我居然真的都记着。我低头问{{ta}}：『这么多个晚上过去，我会真的是你的唯一，对吧？』问出口才明白，我要的从来不只是被记住——是只想被{{ta}}一个人记住。"},
            {"id": "fake_tool", "label": "假·工具", "condition": "答对 ≤ 1",
             "effect": {"psyche": -8}, "flag": "used_as_tool",
             "note": "{{ta}}问得很轻，一句一句，像在给我机会。可我脑子里翻来覆去只剩『有人陪我』这四个字——{{ta}}养了什么、怕什么、想要什么，我一件也说不出。{{ta}}听完没说话，只是把距离慢慢拉开。那句『我会不会是你的唯一』，我到最后也没敢问出口。"},
        ],
        "final_choices": [
            {"id": "sink", "label": "就这么下去", "desc": "不公开，也不断。当它没有尽头",
             "immediate": {"psyche": 4, "kaibox": 10, "enjou": 6}, "flags": [],
             "note": "我没有回那条消息，也没有不回。第二天她照常坐在列里等我。"},
            {"id": "cut_clean", "label": "跟她说清楚，以后别来了", "desc": "把线剪干净",
             "immediate": {"psyche": -8, "kaibox": -14, "shiroi": -10}, "flags": [],
             "note": "我打了一大段，删了，又打了一段。最后发出去的是最短的那句。"},
        ],
    },
}

with open(OUT, "w", encoding="utf-8") as f:
    json.dump(doc, f, ensure_ascii=False, indent=2)
    f.write("\n")

# quick summary
n_variants = sum(len(s.get("variants", [])) for s in doc["stages"])
print("WROTE", OUT)
print("stages", len(doc["stages"]), "variants", n_variants, "final_choices", len(doc["finale"]["final_choices"]))
