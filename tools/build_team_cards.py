# -*- coding: utf-8 -*-
"""补团内冲突卡 + 队友关系卡（2026-11-14 用户要求「加几张团内冲突卡」「怎么和队友刷好感谈恋爱」）。

两条路：
  1. team.json 新增 6 张卡：分钱不均 / 露露抢 C 位 / 小满被骂哭 / 阿棠想退团 /
     排练迟到被点名 / 团内冷战。都是「两难」：站一边就一定得罪另一边。
  2. 新增 `data/cards/team_bond.json`：3 组「一起做一件事」的关系卡
     （阿棠线 relation_A、露露线 relation_B、小满线 relation_C），
     每张都是「花时间/花钱换关系」，且带负项，不能纯赚。
"""
import json
import io
import os

BASE = r"C:\Users\kk\Documents\deepseek-harness\default-workspace\聚场\data\cards"


def o(oid, label, desc, im, delayed=None):
    return {"id": oid, "label": label, "desc": desc,
            "immediate": im, "delayed": delayed or []}


CARDS = [
    {
        "id": "team_money_split",
        "type": "团内",
        "title": "分钱的时候",
        "gate": "周 ≥ 2",
        "weight": 1.1,
        "cooldown": 4,
        "narrative": "运营把这一场的账摊在桌上，说特典收入要按人数分。露露当场就笑了：『按人数？我这一场买券的人最多。』小满低头看手机，阿棠没说话。运营看着我说：『你是 C 位，你说怎么分。』",
        "options": [
            o("split_by_tickets", "按券分，谁卖得多谁多拿",
              "公平，但把「谁更像商品」摆到了台面上",
              {"relation_B": 6, "relation_C": -5, "relation_A": -2, "psyche": -2}),
            o("split_even", "平分，谁也别多谁也别少",
              "保住感情，露露会记这一笔",
              {"relation_A": 4, "relation_C": 4, "relation_B": -6, "fame": -1}),
            o("split_by_need", "按谁这个月更缺钱来分",
              "把私事当依据，谁都得说点不想说的",
              {"relation_C": 5, "relation_B": -3, "stamina": -3, "psyche": -4},
              [{"when": "下周", "effect": {"relation_B": -3},
                "note": "露露私下跟人说，C 位拿钱的时候讲的是感情"}]),
        ],
    },
    {
        "id": "team_center_push",
        "type": "团内",
        "title": "招新的海报",
        "gate": "人气 ≥ 20 且 周 ≥ 2",
        "weight": 1.0,
        "cooldown": 5,
        "narrative": "运营做了新海报，主视觉是两个人，露露站在我旁边，位置其实是齐的。她看了两遍，忽然问：『为什么我不能站中间？』运营端着手机打哈哈，让我决定。",
        "options": [
            o("give_her_center", "让她站中间，我去旁边",
              "队里会松一口气，外面会说这个团乱了",
              {"relation_B": 10, "fame": -4, "psyche": -3, "relation_A": 2}),
            o("keep_center_dry", "照原样，说这是运营定的",
              "把决定推给上面，谁也不得罪，也没人舒服",
              {"relation_B": -5, "psyche": 2, "enjou": 2}),
            o("two_posters", "说做两版，一人一版轮着发",
              "两边都照顾了，成本是时间和钱",
              {"money": -180, "relation_B": 4, "relation_all": 2, "stamina": -4}),
        ],
    },
    {
        "id": "team_mamman_cried",
        "type": "团内",
        "title": "排练被骂哭了",
        "gate": "周 ≥ 2",
        "weight": 1.1,
        "cooldown": 4,
        "narrative": "排练到一半，老师指着小满说『你再这样下去就别上了』。小满没顶嘴，一直低着头。散场以后她坐在台阶上没走，裙摆上还沾着排练室地板的灰。我站在门口，里面灯还亮着，老师在收音响。",
        "options": [
            o("sit_with_her", "走过去陪她坐一会儿，什么也不说",
              "今晚练不成了，可她需要有人在场",
              {"relation_C": 9, "stamina": -4, "psyche": 2}),
            o("go_back_practice", "回去接着练，明天再来找她",
              "先把自己的事做对，她会懂也会记",
              {"relation_C": -4, "dance": 2, "psyche": -3}),
            o("talk_to_teacher", "去跟老师说，能不能再给她一次机会",
              "替她把话说出口，老师的火转到这边",
              {"relation_C": 7, "enjou": 3, "psyche": -5},
              [{"when": "本周", "effect": {"relation_all": -2},
                "note": "老师后来在群里点了名，说有人替别人求情"}]),
        ],
    },
    {
        "id": "team_atang_quit",
        "type": "团内",
        "title": "她说她大概要走了",
        "gate": "阿棠关系 ≥ 55 且 周 ≥ 3",
        "weight": 1.0,
        "cooldown": 6,
        "narrative": "阿棠把手机递过来，屏幕上是她妈发的一串语音，标题写着『房子的事』。她收回手机，说：『我可能下个月就不干了。』说得很轻，像怕我听见。排练室外面有人在搬箱子，声音一下一下的。",
        "options": [
            o("ask_her_stay", "问她留下要什么条件，能帮的都帮",
              "把她的难处接过来一部分",
              {"relation_A": 12, "money": -300, "psyche": -4, "stamina": -3}),
            o("let_her_go", "说不管你走不走，我都记得这一段",
              "不拦，把话说到，心里空一块",
              {"relation_A": 6, "psyche": -6}),
            o("ask_ops", "去问运营有没有办法留人",
              "把事情交给有办法的人，也交出去了她的私事",
              {"relation_A": -3, "relation_all": 2, "enjou": 2, "psyche": 2}),
        ],
    },
    {
        "id": "team_late_rollcall",
        "type": "团内",
        "title": "又是她迟到",
        "gate": "周 ≥ 2 且 体力 < 60",
        "weight": 1.0,
        "cooldown": 4,
        "narrative": "第三次了。露露踩着点到，包都不换就站进队形。老师看了我一眼，意思是『你是 C 位』。队里没人说话，可所有人都在等一个态度，包括露露自己。",
        "options": [
            o("cover_for_her", "跟大家说这次算我的",
              "把事压下去，队里会记我一笔",
              {"relation_B": 6, "relation_A": -3, "relation_C": -2, "psyche": -4}),
            o("call_it_out", "当着所有人说清楚规矩",
              "规矩立住了，露露会记住是我开的口",
              {"relation_B": -8, "relation_A": 4, "relation_C": 2, "psyche": -2}),
            o("ask_why_private", "散场以后单独问她怎么了",
              "先问原因，再谈规矩",
              {"relation_B": 3, "stamina": -3, "psyche": -2},
              [{"when": "条件", "condition": "露露关系 ≥ 65", "effect": {"relation_B": 4},
                "note": "她后来没再迟到，还在群里说了句『以后我不拖团里后腿』"}]),
        ],
    },
    {
        "id": "team_cold_war",
        "type": "团内",
        "title": "群里安静了三天",
        "gate": "周 ≥ 3",
        "weight": 0.9,
        "cooldown": 5,
        "narrative": "排练完没人走，也没人说话。收东西的声音特别响。有人把空调关了，有人又重新打开。我知道前天那件事还没过去，可是谁也不想当第一个开口的人。",
        "options": [
            o("break_ice", "先开口，把那件事摆出来说",
              "撕开一次，可能好也可能更糟",
              {"relation_all": 3, "psyche": -5, "stamina": -2}),
            o("let_it_rot", "谁都不提，让时间过去",
              "短期太平，坏的会沉下去",
              {"psyche": 2, "relation_all": -3},
              [{"when": "条件", "condition": "队友关系均值 < 45", "effect": {"relation_all": -4},
                "note": "那三天的事没人再提，可排练时再没人接我的话"}]),
            o("buy_them_food", "自掏腰包点了宵夜，边吃边聊",
              "钱能买一点缓冲",
              {"money": -120, "relation_all": 4, "stamina": -2}),
        ],
    },
]

BOND = [
    {
        "id": "bond_atang_practice",
        "type": "团内关系",
        "title": "多留一个小时",
        "gate": "阿棠关系 ≥ 45 且 周 ≥ 1",
        "weight": 1.2,
        "cooldown": 3,
        "narrative": "排练散了她没走，说想把最后那一段再对一遍。灯只开了一半，我们从对着镜子抠动作，到就那么坐在地上说话。窗外马路的声音一阵一阵的，她讲她以前在工厂做的那半年。",
        "options": [
            o("stay_and_listen", "留下来，听她讲完",
              "多一个小时的体力，换她多讲一点",
              {"relation_A": 9, "stamina": -6, "psyche": 2}),
            o("stay_but_leave_early", "陪半小时，说自己明天还有早班",
              "有关系，也有分寸",
              {"relation_A": 4, "stamina": -2}),
            o("ask_about_hers", "把话头转过去，问她怎么看团里的事",
              "聊工作以外的，走近一步也踩一步",
              {"relation_A": 5, "relation_B": -3, "psyche": -1}),
        ],
    },
    {
        "id": "bond_atang_birthday",
        "type": "团内关系",
        "title": "她的生日在这周",
        "gate": "阿棠关系 ≥ 60 且 周 ≥ 2",
        "weight": 1.1,
        "cooldown": 6,
        "narrative": "我是在她手机壳后面贴的口红印促销单上看见生日的。她一个字都没提，排练照常来，照常第一个走。小店里的蛋糕要三百多，钱还在房租里。",
        "options": [
            o("buy_cake", "买了，散场以后在后台切",
              "钱没了，她那晚吃了两口就说够了",
              {"money": -320, "relation_A": 14, "psyche": 3},
              [{"when": "下周", "effect": {"relation_A": 4},
                "note": "她第二天带了盒自己做的菜放在排练室冰箱里，标签写着我的名字"}]),
            o("handwritten", "手写一张卡片，贴在她柜门上",
              "不值钱，但只有我看见了这个日子",
              {"relation_A": 8, "stamina": -2, "psyche": 2}),
            o("say_nothing", "不提，免得她有负担",
              "尊重她的沉默，也错过一次",
              {"relation_A": -2, "psyche": -1}),
        ],
    },
    {
        "id": "bond_lulu_after",
        "type": "团内关系",
        "title": "散场以后只剩我们两个",
        "gate": "露露关系 ≥ 45 且 周 ≥ 2",
        "weight": 1.1,
        "cooldown": 4,
        "narrative": "收完器材，露露在门口点了一根烟，看见我只抬了抬下巴。她说台上有几个动作我今天抢了拍子，说她要是再快点就可能撞上我。语气还是那副刺样，但不是骂人的意思。",
        "options": [
            o("admit_and_fix", "认下来，说下次配合她",
              "把刺接住，她会松一点",
              {"relation_B": 8, "psyche": -2, "dance": 1}),
            o("push_back_friendly", "怼回去：那你倒是快点",
              "用她的方式相处，关系往另一种方向走",
              {"relation_B": 6, "enjou": 2, "psyche": 3}),
            o("leave_quiet", "说累了，先走",
              "不往前走，也省下力气",
              {"relation_B": -2, "stamina": 3}),
        ],
    },
    {
        "id": "bond_lulu_share",
        "type": "团内关系",
        "title": "她问我要不要一起打车",
        "gate": "露露关系 ≥ 55 且 周 ≥ 3",
        "weight": 1.0,
        "cooldown": 5,
        "narrative": "下大雨，打车软件一直显示排队。露露把伞撑开，看我在门口犹豫：『拼一辆？我不咬人。』她身上有股很重的洗衣粉味，站得很近，近到我能看见她伞骨上一小块锈。",
        "options": [
            o("share_cab", "上车，各坐一边，聊一路",
              "这一路上的话，比三个月排练都多",
              {"relation_B": 10, "money": -60, "psyche": 2}),
            o("refuse_politely", "说有人来接，自己等雨小",
              "守住距离，她也没再多说",
              {"relation_B": -1, "stamina": -3}),
            o("walk_together", "说干脆一起走过去，路上有伞",
              "省了钱，长了距离",
              {"relation_B": 5, "stamina": -8, "psyche": 3},
              [{"when": "条件", "condition": "露露关系 ≥ 70", "effect": {"relation_B": 3},
                "note": "后来组里有人开玩笑说我们两个走得很近，她当场把话顶回去了"}]),
        ],
    },
    {
        "id": "bond_mamman_note",
        "type": "团内关系",
        "title": "她把我写进了她的本子",
        "gate": "小满关系 ≥ 50 且 周 ≥ 2",
        "weight": 1.1,
        "cooldown": 4,
        "narrative": "小满的本子掉在地上摊开着，我捡起来那一眼，看见自己的名字写满了半页，后面是日期，还有一句『今天她夸我音准了』。她冲过来把本子抢回去，耳朵红得很，说这个是随便写的。",
        "options": [
            o("pretend_unseen", "说没看清，把本子还给她",
              "守住她的脸面，也把门留一条缝",
              {"relation_C": 5, "psyche": -3}),
            o("praise_her", "说那页最后一句是真的，她音准确实稳了",
              "承认看见了，她当晚大概睡不着",
              {"relation_C": 11, "psyche": 2, "stamina": -2}),
            o("joke_it", "开玩笑说那本子以后得拍给我看",
              "玩笑让气氛过去，也让她当真了一半",
              {"relation_C": 4, "enjou": 1, "psyche": -2}),
        ],
    },
    {
        "id": "bond_mamman_breakfast",
        "type": "团内关系",
        "title": "排练室的早饭",
        "gate": "小满关系 ≥ 45 且 周 ≥ 1",
        "weight": 1.2,
        "cooldown": 3,
        "narrative": "周六早上到的时候，排练室的长椅上放着一个保温袋，里面是两个包子和一杯豆浆，还有一张便利贴：『今天别看手机。』字很工整，还画了个笑脸。袋子上写着我的名字，用铅笔写的。",
        "options": [
            o("eat_together", "等她来了一起吃，问问她几点起的",
              "包子凉了，可话就热了",
              {"relation_C": 8, "stamina": -4, "psyche": 2}),
            o("eat_alone", "吃了，发一句『谢谢，很好吃』",
              "礼貌的温度，够暖不够近",
              {"relation_C": 3, "stamina": 3, "psyche": -1}),
            o("buy_back", "第二天买两份早饭放回去",
              "用她的方式还她",
              {"relation_C": 7, "money": -40, "psyche": 1}),
        ],
    },
]


def main():
    p = os.path.join(BASE, "team.json")
    d = json.load(io.open(p, encoding="utf-8"))
    have = {c["id"] for c in d["cards"]}
    added = 0
    for c in CARDS:
        if c["id"] in have:
            continue
        d["cards"].append(c)
        added += 1
    io.open(p, "w", encoding="utf-8").write(
        json.dumps(d, ensure_ascii=False, indent=1) + "\n")

    p2 = os.path.join(BASE, "team_bond.json")
    doc = {"_meta": {"kind": "cards", "name": "队友关系",
                     "note": "和队友刷好感的日常卡：每一张都要花时间或花钱，"
                             "且都有负项，不能纯赚。"},
           "cards": BOND}
    io.open(p2, "w", encoding="utf-8").write(
        json.dumps(doc, ensure_ascii=False, indent=1) + "\n")
    print("team.json +%d (total %d)" % (added, len(d["cards"])))
    print("team_bond.json %d" % len(BOND))


if __name__ == "__main__":
    main()
