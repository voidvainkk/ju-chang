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
            "唯一钉死的日历是拍5『收场』在 W6 决赛前必到；收场先做『你还记得 TA 吗』拷问（从已解锁的记忆点抽 3 道），"
            "答对多=真·被看见，答不出=假·工具；随后做最后选择：公开/断联/沉沦/划边界，交结局判定。"
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
        ),
    },
    # 结局判定用到的记忆点题库（key -> 问题/答案阈值无关，只用于文案）
    # 拷问题库：记忆点越多越杂，越考验玩家是否真的"看见"了这个人。
    # kind=fact 由剧情固定写入；kind=choice 每次开局从 pool 里随机取一个值（同一局内固定，复玩不同）。
    "memory_key": {
        "job_pain":  {"q": "TA 工作上最憋屈的一件事", "kind": "fact"},
        "fear":      {"q": "TA 最怕的东西", "kind": "fact"},
        "home":      {"q": "TA 住在什么样的地方", "kind": "fact"},
        "hometown":  {"q": "TA 老家是哪里的", "kind": "choice", "pool": ["江西的一个小县城", "东北的矿区", "云南的山里", "福建的海边", "川南的小城"]},
        "cat_name":  {"q": "TA 的猫叫什么", "kind": "choice", "pool": ["团子", "年糕", "布丁", "芝麻", "豆花", "橘子", "汤圆", "煤球"]},
        "family":    {"q": "TA 老家还有什么人", "kind": "fact"},
        "drink":     {"q": "TA 每次点同一杯什么", "kind": "choice", "pool": ["酸梅汤", "冰美式", "温豆浆", "柠檬水", "大麦茶", "无糖乌龙"]},
        "food_hate": {"q": "TA 最讨厌吃的东西", "kind": "choice", "pool": ["香菜", "肥肉", "苦瓜", "折耳根", "榴莲", "海带"]},
        "wish":      {"q": "TA 随口说过的一个愿望", "kind": "fact"},
        "song":      {"q": "TA 说最喜欢你们哪首歌", "kind": "choice", "pool": ["《还没学会告别》", "《周五的雨》", "《把灯留着》", "《散场以后》"]},
        "promise":   {"q": "你被 TA 逼着答应过的那件事", "kind": "fact"},
        "flower":    {"q": "TA 每次送你的花是什么", "kind": "choice", "pool": ["洋桔梗", "小雏菊", "向日葵", "满天星", "白玫瑰"]},
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
                                                   "note": "照片的窗外景色，让 TA 认出了你住的大概方向"}],
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
                    "title": "散场后的一碗面",
                    "narrative": "散场已经十一点，{{ta}}说『附近有家面馆，要不…吃一口再走？』语气很自然，像早想好了。我明天一早还要排练，可今天实在太累了，累到不想一个人回那个空房子。夜风吹在脸上，我犹豫了两秒——这两秒里，我其实已经答应了一半。",
                    "options": [
                        {"id": "go", "label": "去吧，就当吃碗面", "desc": "反正只是吃面，我在心里给自己找台阶",
                         "immediate": {"psyche": 10, "kaibox": 10, "stamina": -6}, "advance": 1, "learns": ["drink", "food_hate"],
                         "flags": ["met_alone"], "delayed": [{"when": "条件", "condition": "开盒风险 ≥ 45", "effect": {"shiroi": 12},
                                                              "note": "TA 记住了你常去的方向，之后散场总能在路口『碰见』你"}],
                         "note": "TA 每次都点同一杯{{drink}}，说怕太甜；面端上来，TA 又一个劲儿把{{food_hate}}往外挑，说这辈子最受不了这个"},
                        {"id": "decline", "label": "改天吧，太晚了我得回去", "desc": "把这份暖推回去，自己走",
                         "immediate": {"psyche": -4, "kaibox": -4}, "advance": 0, "learns": None,
                         "flags": [], "delayed": [], "note": "TA 说『好』，一个人在面馆坐到打烊"},
                    ],
                },
                {
                    "id": "meet_station",
                    "title": "送我到车站",
                    "narrative": "{{ta}}坚持要送我。一路上我们隔着半臂的距离，谁也不提刚才在台下那些话。到车站，TA 忽然说：『就到这儿吧，你进去，我看着你走。』我说不用麻烦，TA 却站着不动。末班车的灯很亮，我走进站台回头，TA 还站在原地，举了下手。",
                    "options": [
                        {"id": "wave_back", "label": "折回来，多说两句", "desc": "那一下，我没忍住",
                         "immediate": {"psyche": 8, "kaibox": 8, "stamina": -4}, "advance": 1, "learns": ["wish", "family"],
                         "flags": ["met_alone"], "delayed": [{"when": "条件", "condition": "开盒风险 ≥ 50", "effect": {"kaibox": 6},
                                                              "note": "围观的路人里有认出你们的，照片开始在某些群里流转"}],
                         "note": "TA 说，最大的愿望是有一天能不用买票，坐在台下正中间听你唱一次；TA 还提起老家有个常年吃药的妈妈，每个月工资一大半寄回去"},
                        {"id": "just_wave", "label": "隔着玻璃摆摆手，上车", "desc": "留一点余地",
                         "immediate": {"psyche": 4, "kaibox": 3}, "advance": 1, "learns": "wish",
                         "flags": [], "delayed": [], "note": "TA 在微信里说，看着车开走，站了好久"},
                    ],
                },
                {
                    "id": "meet_walk_home",
                    "title": "送 TA 回家",
                    "narrative": "这次是{{ta}}喝多了，在群里发消息说一个人回不去。我鬼使神差地赶到，扶着 TA 往TA住的方向走。路灯下 TA 靠得很近，半醉半醒地念叨：『你知道吗，我从来没想过，会有个偶像陪我走这段路。』我心口一紧，说不出话。这一段路，走完就再也退不回去了。",
                    "options": [
                        {"id": "walk_all_way", "label": "一直送到楼下", "desc": "都走到这儿了，不差这一截",
                         "immediate": {"psyche": 8, "kaibox": 14, "stamina": -8}, "advance": 1, "learns": ["home", "song"],
                         "flags": ["met_alone", "knows_home"], "delayed": [{"when": "条件", "condition": "开盒风险 ≥ 60", "effect": {"shiroi": 14},
                                                                             "note": "TA 记住了你送TA回来的路，也把这条路的另一头，记成了你家"}],
                         "note": "TA 租在老城区边上那种带电梯的公寓，一个人住，说图个安静；路上 TA 哼起{{song}}，说每次撑不下去就循环这首"},
                        {"id": "call_cab", "label": "帮 TA 叫辆车，看着上车", "desc": "把人安顿好，我抽身",
                         "immediate": {"psyche": 3, "kaibox": 4, "stamina": -3}, "advance": 0, "learns": None,
                         "flags": [], "delayed": [], "note": "第二天 TA 发消息：『谢谢你没上来』——我不知道这是庆幸还是遗憾"},
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
                    "title": "被队友撞见",
                    "narrative": "排练完，我送{{ta}}到后门，一转身撞上小满。她手里还拎着没吃完的饭团，看看我，又看看那个陌生背影，脸上的表情慢慢变了：『姐，那个人……是不是上次那个？』我张了张嘴，那句『不是』卡在喉咙里，怎么都吐不出来。",
                    "options": [
                        {"id": "confide_C", "label": "拉住小满，把小半真相告诉她", "desc": "一个人扛不动了",
                         "immediate": {"relation_C": 4, "psyche": 4, "kaibox": 3}, "advance": 1, "learns": None,
                         "flags": ["team_knows"], "delayed": [{"when": "条件", "condition": "心理 < 30", "effect": {"relation_all": -5},
                                                              "note": "小满答应替你瞒着，可她看你的眼神，再也回不到从前"}],
                         "note": "小满说：『我不管你对不对，你别把自己搭进去』"},
                        {"id": "deny_C", "label": "说『只是粉丝，送到门口而已』", "desc": "把裂痕暂时捂住",
                         "immediate": {"relation_C": -5, "psyche": -4, "kaibox": 2}, "advance": 1, "learns": None,
                         "flags": ["denied"], "delayed": [], "note": "小满『哦』了一声，转身走了，饭团一直没吃"},
                        {"id": "stop_here", "label": "当晚就跟 TA 说，以后别来了", "desc": "趁还没闹大，自己斩断",
                         "immediate": {"psyche": -8, "kaibox": -6, "shiren": 0}, "advance": 0, "learns": None,
                         "flags": ["cut_early"], "delayed": [], "note": "TA 在电话那头很久没说话，最后只说『好，你别有负担』"},
                    ],
                },
                {
                    "id": "crack_fans",
                    "title": "别的粉丝看到了",
                    "narrative": "板子上出现一个帖子，配图是我和{{ta}}在街角的背影，很糊，但熟悉的人一眼认得出来。标题就一行：『某某私下跟常连单独见面？』底下已经吵翻了。我盯着那张照片，手脚冰凉——我以为做得很小心，可这世上根本没有不透风的喜欢。",
                    "options": [
                        {"id": "public_deny", "label": "让运营发个声明，说是粉丝见面会", "desc": "把火先压下去，用一点谎",
                         "immediate": {"enjou": -6, "fame": -3, "psyche": -4}, "advance": 1, "learns": None,
                         "flags": ["official_denial"], "delayed": [{"when": "条件", "condition": "板子关注度 ≥ 40", "effect": {"banzi": 10},
                                                                     "note": "那张糊图被人拿去做了对比图，『辟谣』反而坐实了另一半"}],
                         "note": "运营皱着眉替你发了声明，可她自己也不信"},
                        {"id": "stay_silent", "label": "什么都不说，等热度过去", "desc": "清者自清，可我并不清",
                         "immediate": {"enjou": 4, "psyche": -6, "banzi": 6}, "advance": 1, "learns": None,
                         "flags": [], "delayed": [], "note": "帖子挂了两天，越扒越细，你的名字开始和『塌房』绑在一起"},
                    ],
                },
                {
                    "id": "crack_manager",
                    "title": "运营的警告",
                    "narrative": "运营把我叫进办公室，把手机推过来，就是那张照片。她没发火，只是很平静地说：『我不问真的假的。你就告诉我一句，你想不想干下去了。』桌上摊着下个季度的资源表，我的名字被红笔圈着。我看着那个圈，忽然分不清这是警告，还是最后一次机会。",
                    "options": [
                        {"id": "promise_stop", "label": "当着运营的面，把 TA 删了", "desc": "保住饭碗，代价是我自己",
                         "immediate": {"psyche": -10, "kaibox": -8, "shiren": 0, "fame": 3}, "advance": 0, "learns": None,
                         "flags": ["deleted_ta", "cut_early"], "delayed": [], "note": "删掉的那一刻，TA 正好发来一句『今天排练累吗』"},
                        {"id": "beg_once", "label": "求运营，再给我一次机会", "desc": "把柄交到别人手里",
                         "immediate": {"psyche": -4, "fame": -2, "enjou": 3}, "advance": 1, "learns": None,
                         "flags": ["manager_leverage"], "delayed": [{"when": "条件", "condition": "炎上 ≥ 40", "effect": {"fame": -5},
                                                                     "note": "后来运营一句话，就能让你不敢再提任何条件"}],
                         "note": "运营叹了口气：『我是为你好』——从此你欠了她一次"},
                        {"id": "keep_it", "label": "嘴上应着，私下不断", "desc": "两头都想要，两头都危险",
                         "immediate": {"psyche": 2, "kaibox": 8}, "advance": 1, "learns": None,
                         "flags": ["double_life"], "delayed": [{"when": "下周", "effect": {"enjou": 6},
                                                                 "note": "你开始学着撒谎，对一个想捧你的人撒谎，越来越熟练"}],
                         "note": "你走出办公室，第一件事是给 TA 发消息：『没事，继续』"},
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
        "intro": "决赛前一晚，场馆空着，灯只开了一半。我坐在台边，手机里是{{ta}}的消息。这一季走到这里，我忽然很想问问自己——那个陪我走过这些深夜的人，我到底看清楚过没有？还是我从来只看见了『被喜欢』这件事本身。",
        "quiz": {
            "note": "从 protagonist.memory 已解锁的记忆点里随机抽 3 道（记忆点种类多、含随机变体，如猫的名字/家乡/讨厌的食物/喜欢的歌，同一局锁定、复玩不同）。答对≥2 → 真·被看见（认得 TA 这个人）；答对≤1 → 假·工具（你其实没看见 TA，只看见了被需要）。",
            "draw": 3, "pass_threshold": 2,
        },
        "outcomes": [
            {"id": "real_seen", "label": "真·被看见", "condition": "答对 ≥ 2",
             "effect": {"psyche": 10}, "flag": "truly_seen",
             "note": "你知道 TA 的猫叫什么、在哪上班、最怕什么、想要什么。那一刻你承认：你看见的是一个人。"},
            {"id": "fake_tool", "label": "假·工具", "condition": "答对 ≤ 1",
             "effect": {"psyche": -8}, "flag": "used_as_tool",
             "note": "你答不上来。你忽然发现，这些深夜你记得的是『有人陪我』，不是『TA 是谁』。"},
        ],
        "final_choices": [
            {"id": "go_public", "label": "公开：承认这段关系，哪怕塌房", "desc": "把真相摆上台面",
             "immediate": {"enjou": 20, "fame": -8, "psyche": 6, "shiren": 0}, "flags": ["final_public"],
             "delayed": [{"when": "条件", "condition": "炎上 ≥ 60", "effect": {"fame": -10, "psyche": -6},
                          "note": "团被拖下水，有人在评论区问『为了一个人值得吗』"}]},
            {"id": "cut_clean", "label": "断联：决赛后彻底断掉，各自回到岸上", "desc": "把线剪干净",
             "immediate": {"psyche": -8, "kaibox": -14, "shiroi": -10, "shiren": 0}, "flags": ["final_cut"],
             "delayed": []},
            {"id": "sink", "label": "沉沦：不公开也不断，就这么一直下去", "desc": "假装看不见尽头",
             "immediate": {"psyche": 4, "kaibox": 10, "enjou": 6}, "flags": ["final_sink"],
             "delayed": [{"when": "条件", "condition": "开盒风险 ≥ 70", "effect": {"enjou": 15, "psyche": -12},
                          "note": "纸终究包不住火，等它烧起来的时候，你已经退无可退"}]},
            {"id": "draw_line", "label": "划边界：说清楚『我只能是偶像』", "desc": "把暖留在台面上",
             "immediate": {"psyche": -4, "kaibox": -8, "ota_all": 3}, "flags": ["final_boundary"],
             "delayed": []},
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
