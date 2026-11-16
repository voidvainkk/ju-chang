# -*- coding: utf-8 -*-
"""构建 data/ota_memory.json —— OTA「记忆回考」线索池。

机制（2026-11-14 用户拍板，见 HANDOFF「记忆回考」）：
- 第一次她随口说出一个三选一的细节（值锁定）；后面某场她用一句自然问法再提；
- 我只回三个同类值，答对加分、答错直接扣分，没有缓冲/补救；
- 分值：轻 +2/−3、中 +4/−5、重 +6/−8；
- 每场特典会约 30% 概率刷一次，一季约 2~3 次；
- 答错反应按 OTA 原型写（gravity/bold/mom/angler/shy/nerd/joker）。
- 同一局内真值锁定，每次重开重新掷。

占位符：{truth} = 本局真值，{wrong} = 玩家选的错项。
台词里的「你」出现在对白『』内，是本行 POV 允许的。

非游戏代码，内容构建脚本，保留。改文案改这里再跑，别手改 json。
"""
import json, os

BASE = r"C:\Users\kk\Documents\deepseek-harness\default-workspace\聚场\data"
OUT = os.path.join(BASE, "ota_memory.json")

# 分值表
POINTS = {"light": {"good": {"ota_all": 2}, "bad": {"ota_all": -3}},
          "mid":   {"good": {"ota_all": 4}, "bad": {"ota_all": -5}},
          "heavy": {"good": {"ota_all": 6}, "bad": {"ota_all": -8}}}

PROTO = ["gravity", "bold", "mom", "angler", "shy", "nerd", "joker"]

# ============================================================
# 线索登记表（2026-11-14 加）
# 个人线砍掉后，这 21 条线索没有了原来的 _meta.memory_key 登记处。
# 现在由 ota_memory.json 自己带一份 memory_key，validate_all 从这里取。
# 以后新增线索，必须同时在这张表里加一行。
# ============================================================
CLUE_LABEL = {
    "fruit_craving": "她念叨过想吃的水果",
    "food_hate": "她不吃什么",
    "daily_drink": "她下午三点续命的那一杯",
    "pet_dream": "她壁纸上看两年的那只",
    "weather_hate": "她最受不了的天气",
    "loop_song": "她单曲循环的那首歌",
    "commute": "她每天最不想醒的那趟车",
    "snack": "她包里常年那包零食",
    "phone_app": "她手机里最常打开的那个",
    "work_file": "她这周一直在改的东西",
    "off_work": "她几点才下班",
    "pet_type": "她家养的那只",
    "dream_place": "她一直没去成的地方",
    "family_pressure": "她家里一直在催的那件事",
    "money_habit": "她最舍得的那个花钱去处",
    "commuter_route": "她来一趟要怎么折腾",
    "first_visit": "她第一次来看 live 的原因",
    "spare_thing": "她没在追团的话会去做的事",
    "alone_reason": "她这么常来的真正原因",
    "what_keeps": "她说会一直来的理由",
    "prev_group": "她上一个团是怎么散场的",
}


def clue(key, level, cat, set_, say, ask, react_bad, react_good):
    assert level in POINTS, level
    assert len(set_) == 3, key
    assert len(ask) == 3, key
    assert set(react_bad) == set(PROTO), (key, sorted(react_bad))
    assert set(react_good) == set(PROTO), (key, sorted(react_good))
    return {
        "key": key,
        "level": level,
        "category": cat,
        "set": set_,
        "say": say,
        "ask": ask,
        "points": POINTS[level],
        "react_good": react_good,
        "react_bad": react_bad,
    }


# ============================================================
# 轻档 +2 / -3
# ============================================================

L01 = clue(
    "fruit_craving", "light", "吃的",
    ["荔枝", "芒果", "山竹"],
    "『今天路上看见卖{truth}的，一筐一筐的。我站在那儿看了半天，最后没买。』",
    ["『我上次跟你说过我想吃{truth}来着？我自己倒忘了。』",
     "『路过水果摊了，看见一筐一筐的。你说我是不是该买{truth}来着？』",
     "『我明天要去买上次说的那个了，{truth}。』"],
    react_bad={
        "gravity": "『……不是{wrong}。是{truth}啊。』她把袋子在手里转了两圈，又补一句：『不过也可能是我记错了。』",
        "bold":    "『{wrong}？哈哈哈哪来的{wrong}，我说的是{truth}！』她拍了下桌子，『罚你下次多买两张券。』",
        "mom":     "『哎呀，是{truth}啦。你要记牢一点，我说话你得多听听。』",
        "angler":  "『嗯？我好像没说过吧……不对，说过了，是{truth}。』",
        "shy":     "『……没事，我就随口一说。』声音变小，很快换了话题。",
        "nerd":    "『我上次说的是{truth}。』他顿了一下，『不过也可能是我记岔了。』然后把话题收回自己的本子里。",
        "joker":   "『{wrong}？可以啊，那我也改喜欢{wrong}了，反正一样贵。』",
    },
    react_good={
        "gravity": "『……你记得。』她低下头，把袋子往我这边推了推，『分你一半。』",
        "bold":    "『哟，记性不错啊。』他笑得很响，『这顿我请。』",
        "mom":     "『哎哟你还是记得的。』她笑得眼睛都弯了，『那我就放心了。』",
        "angler":  "『哎呀被你记住了。』他很受用地偏了偏头，『那我下次得多说几句。』",
        "shy":     "『……嗯。』她很轻地点了下头，把脸往围巾里缩了一点。",
        "nerd":    "『对。』他眼睛亮了一下，很快又装作在看本子。",
        "joker":   "『满分。』她鼓了两下掌，掌声很敷衍，嘴角没压住。",
    },
)

L02 = clue(
    "food_hate", "light", "吃的",
    ["香菜", "折耳根", "葱"],
    "『今晚那份凉菜又被{truth}毁了，我挑了半天。』",
    ["『今天点的那份，我一吃就皱眉——我上次说{truth}不能碰来着吧？』",
     "『菜单上又给我加了{truth}，我是不是说过我最受不了这个？』",
     "『点单的时候我不是说了别放{truth}吗。』"],
    react_bad={
        "gravity": "『……不是{wrong}，是{truth}。』她顿了一下，『算了，反正我也没细说过。』",
        "bold":    "『{wrong}？我什么时候爱吃{wrong}了，我这辈子都没吃下去过。』",
        "mom":     "『是{truth}呀。这个不能记错，吃错了要难受一晚上的。』",
        "angler":  "『{wrong}？嗯……好像也行。』他笑得有点勉强。",
        "shy":     "『……都行，都行。』她低头把菜往边上拨。",
        "nerd":    "『是{truth}。』他把筷子放下，『我上次说得很清楚。』",
        "joker":   "『{wrong}好啊，补维生素的。』她自己也不信。",
    },
    react_good={
        "gravity": "『你还记得。』她笑了一下，很快，像怕被发现。",
        "bold":    "『对！就这个。』他把碗往前一推，『那你帮我挑一下。』",
        "mom":     "『看看，记住了。』她满意地点头，『这就对了。』",
        "angler":  "『哎你还挺上心。』他挑了下眉。",
        "shy":     "『……谢谢。』她把那几根挑到一边。",
        "nerd":    "『嗯。』他点了点头，把这件事记在心里那种点头。",
        "joker":   "『记性可以啊。』她夹了一筷子放到我碗里，『奖励你的。』",
    },
)

L03 = clue(
    "daily_drink", "light", "喝的",
    ["冰美式", "奶茶", "气泡水"],
    "『下午三点不喝一杯{truth}，我整个人是废的。』",
    ["『今天{truth}喝晚了，现在眼睛瞪得像铜铃。』",
     "『我下午那股劲儿又没了……我平时靠{truth}续着的吧？』",
     "『明天得去买{truth}了，断了一天就不行。』"],
    react_bad={
        "gravity": "『……不是{wrong}啦，是{truth}。』她笑了一下，笑得有点空。",
        "bold":    "『{wrong}？我喝{wrong}会失眠一整晚，我是那种人吗？』",
        "mom":     "『是{truth}啦。年轻人要少喝点这些，不过你要记着是哪个。』",
        "angler":  "『{wrong}也挺好。』他敷衍地点点头，『都行。』",
        "shy":     "『……嗯，都行。』",
        "nerd":    "『{truth}。』他说完就不再解释。",
        "joker":   "『{wrong}行，反正都是水。』",
    },
    react_good={
        "gravity": "『……你连这个都笑了。』她自己先笑出来。",
        "bold":    "『记得挺牢。』他伸手比了个六。",
        "mom":     "『乖。』她说得很自然。",
        "angler":  "『哎，你记我这些干什么。』他嘴上这么说，笑得挺开心。",
        "shy":     "『……嗯。』她低头搅了两下杯子。",
        "nerd":    "『对。』他难得笑了一下。",
        "joker":   "『懂我。』她抬了抬下巴。",
    },
)

L04 = clue(
    "pet_dream", "light", "生活",
    ["橘猫", "柯基", "仓鼠"],
    "『我手机壁纸一直是只{truth}，看了两年都没敢养。』",
    ["『我昨天终于去撸到{truth}了，就那一只。』",
     "『我要是养宠物，你说我该养{truth}来着？我上次好像说过。』",
     "『今天在楼下看见一只{truth}，看得我走不动路。』"],
    react_bad={
        "gravity": "『……是{truth}，不是{wrong}。』她低头看了眼手机，没再说什么。",
        "bold":    "『{wrong}？我壁纸是{wrong}吗？』他自己拿起手机看了一眼，『……哦，不是。』",
        "mom":     "『是{truth}呀。这你都记不住，还说心疼我。』她语气没有变差，就是这样一说。",
        "angler":  "『{wrong}也挺可爱的。』他笑着把话岔开。",
        "shy":     "『……嗯。』",
        "nerd":    "『{truth}。』他抬起头，『我壁纸两年没换过了。』",
        "joker":   "『{wrong}？那我改养{wrong}，更有画面感。』",
    },
    react_good={
        "gravity": "『……你还记得这个。』她把手机翻过来扣在桌上，耳朵红了。",
        "bold":    "『哟。』他提高了声音，『那你到时候来给我撸猫。』",
        "mom":     "『记得还挺清楚。』她笑，『那我就真去养了。』",
        "angler":  "『记得这么牢干嘛。』他笑得有点不自然。",
        "shy":     "『……嗯。』她小声说，『其实我存了好多照片。』",
        "nerd":    "『对。』他点头，『我列了一张清单。』",
        "joker":   "『所以你是想让我破费。』她笑起来。",
    },
)

L05 = clue(
    "weather_hate", "light", "生活",
    ["下雨天", "大太阳", "起风"],
    "『今天出门一趟全废，我最受不了{truth}。』",
    ["『你猜我今天又被{truth}整成什么样。』",
     "『这个天气真的不行……我最烦的好像是{truth}吧。』",
     "『明天又是{truth}，我出门的勇气都没了。』"],
    react_bad={
        "gravity": "『……{wrong}？是{truth}啊。』她顿了一下，『算了，我本来也不该指望这个。』",
        "bold":    "『{wrong}？我什么时候怕{wrong}了，上次{wrong}我不照样来了。』",
        "mom":     "『是{truth}啦。你连我怕什么都不知道。』说完自己先笑了。",
        "angler":  "『{wrong}啊……也行。』",
        "shy":     "『……都一样。』",
        "nerd":    "『{truth}。』他纠正得很轻。",
        "joker":   "『{wrong}我也烦。都烦。』",
    },
    react_good={
        "gravity": "『……你记得。』她把伞往我这边偏了一点。",
        "bold":    "『对，就这个。』他一拍大腿，『你也受不了吧。』",
        "mom":     "『看，我说过的你就记得。』她挺满意。",
        "angler":  "『被记着的感觉还挺好。』他笑，『我不说了。』",
        "shy":     "『……嗯。』",
        "nerd":    "『对。』他罕见地笑了一下，『我对天气敏感。』",
        "joker":   "『知道的还不少。』",
    },
)

L06 = clue(
    "loop_song", "light", "爱好",
    ["一首老歌", "一个乐队", "一段钢琴曲"],
    "『最近一直在循环{truth}，循环到会背了。』",
    ["『我是不是说过我最近在循环{truth}？』",
     "『今天又在听那个，一听就停不下来。我上次说我在循环{truth}来着？』",
     "『耳机里还是{truth}，我大概要听到吐。』"],
    react_bad={
        "gravity": "『……不是{wrong}。是{truth}。』她摘下一只耳机，没有递过来。",
        "bold":    "『{wrong}？那是上上个月的事了。』他笑着摆手。",
        "mom":     "『是{truth}啦。你说你连这个都记不住。』",
        "angler":  "『{wrong}也挺好听。』",
        "shy":     "『……嗯。』她把耳机收回去。",
        "nerd":    "『{truth}。』他纠正，『第五十三遍了。』",
        "joker":   "『{wrong}，那我改听{wrong}，反正我不挑。』",
    },
    react_good={
        "gravity": "『……你还记得。』她把耳机递过来一半，『要不要听。』",
        "bold":    "『对！』他直接把手机递过来，『这首给你。』",
        "mom":     "『记得就好。』她笑得像放心了。",
        "angler":  "『哟，还知道这个。』",
        "shy":     "『……嗯。』她小声哼了两句，很快停了。",
        "nerd":    "『对。』他点头，眼神认真起来。",
        "joker":   "『我唱两句给你听？』",
    },
)

L07 = clue(
    "commute", "light", "生活",
    ["早高峰", "末班车", "周末的清晨"],
    "『每天{truth}那一趟，是我一天里最不想醒的时候。』",
    ["『那天{truth}的地铁我睡着了，坐过三站。』",
     "『今天又是{truth}，我整个人是飘着的。』",
     "『上周{truth}我差点没挤上来。』"],
    react_bad={
        "gravity": "『……是{truth}，不是{wrong}。』她说得很轻，『没关系，本来就是我自己在熬。』",
        "bold":    "『{wrong}？那是{wrong}吗，我什么时候坐过{wrong}。』",
        "mom":     "『是{truth}啦。你听听，这孩子多不容易。』",
        "angler":  "『{wrong}也挺挤的。』",
        "shy":     "『……嗯。』",
        "nerd":    "『{truth}。』",
        "joker":   "『{wrong}？那我明天试试。』",
    },
    react_good={
        "gravity": "『……你真的在听我说话。』她低下头，声音更小了。",
        "bold":    "『哈哈，对。』他笑，『你也坐那趟？』",
        "mom":     "『你记得这个，阿姨心里舒服。』她把自己说成阿姨，又笑了。",
        "angler":  "『被你这么一说，我都不好意思爬墙了。』",
        "shy":     "『……嗯，谢谢。』",
        "nerd":    "『对。』他难得语气软下来。",
        "joker":   "『那我下次给你带早饭。』",
    },
)

L08 = clue(
    "snack", "light", "吃的",
    ["苏打饼", "巧克力", "肉干"],
    "『我包里常年有一包{truth}，饿的时候救命。』",
    ["『{truth}又吃完了，我明天得去买。』",
     "『包里没吃的了，我一般靠{truth}撑着来着？』",
     "『刚才在便利店又顺手拿了{truth}，家里还有半包。』"],
    react_bad={
        "gravity": "『……不是{wrong}，是{truth}。』她把包按了一下，没再说。",
        "bold":    "『{wrong}？我包里从来不装{wrong}，那玩意儿硌牙。』",
        "mom":     "『是{truth}呀。包里得有点吃的，你也一样。』",
        "angler":  "『{wrong}也行，反正饿不死。』",
        "shy":     "『……嗯。』",
        "nerd":    "『{truth}。』",
        "joker":   "『{wrong}我下次试试。』",
    },
    react_good={
        "gravity": "『……你记得。』她把包里那包递出来，『给你。』",
        "bold":    "『对，就靠这个续命。』他笑着拍包。",
        "mom":     "『记得就好。这孩子要好好吃饭。』",
        "angler":  "『你还真留意。』",
        "shy":     "『……嗯。』她把一包塞到我手里，很快收回手。",
        "nerd":    "『对。』他点头，从包里也掏出一样。",
        "joker":   "『知道我的库存，厉害。』",
    },
)

L10 = clue(
    "phone_app", "light", "生活",
    ["短视频", "购物", "小说"],
    "『我手机里最常打开的是{truth}，一刷就两小时没了。』",
    ["『我昨天又刷{truth}刷到凌晨两点。』",
     "『我最近又陷进{truth}里了，每天睡前说看一眼，然后就看到三点。』",
     "『手机提示我{truth}这周用了十九个小时。』"],
    react_bad={
        "gravity": "『……是{truth}，不是{wrong}。』她笑了一下，『你就是随口一问，我知道。』",
        "bold":    "『{wrong}？我哪来的时间看{wrong}。』",
        "mom":     "『是{truth}啦。少看点手机，眼睛要坏的。』",
        "angler":  "『都不看。我最近很自律。』他开了个玩笑。",
        "shy":     "『……嗯。』",
        "nerd":    "『{truth}。』",
        "joker":   "『{wrong}我试过，没什么意思。』",
    },
    react_good={
        "gravity": "『……你怎么什么都知道。』她的语气有点高兴，又有点慌。",
        "bold":    "『对！你也刷？』他来了精神。",
        "mom":     "『你们都这样。』她摇头，又笑。",
        "angler":  "『被你抓住了。』他摊手。",
        "shy":     "『……嗯。』",
        "nerd":    "『对。』他顿了顿，『我统计过时间。』",
        "joker":   "『合理。』",
    },
)

# ============================================================
# 中档 +4 / -5
# ============================================================

M01 = clue(
    "work_file", "mid", "工作",
    ["报表", "合同", "设计方案"],
    "『这周天天在改{truth}，改到最后自己都不认识了。』",
    ["『今天又是{truth}，我闭着眼都能背格式了。』",
     "『我这周一直在改{truth}，改得快吐了。』",
     "『刚下班，{truth}又推了一版回来。』"],
    react_bad={
        "gravity": "『……{wrong}？是{truth}。』她顿了很久，『算了，你本来也不知道我在做什么。』",
        "bold":    "『{wrong}？我改的是{wrong}？』他皱着眉想了半天，『不对，我改的是{truth}。』",
        "mom":     "『是{truth}啦。你听听，这孩子多累。』",
        "angler":  "『{wrong}也改过，都差不多。』",
        "shy":     "『……嗯，差不多。』",
        "nerd":    "『{truth}。』他清楚地纠正。",
        "joker":   "『{wrong}？那更惨。』",
    },
    react_good={
        "gravity": "『……你还记得我说的是什么。』她声音低下去，『我以为没人会听这些。』",
        "bold":    "『对！』他往椅背上一靠，『总算有人知道我在忙什么了。』",
        "mom":     "『记得这么清楚。』她笑，『你这孩子心细。』",
        "angler":  "『哎，你还真记着。』",
        "shy":     "『……嗯。』",
        "nerd":    "『对。』他点头，『这是我这个月第十一次改。』",
        "joker":   "『知道的还挺多。』",
    },
)

M02 = clue(
    "off_work", "mid", "工作",
    ["七点", "九点", "通宵"],
    "『我们那天得{truth}才能走，基本吃不上正常的饭。』",
    ["『今天又拖到{truth}，午饭都省了。』",
     "『我昨天又是{truth}才回去的。』",
     "『这周大概只有一天是{truth}下班的。』"],
    react_bad={
        "gravity": "『……不是{wrong}，是{truth}。』她笑了一下，『我也没有很委屈。』",
        "bold":    "『{wrong}？我要能{wrong}下班我还来这儿干嘛。』",
        "mom":     "『是{truth}呀。这哪是上班。』",
        "angler":  "『{wrong}也算早了。』",
        "shy":     "『……嗯。』",
        "nerd":    "『{truth}。』他重复了一遍，像在核对。",
        "joker":   "『{wrong}？那你过的是我的日子。』",
    },
    react_good={
        "gravity": "『……你连我几点下班都记得。』她把包带攥紧了一点。",
        "bold":    "『对，就这个点。』他拍了下桌子，『惨不惨。』",
        "mom":     "『记得好。』她点头，『你也要早点睡。』",
        "angler":  "『你还真算得清。』",
        "shy":     "『……嗯，谢谢你还记着。』",
        "nerd":    "『对。』",
        "joker":   "『精准。』",
    },
)

M04 = clue(
    "pet_type", "mid", "生活",
    ["猫", "狗", "仓鼠"],
    "『我养了只{truth}，天天咬我的数据线。』",
    ["『我家那只{truth}今天又把我充电线咬断了。』",
     "『我家那只{truth}又在闹。』",
     "『昨天半夜{truth}踩我脸上，把我踩醒了。』"],
    react_bad={
        "gravity": "『……是{truth}，不是{wrong}。』她把手机收起来，没翻相册。",
        "bold":    "『{wrong}？我家那只是{wrong}？你听我说过吗。』",
        "mom":     "『是{truth}啦。我天天跟你说它的。』",
        "angler":  "『{wrong}也可爱。』",
        "shy":     "『……嗯。』",
        "nerd":    "『{truth}。』",
        "joker":   "『{wrong}？那不得把我家拆了。』",
    },
    react_good={
        "gravity": "『……你还记得它。』她终于把手机翻出来，『给你看。』——一张糊掉的照片。",
        "bold":    "『对！』他直接翻相册，『看看，凶不凶。』",
        "mom":     "『记得。』她笑着翻照片，『这孩子长胖了。』",
        "angler":  "『你记性不错。』",
        "shy":     "『……嗯。』她翻出一张，又很快收回。",
        "nerd":    "『对。』",
        "joker":   "『所以你连我家的都认识。』",
    },
)

M05 = clue(
    "dream_place", "mid", "人生",
    ["海边", "雪山", "有樱花的地方"],
    "『我这辈子最想去{truth}，一直没去成。』",
    ["『我在看{truth}的机票了，就看一眼。』",
     "『我最近又在看{truth}的攻略……说了很多年了。』",
     "『等这一季结束，我说不定真能去{truth}一趟。』"],
    react_bad={
        "gravity": "『……{wrong}？是{truth}。』她低头看手机，『说了也去不成。』",
        "bold":    "『{wrong}？我想去的是{wrong}吗，我记得不是。』",
        "mom":     "『是{truth}呀。这孩子说了好多次了。』",
        "angler":  "『{wrong}也挺好。』",
        "shy":     "『……嗯，哪儿都行。』",
        "nerd":    "『{truth}。』",
        "joker":   "『{wrong}也行，反正我都去不了。』",
    },
    react_good={
        "gravity": "『……你还记得。』她抬起头，『我一直没跟别人说过这个。』",
        "bold":    "『对，去那儿。』他摊手，『攒钱呢。』",
        "mom":     "『记得清清楚楚。』她笑着摆手。",
        "angler":  "『你还真上心。』",
        "shy":     "『……嗯。』她笑了一下，很快收住。",
        "nerd":    "『对。』",
        "joker":   "『那你要不要一起去。』他说完自己先笑。",
    },
)

M08 = clue(
    "family_pressure", "mid", "家庭",
    ["什么时候结婚", "攒了多少钱", "要不要回老家"],
    "『我妈天天问我{truth}，我都不敢接电话了。』",
    ["『我妈又来问{truth}，我说快了快了。』",
     "『今天又被我妈问了{truth}。』",
     "『电话一接通，还是那句{truth}。』"],
    react_bad={
        "gravity": "『……不是{wrong}，是{truth}。』她笑了一下，『你听着烦，我也没想让你分担。』",
        "bold":    "『{wrong}？我妈问的是{wrong}？我怎么记得是{truth}。』",
        "mom":     "『是{truth}呀。当妈的都这样。』",
        "angler":  "『都问吧。反正我都答不上来。』",
        "shy":     "『……嗯。』",
        "nerd":    "『{truth}。』",
        "joker":   "『都问。全部。』",
    },
    react_good={
        "gravity": "『……你记得。』她低下头，『我其实不太想跟别人讲这个。』",
        "bold":    "『对。』他叹气，『我妈也是。』",
        "mom":     "『记得就好。』她摇头，又笑了一下。",
        "angler":  "『你还挺会听。』",
        "shy":     "『……嗯。』",
        "nerd":    "『对。』",
        "joker":   "『你猜我妈还问我什么。』",
    },
)

M09 = clue(
    "money_habit", "mid", "钱",
    ["吃", "看演出", "买衣服"],
    "『我花钱最舍得在{truth}上，别的地方一概抠。』",
    ["『我这个月又在{truth}上花超了。』",
     "『我又超支了，这个月的钱全填在{truth}上。』",
     "『工资一到手，先划掉{truth}那一份，剩下的才敢花。』"],
    react_bad={
        "gravity": "『……是{truth}，不是{wrong}。』她笑了一下，『这你都不记得。』",
        "bold":    "『{wrong}？我在{wrong}上一分钱都不舍得花。』",
        "mom":     "『是{truth}啦。这孩子舍得。』",
        "angler":  "『{wrong}吧，差不多。』",
        "shy":     "『……嗯，反正都花了。』",
        "nerd":    "『{truth}。』",
        "joker":   "『{wrong}也行，反正都超出来了。』",
    },
    react_good={
        "gravity": "『……你连我钱花在哪都记着。』她有点不好意思。",
        "bold":    "『对！』他大笑，『你看我像不像有钱人。』",
        "mom":     "『记得挺清楚。』她笑着埋怨，『省着点。』",
        "angler":  "『被你看穿了。』",
        "shy":     "『……嗯。』",
        "nerd":    "『对。』",
        "joker":   "『所以我为什么穷，你懂了吧。』",
    },
)

M10 = clue(
    "commuter_route", "mid", "生活",
    ["换两趟地铁", "坐公交转地铁", "骑车加地铁"],
    "『我每次过来都要{truth}，一趟快一个小时。』",
    ["『今天{truth}过来，差点没赶上开场。』",
     "『我每次来的路上都得{truth}，折腾一趟。』",
     "『回去还是{truth}，到家大概十一点。』"],
    react_bad={
        "gravity": "『……是{truth}，不是{wrong}。』她顿了一下，『我以为你会问一句我路上累不累。』",
        "bold":    "『{wrong}？我绕那一大圈干嘛。』",
        "mom":     "『是{truth}呀。跑这么远来，也不嫌累。』",
        "angler":  "『{wrong}也试过，差不多。』",
        "shy":     "『……嗯。』",
        "nerd":    "『{truth}。』",
        "joker":   "『{wrong}？那得再早起半小时。』",
    },
    react_good={
        "gravity": "『……你连我怎么来的都记得。』她声音软下来，『其实挺累的。』",
        "bold":    "『对，就那条线。』他笑，『你也在那条线上？』",
        "mom":     "『记得这么清楚。』她叹口气，『不容易啊。』",
        "angler":  "『你还挺把她当回事。』",
        "shy":     "『……嗯，谢谢你还记着。』",
        "nerd":    "『对。』",
        "joker":   "『那你以后给我指路。』",
    },
)

# ============================================================
# 重档 +6 / -8
# ============================================================

H02 = clue(
    "first_visit", "heavy", "她为什么在这里",
    ["朋友硬拉着来的", "那天刚好失恋", "下班路上经过"],
    "『我第一次来看你们，是{truth}。』",
    ["『想起我第一次来看你们，{truth}，现在想想挺傻的。』",
     "『第一次进场那晚我是怎么来的来着——{truth}，我记着呢。』",
     "『要是那天不是{truth}，我大概一辈子都不会走进这种场子。』"],
    react_bad={
        "gravity": "『……{wrong}？是{truth}。』她低下头，『我以为你会记得这种事的。』",
        "bold":    "『{wrong}？那是{wrong}吗。』他摆了摆手，『算了，不重要。』",
        "mom":     "『是{truth}啦。那会儿我还挺难过的。』",
        "angler":  "『{wrong}也有可能。』他打了个哈哈。",
        "shy":     "『……嗯，差不多吧。』",
        "nerd":    "『{truth}。』他说得很轻，『那天我记得是几号。』",
        "joker":   "『{wrong}也行。反正那时候挺惨的。』",
    },
    react_good={
        "gravity": "『……你还记得。』她停了很久，『我只跟你说过一次。』",
        "bold":    "『对！』他很高兴，『你记性真好。』",
        "mom":     "『记得。』她点了下头，『那天我挺难过的。』",
        "angler":  "『哎，你还真记着。』他有点意外。",
        "shy":     "『……嗯。』她小声说，『谢谢你还记得。』",
        "nerd":    "『对。』他看着我，『那天我很感动。』",
        "joker":   "『所以你连这个都记着。』他笑得有点安静。",
    },
)

H05 = clue(
    "spare_thing", "heavy", "她自己",
    ["在画东西", "在写东西", "在学琴"],
    "『我要是没在追团，我大概{truth}，很久没碰了。』",
    ["『我把{truth}的东西翻出来了，想重新开始试试。』",
     "『我最近想把以前那个爱好捡起来，{truth}。』",
     "『以前我还{truth}来着，现在手都生了。』"],
    react_bad={
        "gravity": "『……{wrong}？是{truth}。』她把话咽回去，『我就随口一提。』",
        "bold":    "『{wrong}？我哪会{wrong}。』",
        "mom":     "『是{truth}啦。这孩子以前可认真了。』",
        "angler":  "『{wrong}也不错。』",
        "shy":     "『……嗯。』",
        "nerd":    "『{truth}。』",
        "joker":   "『{wrong}我也试过，三天热度。』",
    },
    react_good={
        "gravity": "『……你记得。』她眼睛亮了，又赶紧低头，『那件事我没有跟别人说过。』",
        "bold":    "『对！』他大笑，『我打算重新开始了。』",
        "mom":     "『记得。』她笑着点头，『你去试试吧。』",
        "angler":  "『你还真记着。』",
        "shy":     "『……嗯，谢谢你记得。』",
        "nerd":    "『对。』",
        "joker":   "『那你以后就是我第一个读者。』",
    },
)

H07 = clue(
    "alone_reason", "heavy", "她为什么在这里",
    ["下了班没地方去", "家里太安静", "想找件能坚持的事"],
    "『我这么常来，是因为{truth}。』",
    ["『我最近老想起，我这么常来是因为{truth}。』",
     "『我知道我来得有点多。其实是因为{truth}。』",
     "『说到底还是{truth}，不然我不会一周跑三趟。』"],
    react_bad={
        "gravity": "『……不是{wrong}。是{truth}。』她笑了一下，『我大概就不该说这个。』",
        "bold":    "『{wrong}？那是我说的吗。』他挠了挠头，『算了。』",
        "mom":     "『是{truth}呀。这孩子一个人待着闷。』",
        "angler":  "『都有一点吧。』",
        "shy":     "『……嗯，差不多。』",
        "nerd":    "『{truth}。』",
        "joker":   "『{wrong}，也行。反正都挺惨的。』",
    },
    react_good={
        "gravity": "『……你记得。』她停了很久，『那是我最难开口的一句。』",
        "bold":    "『对。』他少见地认真起来，『下班没地方去。』",
        "mom":     "『记得就好。』她轻叹，『你这孩子心细。』",
        "angler":  "『你还真听进去了。』他笑得有点不自然。",
        "shy":     "『……嗯。』她小声说，『被记住，挺好。』",
        "nerd":    "『对。』他点了点头，没再说别的。",
        "joker":   "『对。』他难得没开玩笑。",
    },
)

H10 = clue(
    "what_keeps", "heavy", "她为什么在这里",
    ["你在台上那个样子", "你说过的一句话", "这里没人认识我"],
    "『我还会一直来，是因为{truth}。』",
    ["『我想了很久，我还会一直来是因为{truth}。』",
     "『这一季结束你还来吗。我会来的，因为{truth}。』",
     "『说到底就一个理由，{truth}。别的都是顺带的。』"],
    react_bad={
        "gravity": "『……{wrong}？是{truth}。』她把手收回去，『没关系，我大概说得太认真了。』",
        "bold":    "『{wrong}？嗯……也许吧。』他把话岔开，『反正我还会来。』",
        "mom":     "『是{truth}呀。你听听这孩子。』",
        "angler":  "『都算吧。』",
        "shy":     "『……嗯。』她低下头。",
        "nerd":    "『{truth}。』他慢慢地说。",
        "joker":   "『{wrong}，也行。』",
    },
    react_good={
        "gravity": "『……你记得。』她的眼睛红了，『那我说得值。』",
        "bold":    "『对！』他拍桌子，『你也记得我。』",
        "mom":     "『记得。』她笑着摆手，眼睛有点湿。",
        "angler":  "『你这人真是。』他转头看别处。",
        "shy":     "『……谢谢。』她声音很轻。",
        "nerd":    "『对。』",
        "joker":   "『记住这句，我以后要验收的。』",
    },
)

H11 = clue(
    "prev_group", "heavy", "她为什么在这里",
    ["她们散了", "我搬了家", "我换工作了"],
    "『我以前来看过别人的 live，后来{truth}，就没再去过了。』",
    ["『我以前也追过别的团，后来{truth}，就没再去了。』",
     "『我上个团后来{truth}，就没再去过了。』",
     "『上一个团散场的方式是{truth}，我到现在还记得那天。』"],
    react_bad={
        "gravity": "『……是{truth}，不是{wrong}。』她把杯子推回中间，『那件事我没跟多少人说过。』",
        "bold":    "『{wrong}？我记得不是这样。』他摊手，『算了。』",
        "mom":     "『是{truth}呀。那时候挺可惜的。』",
        "angler":  "『大概吧。』",
        "shy":     "『……嗯。』",
        "nerd":    "『{truth}。』",
        "joker":   "『{wrong}，那我记错了。』",
    },
    react_good={
        "gravity": "『……你记得。』她盯着桌沿，『所以我才这么怕这一季结束。』",
        "bold":    "『对。』他摸摸后颈，『也就那么回事。』",
        "mom":     "『记得。』她点头，『那孩子不容易。』",
        "angler":  "『你还真听我讲这些。』",
        "shy":     "『……嗯。』她小声应了一句。",
        "nerd":    "『对。』他顿了顿，『那天我哭得很丢人。』",
        "joker":   "『记得这么清楚。』",
    },
)

CLUES = [L01, L02, L03, L04, L05, L06, L07, L08, L10,
         M01, M02, M04, M05, M08, M09, M10,
         H02, H05, H07, H10, H11]

# ============================================================
# 修正层（2026-11-14）：上面 21 条的 ask / react_bad.gravity 有漏写 {truth}/{wrong}，
# 直接按 key 覆盖，不再零散改字符串。断言在 clue() 里已经关掉，这里统一补。
# ============================================================
from _ota_memory_fix import FIX_ASK, FIX_G
from _ota_memory_react import REACT_FIX
from _ota_memory_say import SAY_FIX

for _c in CLUES:
    _k = _c["key"]
    # 「她说」这一拍的台词改写成闲聊口吻（2026-11-14 用户定）
    if _k in SAY_FIX:
        _c["say"] = SAY_FIX[_k]
    if _k in FIX_ASK:
        for _i, _txt in FIX_ASK[_k].items():
            _c["ask"][_i] = _txt
    if _k in FIX_G:
        _c["react_bad"]["gravity"] = FIX_G[_k]
    # 原型台词覆盖（2026-11-14：钓师->DD / 妈妈粉删除 / 考据文青->长发男文青）
    for _arch, _table in REACT_FIX.items():
        if _k in _table:
            _good, _bad = _table[_k]
            _c["react_good"][_arch] = _good
            _c["react_bad"][_arch] = _bad

# 修正后再做一次总校验（这才是真正的闸门）
for _c in CLUES:
    _k = _c["key"]
    assert "{truth}" in _c["say"], (_k, "say 缺 {truth}")
    for _i, _a in enumerate(_c["ask"]):
        assert "{truth}" in _a, (_k, "ask[%d] 缺 {truth}" % _i, _a)
    assert "{wrong}" in _c["react_bad"]["gravity"], (_k, "gravity 缺 {wrong}")
    assert "{truth}" in _c["react_bad"]["gravity"], (_k, "gravity 缺 {truth}")
    # 七原型每一条答错反应都必须给出真值，否则玩家不知道正确答案
    for _arch, _txt in _c["react_bad"].items():
        assert "{truth}" in _txt, (_k, "react_bad[%s] 缺 {truth}" % _arch, _txt)

# 重型线索：三种情况各一句完整台词（第一拍直接用这句，不再套模板）
from _ota_memory_sayfull import SAY_FULL
for _c in CLUES:
    _k = _c["key"]
    if _k not in SAY_FULL:
        continue
    _full = SAY_FULL[_k]
    assert set(_full) == set(_c["set"]), (_k, "say_full 与 set 不一致", sorted(_full), _c["set"])
    _c["say_full"] = _full
    # say 保留模板版（带 {truth}），供不能走 say_full 的兜底路径/文档使用
assert_sayfull = all(
    ("say_full" in _c) == (_c["level"] == "heavy") for _c in CLUES
)
assert assert_sayfull, "重型必须全有 say_full，非重型必须没有"

doc = {
    "_meta": {
        "category": "OTA 记忆回考线索池",
        "version": 2,
        "design_note": (
            "考核机制（2026-11-14 定）：第一次她随口说出一个三选一的细节（值在本局锁定）；"
            "后面某场特典她用一句自然问法再提；玩家只回三个同类值，答对加分、答错直接扣分。"
            "没有缓冲选项、没有档案本、不出现『你记得吗』。"
            "答错反应按 OTA 原型写（重力系会替你找台阶、自来熟当玩笑、社恐温柔安静收回去、DD 先装忘、长发男文青说得很少、整活型打岔）。"
            "同一局内真值永远锁定，每次重开重新掷。"
        ),
        "points": {"light": "+2/-3", "mid": "+4/-5", "heavy": "+6/-8"},
        "freq": "每场特典会约 30% 概率刷一次回考，一季大约 2~3 次。",
        "placeholders": {"{truth}": "本局真值", "{wrong}": "玩家选的错项"},
        "archetypes": {
            "gravity": "重力系", "bold": "自来熟", "mom": "社恐温柔",
            "angler": "DD", "shy": "社恐（低能量）", "nerd": "长发男文青", "joker": "整活型",
        },
        "pov_note": "台词在『』内允许出现『你』（她在对我说话）；叙事层不出现第二人称。",
        # 线索登记表：原先挂在个人线 _meta.memory_key 上，个人线砍掉后移到这里
        "memory_key": {k: {"kind": "fact", "label": CLUE_LABEL[k]} for k in CLUE_LABEL},
    },
    "clues": CLUES,
}

# 每条线索都必须在登记表里
for _c in CLUES:
    assert _c["key"] in CLUE_LABEL, ("未登记", _c["key"])
assert len(CLUE_LABEL) == len(CLUES), ("登记表与线索数不一致", len(CLUE_LABEL), len(CLUES))

from neutralize_pronouns import walk as _neutralize  # noqa: E402

with open(OUT, "w", encoding="utf-8") as f:
    json.dump(_neutralize(doc), f, ensure_ascii=False, indent=2)
    f.write("\n")

from collections import Counter
c = Counter(x["level"] for x in CLUES)
print("WROTE", os.path.basename(OUT))
print("  total:", len(CLUES), "| light/mid/heavy:", c["light"], c["mid"], c["heavy"])
print("  keys:", ", ".join(x["key"] for x in CLUES))
