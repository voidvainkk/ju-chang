# -*- coding: utf-8 -*-
"""构建私生线（stalking / 被重力粉缠上）剧情线 storyline_shiroi.json。
一条线 = 5 拍（0 察觉 / 1 试探 / 2 逼近 / 3 越界 / 4 摊牌），每拍 3 个剧情变体随机上 1。
这是『后果线』：不是玩家主动开的，是玩家把某个粉养成重力粉（黏性≥80 且 risk≥0.3，如盐渍水母）
或私生跟踪值累积到阈值才触发；对象用玩家自己养出来的那个重力粉（不是生成新人）。
没有终局拷问——只写 flag、推进数值，把结论交给结局系统判定（与私联线的关键区别）。
推进由『dread 恐惧值』驱动（她的越界程度），不是玩家的投入热度。
非游戏代码，内容构建脚本，保留。"""
import json, os

OUT = r"C:\Users\kk\Documents\deepseek-harness\default-workspace\聚场\data\storylines\storyline_shiroi.json"
os.makedirs(os.path.dirname(OUT), exist_ok=True)


def opt(oid, label, desc, immediate, advance, flags=None, delayed=None, note=None):
    o = {"id": oid, "label": label, "desc": desc, "immediate": immediate,
         "advance": advance, "flags": flags or [], "delayed": delayed or []}
    if note:
        o["note"] = note
    return o


def dl(when, effect, note, condition=None):
    d = {"when": when, "effect": effect, "note": note}
    if condition:
        d["condition"] = condition
    return d


doc = {
    "_meta": {
        "kind": "storyline",
        "id": "shiroi",
        "name": "私生线",
        "category": "线性剧情线",
        "design_note": (
            "私生线是一条『后果线』：玩家不会主动开启它，是因为把某个粉丝养成了重力粉"
            "（该 OTA 黏性≥80 且 risk≥0.3，如盐渍水母），或私生跟踪值累积到阈值，才会被缠上。"
            "对象就是玩家自己养出来的那个重力粉，不另外生成、也不抓种子以外的新人。"
            "五拍=察觉→试探→逼近→越界→摊牌，每拍 3 个剧情变体随机上 1。"
            "推进由 dread（她的越界程度）驱动，不是玩家的投入——所以玩家越回避、越心软，往往越快、越深。"
            "整条线没有终局拷问：每个选择只写 flag、推进数值，把结论交给结局系统判定。"
            "摊牌拍最终四分歧：报警反杀 / 搬家逃离 / 心软接纳(最危险) / 当面对峙断联——分别写 final_report/final_escape/final_soft/final_confront。"
        ),
        "resource_keys": {
            "money": "钱", "stamina": "体力", "psyche": "心理", "fame": "人气", "stage": "舞台稳定",
            "ota_all": "全体OTA黏性", "relation_A": "阿棠", "relation_B": "露露", "relation_C": "小满",
            "relation_all": "团内关系整体", "shiren": "私联人数", "enjou": "炎上", "kaibox": "开盒风险",
            "shiroi": "私生跟踪", "banzi": "板子关注度",
        },
        "chaser_schema": (
            "进入拍0时选定 chaser（缠上来的私生）：从当前 OTA 中选『黏性最高且 risk≥0.3』的重力粉（如盐渍水母 ota_jelly）；"
            "若没有但 私生跟踪≥25，则按 archetype=重力系 孵化一个。沿用其既有 name/gender，不新建。"
            "文案用 {{ta}} 显示名字、{{ta.ta}} 显示 他/她。"
        ),
        "schema": (
            "stages[i] = {stage:int, key, title, gate, enter_dread, variants[3]}；"
            "variant = {id, title, narrative, options[2-4]}；"
            "option = {id, label, desc, immediate:{res:delta}, advance:int(dread增量), "
            "flags:[...], delayed:[{when,condition?,effect,note}], note?}。"
            "无 learns 字段（私生线不交记忆点、无拷问）。"
        ),
    },
    "stages": [
        # ================= 拍0 察觉 =================
        {
            "stage": 0, "key": "notice", "title": "察觉",
            "gate": "某 OTA 黏性 ≥ 80 且 risk ≥ 0.3，或 私生跟踪 ≥ 25（被缠上的第一周）",
            "enter_dread": 0,
            "select_chaser": True,
            "note": "这一拍玩家只是'感觉到不对劲'，还什么都没发生。所有选项都不会让线结束，只决定它长得多快、藏得多深。",
            "variants": [
                {
                    "id": "notice_follow",
                    "title": "散场后还站在原地",
                    "narrative": "散场熄了大半灯，staff 蹲在地上收线。那个总坐第一排的人还没走，抱着帆布包杵在出口边。我先去后台换了衣服，再出来时她还站在那儿。我从侧门绕出去，走了半条街回头看——隔着一整条马路，有个身影跟着我，见我回头就停下，低下头假装看手机。",
                    "options": [
                        opt("na_ignore", "可能只是顺路，别自己吓自己", "把这点不安咽回去，照常回家",
                            {"shiroi": 4, "psyche": -3}, 1, ["ignored_warning"],
                            note="我加快了脚步，一直到楼下才敢回头，街上已经空了"),
                        opt("na_staff", "回头跟 staff 提一句", "让懂规矩的人先盯一下",
                            {"shiroi": -2, "relation_all": -1}, 0, ["warned_staff"],
                            [dl("下周", {"shiroi": 6}, "staff 说了她两句，她换了个更靠后的位置，反而看得更清楚")]),
                        opt("na_smile", "转身笑着挥挥手，把她当熟客", "也许一个笑就能让她安心",
                            {"ota_all": 3, "shiroi": 3, "stamina": -3}, 1, ["was_friendly"],
                            note="她愣了一下，然后笑得很用力，一直挥到手放下"),
                    ],
                },
                {
                    "id": "notice_address",
                    "title": "她说她知道我住哪片",
                    "narrative": "特典会快结束，{{ta}}把最后一张拍立得推回来，忽然压低声音：『你家是不是在 XX 路那边？我前几天路过，好像看到你了。』笔尖在我手里停了一下。那个片区，我从没跟任何一个粉丝提过。",
                    "options": [
                        opt("nb_brush", "笑说她想多了，我住公司附近", "先撒个谎，把话岔开",
                            {"shiroi": 4, "psyche": -4}, 1, ["lied_address"],
                            note="我把话说得很轻松，手心却全是汗"),
                        opt("nb_cold", "当场冷下脸：别打听这些", "把界划得清清楚楚",
                            {"shiroi": -3, "ota_all": -5}, 0, ["set_cold_boundary"],
                            [dl("下周", {"enjou": 5}, "被 idol 当众凶了一句，她转头把这段发到了板子上")]),
                        opt("nb_report", "不动声色，回头报给运营", "把麻烦交给能处理的人",
                            {"shiroi": -4, "banzi": 2, "relation_all": -1}, 0, ["reported_mgmt"],
                            [dl("下周", {"shiroi": 5}, "运营找她谈了话，她却觉得这是'你在意我'的证据")]),
                    ],
                },
                {
                    "id": "notice_book",
                    "title": "她的小本子",
                    "narrative": "散场时{{ta}}的包没拉好，掉出一个小本子。我弯腰帮她捡，翻开的一角密密麻麻全是字——几月几日、哪个场、我穿了什么颜色的演出服、几点散场、从哪个门出去。她把本子抢回去的动作很快，脸有点红：『我、我就是记性好。』",
                    "options": [
                        opt("nc_playdumb", "把本子还她，说记性真好", "装傻，当作没看见里面的东西",
                            {"shiroi": 5, "psyche": -4}, 1, ["played_dumb"],
                            note="她松了口气，那口气松得太明显了"),
                        opt("nc_warn", "正色告诉她，这样让人害怕", "把不舒服直接说出口",
                            {"shiroi": -2, "ota_all": -3, "psyche": 2}, 0, ["spoke_fear"],
                            [dl("下周", {"enjou": 4}, "她觉得自己被误解，委屈地把这段上了板子")]),
                        opt("nc_publish", "把行程做成公开版发出去，让她没得可挖", "把能公开的都摊开",
                            {"shiroi": -3, "ota_all": 2, "fame": 2, "stamina": -4}, 0, ["opened_schedule"],
                            note="我把能公开的都摊在明面上，剩下的藏得更深"),
                    ],
                },
            ],
        },
        # ================= 拍1 试探 =================
        {
            "stage": 1, "key": "probe", "title": "试探",
            "gate": "dread ≥ 1",
            "enter_dread": 1,
            "variants": [
                {
                    "id": "probe_place",
                    "title": "不该出现的地方",
                    "narrative": "排练结束，我从后门出来买水，便利店门口的台阶上坐着{{ta}}。我们这个排练室从没对外公布过地址。她看见我，站起来，笑得像个偶遇：『好巧啊。』巧得让我后背发凉——她手里的塑料袋里，装着我常喝的那个牌子的水。",
                    "options": [
                        opt("pa_ignore", "当没看见，转身回排练室", "不给她任何反应",
                            {"shiroi": 3, "psyche": -4, "stamina": -2}, 1, ["avoided_place"],
                            note="我从后门退回去，那瓶水一直没敢去买"),
                        opt("pa_confront", "走过去问她怎么找到这里的", "把疑问当面问出来",
                            {"shiroi": 2, "psyche": -2, "ota_all": -2}, 1, ["asked_how_found"],
                            [dl("条件", {"enjou": 6}, "她把我'主动搭话'理解成了默许", condition="私生跟踪 ≥ 50")]),
                        opt("pa_move", "悄悄把排练时间往后挪，避开她", "打乱自己的节奏去躲",
                            {"shiroi": -3, "stamina": -5, "relation_all": -1}, 0, ["shifted_schedule"],
                            [dl("下周", {"shiroi": 4}, "她扑了空，开始在群里打听新的时间")]),
                    ],
                },
                {
                    "id": "probe_dm",
                    "title": "私信越来越密",
                    "narrative": "工作号的消息框里，{{ta}}一天能发几十条。从'今天排练累不累'，到'你是不是下午三点才起'，到'你昨天那个表情是不是不太开心'。她好像隔着一层屏幕，把我的作息摸得一清二楚。",
                    "options": [
                        opt("pb_reply", "挑着回几句，别把关系弄僵", "礼貌地维持着，不敢撕破脸",
                            {"shiroi": 4, "psyche": -2, "ota_all": 2}, 1, ["replied_dm"],
                            [dl("下周", {"shiroi": 4}, "她回得更快了，消息开始挑深夜发")]),
                        opt("pb_silence", "已读不回，冷处理", "不回应，让热度自己降下去",
                            {"shiroi": -2, "ota_all": -4, "psyche": -1}, 0, ["silent_dm"],
                            [dl("下周", {"shiroi": 5}, "沉默被她读成了'欲擒故纵'")]),
                        opt("pb_block", "直接拉黑，眼不见为净", "一刀切断这个入口",
                            {"shiroi": -5, "ota_all": -6, "psyche": 2}, 0, ["blocked_dm"],
                            [dl("下周", {"enjou": 5}, "她换了个号，用'被抛弃'的语气在板子上发长文")]),
                    ],
                },
                {
                    "id": "probe_gift",
                    "title": "送到后台的东西",
                    "narrative": "staff 递给我一个没署名的袋子，说是有人让转交的。里面是一条手织的围巾，还有一张卡片：一张我上周 Live 的抓拍，背面写着'你那天咳嗽了，多穿点'。照片的角度，是从很靠前、很偏的位置拍的——那个位置，从来不对外开放。",
                    "options": [
                        opt("pc_keep", "收下吧，一条围巾而已", "别把好意想得太坏",
                            {"shiroi": 4, "psyche": 1, "ota_all": 2}, 1, ["kept_gift"],
                            [dl("条件", {"shiroi": 5}, "会织东西的人，往往还有第二件、第三件", condition="私生跟踪 ≥ 45")]),
                        opt("pc_return", "让 staff 退回去，附一句'不用了'", "把界限还回去",
                            {"shiroi": -3, "ota_all": -3, "psyche": -2}, 0, ["returned_gift"],
                            [dl("下周", {"enjou": 4}, "退回去的围巾，成了板子上'耍大牌'的罪证")]),
                        opt("pc_backstage", "追查是谁放进后台的", "把漏洞堵上，别再来第二次",
                            {"shiroi": -2, "relation_all": -2, "stamina": -3}, 0, ["checked_backstage"],
                            [dl("下周", {"shiroi": 3}, "监控里那个身影，和{{ta}}对上了")]),
                    ],
                },
            ],
        },
        # ================= 拍2 逼近 =================
        {
            "stage": 2, "key": "close_in", "title": "逼近",
            "gate": "dread ≥ 2",
            "enter_dread": 2,
            "variants": [
                {
                    "id": "close_home",
                    "title": "跟到楼下",
                    "narrative": "十一点半收工，我打车回出租屋。下车走了两步，余光里那辆电动车也跟着停了。{{ta}}摘了头盔，远远地站着，冲我这边抬了抬下巴，像在说'我看着你上去'。楼道声控灯一层层亮起来的时候，我没敢回头。",
                    "options": [
                        opt("ca_face", "下楼去跟她把话说清楚", "把话摊开，哪怕撕破脸",
                            {"shiroi": 2, "psyche": -3, "stamina": -4}, 1, ["went_down"],
                            note="我说了很多，她一句没反驳，只是一直笑"),
                        opt("ca_hide", "关灯、拉窗帘，装作家里没人", "把自己藏起来",
                            {"shiroi": -2, "psyche": -5}, 0, ["hid_at_home"],
                            [dl("下周", {"shiroi": 5}, "第二天门口的脚垫，被人动过")]),
                        opt("ca_110", "站在楼道里，先打 110 备案", "留一个官方记录",
                            {"shiroi": -4, "banzi": 3, "relation_all": -1}, 0, ["called_police_early"],
                            [dl("条件", {"shiroi": 4}, "警察来了又走，她被劝离，第二天换了身衣服又出现", condition="私生跟踪 ≥ 40")]),
                    ],
                },
                {
                    "id": "close_photo",
                    "title": "寄到后台的东西升级了",
                    "narrative": "这次袋子里不是围巾了。是我某次随手发在朋友圈、半小时就删掉的一张照片——我家阳台的视角，拍到了对面楼的招牌。照片下面压着一行字：'从这里看，晚霞挺好的吧。'我盯着那行字，胃慢慢缩紧：这张照片，只存在过半小时。",
                    "options": [
                        opt("cb_shrug", "也许是有人截图，别多想", "往最不吓人的方向去想",
                            {"shiroi": 5, "psyche": -5}, 1, ["brushed_photo"],
                            note="我把照片删掉、账号设成私密，可那半小时已经收不回来了"),
                        opt("cb_lockdown", "把家里能反光的、能拍到的东西全遮住", "把家变成一只箱子",
                            {"shiroi": -3, "stamina": -6, "psyche": -1}, 0, ["locked_down"],
                            [dl("下周", {"shiroi": 3}, "我把自己关成一只箱子，她还是找得到缝隙")]),
                        opt("cb_ask", "在工作号上直接问她，是不是她", "当面求证，哪怕结果是坏消息",
                            {"shiroi": 2, "psyche": -2}, 1, ["asked_photo"],
                            [dl("条件", {"enjou": 5}, "她没承认，也没否认，只回了句'你终于肯理我了'", condition="私生跟踪 ≥ 50")]),
                    ],
                },
                {
                    "id": "close_stair",
                    "title": "堵在楼梯间",
                    "narrative": "加练到很晚，我在楼梯间遇到了{{ta}}。她不知在那儿等了多久，手里拎着便利店的袋子，说'给你带了宵夜'。声控灯灭了，楼梯间一下子黑下来，我能听见自己的心跳，也能听见她的呼吸——离得比我以为的近。",
                    "options": [
                        opt("cc_take", "接过袋子，快点脱身", "用最快的方式结束这场对峙",
                            {"shiroi": 3, "psyche": -3, "stamina": -2}, 1, ["took_bag"],
                            note="我把门在身后反锁了两道，才想起自己忘了问一句她怎么进来的"),
                        opt("cc_escape", "侧身挤过去，一路跑上楼", "什么都不说，先跑",
                            {"shiroi": -2, "psyche": -4, "stamina": -5}, 0, ["ran_upstairs"],
                            [dl("下周", {"shiroi": 4}, "我跑的那几步，她录了下来，配文'别怕我'")]),
                        opt("cc_friend", "当着她的面，给阿棠打电话让她来接", "拉一个人进来分担",
                            {"relation_A": 3, "shiroi": -3, "ota_all": -2}, 0, ["called_atang"],
                            [dl("条件", {"enjou": 4}, "她记住了阿棠，也记住了'我能靠谁'这件事", condition="私生跟踪 ≥ 45")]),
                    ],
                },
            ],
        },
        # ================= 拍3 越界 =================
        {
            "stage": 3, "key": "cross_the_line", "title": "越界",
            "gate": "dread ≥ 3",
            "enter_dread": 3,
            "variants": [
                {
                    "id": "line_oldaccount",
                    "title": "翻到了我的旧号",
                    "narrative": "半夜手机响，是个陌生号码。接起来，是{{ta}}的声音：『你以前那个号，我找到了。里面好多几年前的动态，那时候还没当偶像呢，好可爱。』她轻描淡写地说着，我握着手机的手在抖——那是我以为早就删干净的东西。",
                    "options": [
                        opt("la_plead", "求她别往外说", "放低姿态，先稳住",
                            {"shiroi": 3, "psyche": -5, "enjou": 2}, 1, ["pleaded"],
                            [dl("条件", {"enjou": 8}, "求人这件事本身，就成了把柄", condition="开盒风险 ≥ 55")]),
                        opt("la_threaten", "警告她再这样我就报警", "把最后的牌先亮出来",
                            {"shiroi": -2, "psyche": -2, "banzi": 2}, 0, ["threatened"],
                            [dl("下周", {"enjou": 6}, "她把'被威胁'也发了出来，配上截图")]),
                        opt("la_negotiate", "稳住她，先答应她一个见面的要求", "用妥协换喘息",
                            {"shiroi": 4, "psyche": -3, "ota_all": 2}, 1, ["promised_meeting"],
                            [dl("条件", {"shiroi": 8}, "一个要求被满足，只会生出下一个", condition="私生跟踪 ≥ 60")]),
                    ],
                },
                {
                    "id": "line_backstage",
                    "title": "她混进了后台",
                    "narrative": "Live 结束，我回后台拿东西，化妆镜前坐着{{ta}}。她不知怎么躲过了检票和 staff，正拿着我的口红在手上试色。听见我的脚步，她转过头，冲镜子里的我笑：『这个颜色，跟你那天照片里一模一样。』",
                    "options": [
                        opt("lb_scream", "喊人来，把她请出去", "当场把事情闹大",
                            {"shiroi": -3, "enjou": 3, "relation_all": -1}, 0, ["had_her_removed"],
                            [dl("下周", {"shiroi": 4}, "被请出去的时候她没有挣扎，只是一直看着我")]),
                        opt("lb_freeze", "愣在原地，不知道怎么办", "吓得动不了",
                            {"shiroi": 4, "psyche": -5}, 1, ["froze"],
                            note="等我回过神，她已经把口红放回原位，像什么都没发生过"),
                        opt("lb_pretend", "装作没事，赶紧把东西收走", "假装这只是个小插曲",
                            {"shiroi": 2, "psyche": -3, "stamina": -3}, 1, ["pretended_fine"],
                            [dl("下周", {"shiroi": 3}, "我走之后，化妆台上少了一样东西")]),
                    ],
                },
                {
                    "id": "line_door",
                    "title": "她出现在我家门口",
                    "narrative": "凌晨，有人在敲门。我从猫眼看出去——{{ta}}站在门外，手里拎着两杯还冒着热气的东西，头发被雨打湿了。她没喊，只是隔一会儿敲一下，很有耐心。屋里没开灯，我靠着门坐在地上，听着那一下一下的，比什么都响。",
                    "options": [
                        opt("lc_open", "开门，这样下去也不是办法", "把门打开，直面她",
                            {"shiroi": 5, "psyche": 2, "enjou": 2}, 1, ["opened_door"],
                            [dl("条件", {"psyche": -10}, "门开过一次，她就记住了这扇门后面有我", condition="开盒风险 ≥ 50")]),
                        opt("lc_silent", "不开，也不出声，等她自己走", "把自己缩进黑暗里",
                            {"shiroi": -2, "psyche": -6, "stamina": -2}, 0, ["stayed_silent"],
                            [dl("下周", {"shiroi": 5}, "天亮时门口留下两杯凉掉的东西，和一张写着'我等得起'的纸")]),
                        opt("lc_neighbor", "给物业和隔壁邻居发消息求助", "让外人介入",
                            {"shiroi": -4, "psyche": -2, "relation_all": -1}, 0, ["asked_neighbors"],
                            [dl("条件", {"banzi": 6}, "'地下偶像被私生堵门'的照片，从邻居的群里流了出去", condition="私生跟踪 ≥ 55")]),
                    ],
                },
            ],
        },
        # ================= 拍4 摊牌 =================
        {
            "stage": 4, "key": "showdown", "title": "摊牌",
            "gate": "dread ≥ 4 或 周 = 6（一季必须收场，不能留到季末还没处理）",
            "enter_dread": 4,
            "note": "最后一拍。四个方向对应四种结局走向，只写 flag 交结局系统判定：final_report（报警反杀）/ final_escape（搬家逃离）/ final_soft（心软接纳=最危险）/ final_confront（当面对峙、划清界限）。",
            "variants": [
                {
                    "id": "showdown_door",
                    "title": "堵在场馆后门",
                    "narrative": "决赛那天，散场后我走的后门。{{ta}}已经在那儿等着了，背靠着墙，像等了很久。她走过来，很自然地伸手要接我手里的包：『累了吧，我送你回去。』好像这一切都天经地义，好像我们之间从来不需要问一句'可以吗'。",
                    "options": [
                        opt("sd_report", "报警，把这条线彻底斩断", "让法律来处理，不留情面",
                            {"shiroi": -8, "enjou": 6, "banzi": 5, "psyche": 2}, 0, ["final_report"],
                            [dl("条件", {"fame": -8, "psyche": -4}, "事情闹上热搜，'偶像报警粉丝'几个字被人翻来覆去地骂", condition="炎上 ≥ 50")],
                            note="警车的灯照在她脸上，她第一次没有笑"),
                        opt("sd_escape", "连夜搬家，从此换个城市", "用钱和一段生活换一个清净",
                            {"money": -800, "stamina": -8, "shiroi": -10, "psyche": -4}, 0, ["final_escape"],
                            [dl("下周", {"shiroi": 3}, "她没立刻找上门，但我知道，有些人换个城市也能找到")],
                            note="搬家那天下着雨，我把所有定位、所有窗帘都换了一遍"),
                        opt("sd_soft", "心软了，把她留下", "她也只是个太用力喜欢的人",
                            {"shiroi": 8, "psyche": 5, "kaibox": 6, "ota_all": -2}, 0, ["final_soft"],
                            [dl("条件", {"shiroi": 10, "psyche": -12, "enjou": 10}, "最危险的温柔：她终于'名正言顺'地站在了门口", condition="私生跟踪 ≥ 70")],
                            note="我把门留了一条缝，那条缝从此再没关上过"),
                        opt("sd_confront", "当面把一切摊开，说清楚再也不见", "不为难她，也不再退让",
                            {"shiroi": -4, "psyche": -5, "ota_all": -2}, 0, ["final_confront"],
                            [dl("条件", {"enjou": 6}, "她答应得很快，太快乐，快到我知道她只是在等下一次", condition="炎上 ≥ 40")],
                            note="我把话说得很慢、很清楚，她点头，眼睛却是空的"),
                    ],
                },
                {
                    "id": "showdown_backstage",
                    "title": "后台的最后一次",
                    "narrative": "换衣间只剩我一个人，门被推开，是{{ta}}。她没有像往常那样笑，把手里的东西放在桌上——是这一季所有关于我的照片、截图、小票，码得整整齐齐。她说：『我把这些都带来了。你选吧，是让我继续喜欢，还是让我毁给所有人看。』",
                    "options": [
                        opt("sb_report", "报警，把这些东西都交给警察", "让流程接管，不再一个人扛",
                            {"shiroi": -8, "enjou": 7, "banzi": 6, "psyche": 2}, 0, ["final_report"],
                            [dl("条件", {"fame": -8, "psyche": -4}, "警察带走了那些照片，也带走了团里最后一点安宁", condition="炎上 ≥ 50")],
                            note="她走的时候很安静，安静得像早就等着这一刻"),
                        opt("sb_escape", "不报警，偷偷搬走，消失一段时间", "不惊动任何人，自己离开",
                            {"money": -700, "stamina": -7, "shiroi": -9, "psyche": -5}, 0, ["final_escape"],
                            [dl("下周", {"shiroi": 3}, "躲开的第一周睡得很沉，第二周开始，听见敲门就心跳")],
                            note="我把能证明'我住哪'的东西，全烧了"),
                        opt("sb_soft", "心软了：'那就继续喜欢吧，我认了'", "她把这些都收着，某种意义上也是一种守护",
                            {"shiroi": 8, "psyche": 4, "kaibox": 7, "ota_all": -3}, 0, ["final_soft"],
                            [dl("条件", {"shiroi": 10, "psyche": -12, "enjou": 10}, "她把'照片'变成了'筹码'，而我把'心软'给成了'授权'", condition="私生跟踪 ≥ 70")],
                            note="她笑了，是那种终于被允许靠近的笑"),
                        opt("sb_confront", "当着她的面，把那些东西一件件扔进垃圾桶", "用行动替自己划界",
                            {"shiroi": -5, "psyche": -4, "ota_all": -2}, 0, ["final_confront"],
                            [dl("条件", {"enjou": 6}, "垃圾桶里的东西，第二天又整整齐齐出现在门口", condition="炎上 ≥ 40")],
                            note="我一件一件地扔，她一件一件地看，谁都没说话"),
                    ],
                },
                {
                    "id": "showdown_call",
                    "title": "深夜的电话",
                    "narrative": "凌晨三点，电话响。{{ta}}的声音很平静，平静得反常：『我在你家楼下。别下来，我就想让你听着——我喜欢你，喜欢到有点不知道该怎么办了。』背景里是风声，和很远的地方传来的、若有若无的警笛。",
                    "options": [
                        opt("sc_report", "挂掉电话，直接报警并说明位置", "把这件事交给应急的人",
                            {"shiroi": -7, "enjou": 6, "banzi": 5, "psyche": 1}, 0, ["final_report"],
                            [dl("条件", {"fame": -8, "psyche": -4}, "'偶像深夜报警'上了热搜，评论两极，没有赢家", condition="炎上 ≥ 50")],
                            note="警车到的时候，她没跑，只是抬头看了看我家的窗"),
                        opt("sc_escape", "天亮就搬，谁都别告诉", "一个人悄悄地撤",
                            {"money": -750, "stamina": -9, "shiroi": -9, "psyche": -6}, 0, ["final_escape"],
                            [dl("下周", {"shiroi": 3}, "换了城市换了窗帘，可深夜的电话一响，我还是会先看一眼来电显示")],
                            note="搬完最后一箱，我站在空房间里，第一次觉得安静也是会吓人的"),
                        opt("sc_soft", "心软了，下楼去见她", "就这一次，把话说开，也许就不一样了",
                            {"shiroi": 9, "psyche": 6, "kaibox": 7, "ota_all": -3}, 0, ["final_soft"],
                            [dl("条件", {"shiroi": 10, "psyche": -12, "enjou": 10}, "她终于'等到'了这一次，也终于知道，只要等，就等得到", condition="私生跟踪 ≥ 70")],
                            note="夜深得像水，她看见我下楼，眼睛一下子亮了"),
                        opt("sc_confront", "在电话里说清楚：这一次，是最后一次", "隔着屏幕把界限定死",
                            {"shiroi": -4, "psyche": -5, "ota_all": -2}, 0, ["final_confront"],
                            [dl("条件", {"enjou": 6}, "电话那头沉默了很久，然后轻轻说了一句'好'——好得让我不安", condition="炎上 ≥ 40")],
                            note="我一个字一个字说完，挂断时才发现自己在发抖"),
                    ],
                },
            ],
        },
    ],
}

with open(OUT, "w", encoding="utf-8") as f:
    json.dump(doc, f, ensure_ascii=False, indent=2)
    f.write("\n")

print("WROTE", OUT)
print("stages:", len(doc["stages"]), "variants each:", [len(s["variants"]) for s in doc["stages"]])
