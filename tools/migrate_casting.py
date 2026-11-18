# -*- coding: utf-8 -*-
"""把写死 OTA 真名的卡改成"选角槽 casting slot"结构。
选角槽约定（写进各卡库 _meta.casting_schema）：
  card.casting = [ {slot, select:{gender?/fan_type?/archetype?/min_stickiness?/private_contact?}, allow_hatch} ]
  - narrative/label/desc 用 {{slot}} 显示名字，{{slot.ta}} 显示他/她
  - effect 键 "@<slot>" = 投给该槽位选中 OTA 的黏性增减；ota_all 仍是全体
  - 若没有符合条件的 OTA 且 allow_hatch=true，按原型孵化一个新人填进去
"""
import json, os

base = r'C:\Users\kk\Documents\deepseek-harness\default-workspace\聚场\data\cards'

NEW = {}  # (file, cid) -> {fields...}

# ---------- ota.json ----------
NEW[('ota.json','ota_regular_shift')] = {
 "gate": "任一 OTA 黏性 ≥ 70",
 "casting": [{"slot":"spender","select":{"archetype":"自来熟","min_stickiness":70},"allow_hatch":True}],
 "narrative": "{{spender}}又来了，这次买了八张券，说要聊到我下班。{{spender.ta}}把券一张一张码在桌上，像在数我还剩多少时间。我盯着那叠券，脑子里先算了一笔账：八张，六百四，这个月房租就够了。想到这儿我自己都愣了一下——什么时候起，我看人先看的是这个。最后{{spender.ta}}顿了顿，问：『你一个人住吗？』",
}
NEW[('ota.json','ota_gachikoi')] = {
 "gate": "任一女友粉 OTA 黏性 ≥ 80 且 私联人数 = 0",
 "casting": [{"slot":"devotee","select":{"fan_type":"女友粉","min_stickiness":80},"allow_hatch":True}],
 "narrative": "{{devotee}}追了半年，特典快结束时攥着券没松手。『我不是把你当偶像，我是真的喜欢你……你能不能，给我个微信号？』{{devotee.ta}}声音压得很低，怕旁边人听见。staff 就在两米外收桌子，随时会回过头。我心跳一下快起来——可奇怪的是，第一个冒出来的念头不是怕，是：给了又怎样，反正没人看见。",
}
NEW[('ota.json','ota_shukudai')] = {
 "gate": "任一 OTA 黏性 ≥ 60",
 "casting": [{"slot":"otaku","select":{"archetype":"考据文青","min_stickiness":60},"allow_hatch":True}],
 "narrative": "{{otaku}}递来宿题切，题目是『用三个词形容我』。纸很大，要写满，还得画个小图。后面还排着七个人，每个人都在看表。我握着笔，手心有点汗：写慢了对不起后面的人，写糊了对不起{{otaku.ta}}。这种时候我总觉得自己被掰成了好几份，哪一份都不够用。",
}
NEW[('ota.json','ota_dd')] = {
 "gate": "任一 OTA 黏性 ≥ 40",
 "casting": [{"slot":"drifter","select":{"archetype":"钓师"},"allow_hatch":True}],
 "narrative": "{{drifter}}每个团都追，来找我时语气轻快得刺耳：『下个月我主推隔壁团了，今天是来告别的。』{{drifter.ta}}说着还晃了晃手里的别家周边。我脸上笑着，心里却像被什么东西轻轻抽空了一下——原来我这半年的『单推』，在{{drifter.ta}}那儿只是一个随时能换掉的选项。",
}
NEW[('ota.json','ota_denki')] = {
 "gate": "任一 OTA 黏性 ≥ 75 且 体力 < 60",
 "casting": [{"slot":"nightowl","select":{"archetype":"社恐温柔","min_stickiness":75},"allow_hatch":True}],
 "narrative": "深夜十二点，{{nightowl}}买了电切。屏幕里{{nightowl.ta}}背后是空荡荡的加班办公室：『就聊五分钟，听你说说话就行。』我明天六点还要起床排练，这个我知道。可看着{{nightowl.ta}}办公室里那盏孤零零的灯，我又觉得，好像也只有此刻，有人是真的需要我。",
}
NEW[('ota.json','ota_shashu')] = {
 "gate": "任一 OTA 黏性 ≥ 70 且 钱 < 1200",
 "casting": [{"slot":"overextended","select":{"fan_type":"妈妈粉","min_stickiness":70},"allow_hatch":True}],
 "narrative": "散场最后走的还是{{overextended}}。{{overextended.ta}}一边收拾东西一边说：「我最近换了工作，工资还没下来，不过这个月我可以多买几张，冲一冲你那个生日应援。」{{overextended.ta}}笑了笑，有点不好意思，「你别有压力啊。」我脑子里那笔账自己就跳出来了：{{overextended.ta}}手上这些券，刚好能补上我这个月的房租。我知道{{overextended.ta}}攒那点钱本来是为了别的事。",
}
# ota_buddy 双槽：男方当哥们 + 女友粉被伤
NEW[('ota.json','ota_buddy')] = {
 "gate": "任一男性 OTA 黏性 ≥ 60",
 "casting": [
   {"slot":"buddy","select":{"gender":"男","min_stickiness":60},"allow_hatch":True},
   {"slot":"hurt","select":{"fan_type":"女友粉"},"allow_hatch":True},
 ],
 "narrative": "特典会散了，{{buddy}}没走，靠着桌边跟我贫：「你这舞，昨天第三段是不是差点忘动作？」说着伸手就来拍我的脑袋，宿舍里那种闹法。我下意识一躲，接着就笑了——好久没人这么跟我说过话，不用营业，不用端着，就当我是个普通姑娘。可我一抬眼，看见{{hurt}}站在不远处，手里攥着两张没送出去的券。",
 "options": [
  {"id":"play_along","label":"玩闹回去，笑成一团","desc":"我抬手把他的手拨开，笑着回敬了一句更难听的。那一瞬间我是真的松快。",
   "immediate":{"psyche":9,"@buddy":6,"@hurt":-6,"ota_all":-2},
   "delayed":[{"when":"下周","effect":{"enjou":8,"banzi":5,"@hurt":-4},"note":"板子上有人发帖：「她把跟男粉勾肩搭背当可爱，那我们凑的钱算什么？」底下几十条『心凉了』"}]},
  {"id":"step_back","label":"笑着退半步，把话头带回台上","desc":"我笑着往后让了让，说「行行行我错了」，顺手把话题拐回今天的歌单。端住了。",
   "immediate":{"psyche":-3,"@buddy":-2,"@hurt":3},"delayed":[]},
  {"id":"make_it_show","label":"把打闹变成给全场的玩笑","desc":"我干脆站起来对着还没散的人喊：「看见没，{{buddy}}说我跳错，下次让他上来跳！」全场笑。",
   "immediate":{"psyche":4,"ota_all":4,"@buddy":-3},"delayed":[]},
 ],
}

# ---------- private.json ----------
NEW[('private.json','priv_meetup')] = {
 "casting": [{"slot":"closeone","select":{"private_contact":True},"allow_hatch":False}],
 "narrative": "散场已经十一点，{{closeone}}说『附近有家面馆，要不…吃一口再走？』语气很自然，像早就想好了。我明天一早还要排练，可今天实在太累了，累到不想一个人回那个空房子。脸被夜风吹着，我犹豫了两秒——这两秒里，我其实已经答应了一半。",
}
NEW[('private.json','priv_gift')] = {
 "casting": [{"slot":"giver","select":{"private_contact":True,"min_stickiness":70},"allow_hatch":False}],
 "narrative": "{{giver}}特地从包里掏出一个盒子，说『路过看到的，觉得适合你』。我打开，是条不便宜的项链。{{giver.ta}}说得轻描淡写，可我知道这东西的钱，够我半个月房租。{{giver.ta}}看着我，眼里那种期待让我开不了口拒绝，又不敢真的收下。",
}
NEW[('private.json','priv_jealous')] = {
 "casting": [{"slot":"confronter","select":{"private_contact":True},"allow_hatch":False}],
 "narrative": "{{confronter}}在特典会上，忽然说：『昨天我看见另一个人从你后台那边出来。』{{confronter.ta}}笑着，眼神却没笑。我手里的笔停住——两个我都私联着，两条线，今天在这里撞上了。我知道，从这一刻起，这件事不再是我一个人能捂住的。",
}

# ---------- ambient.json ----------
NEW[('ambient.json','amb_fan_brings_friend')] = {
 "casting": [{"slot":"bringer","select":{"min_stickiness":60},"allow_hatch":True}],
 "narrative": "{{bringer}}走到特典桌前，身后还跟着个一脸局促的女生。「我室友，被我念叨了仨月，今天非要来看看。」{{bringer.ta}}把券递过来的时候，比我还高兴。",
 "effect": {"money":160,"ota_all":4,"psyche":3,"@bringer":4},
 "note": "多了两张券的钱：钱 +160，黏性 +4，心理 +3",
}

# ---------- positive.json ----------
NEW[('positive.json','pos_letter')] = {
 "casting": [{"slot":"letterwriter","select":{"min_stickiness":65},"allow_hatch":True}],
 "narrative": "散场时{{letterwriter}}塞给我一个对折的信封，说回去再看。拆开是密密麻麻三页字，写从第一次看我，到现在工作第一年。最后一句：「你别飘，也别塌，我们慢慢来。」",
}

# ---- 额外微调：选项里残留的"他/她"改中性或占位 ----
EXTRA_OPT = {
 ('ota.json','ota_gachikoi'): {
   "gentle_no": {"desc":"不给微信号，只把这句话留在她那儿"},
 },
 ('positive.json','pos_letter'): {
   "keep_it_close": {"_delayed0_note":"{{letterwriter.ta}}等了好久没等到回音，后来来得少了"},
 },
}

casting_schema = ("card.casting = [ {slot, select:{gender?/fan_type?/archetype?/min_stickiness?/private_contact?}, allow_hatch} ]；"
 "narrative/label/desc 用 {{slot}} 显示名字、{{slot.ta}} 显示他/她；effect 键 @<slot> = 投给该槽位选中 OTA 的黏性增减，"
 "ota_all 仍为全体；无符合条件者且 allow_hatch 时按原型孵化新人填入。")

def apply(fname):
    path = os.path.join(base, fname)
    d = json.load(open(path, encoding='utf-8'))
    # meta 记录 schema
    if fname in ('ota.json','private.json','ambient.json','positive.json'):
        d['_meta']['casting_schema'] = casting_schema
    for c in d['cards']:
        key = (fname, c['id'])
        if key in NEW:
            c.update(NEW[key])
        if key in EXTRA_OPT:
            for o in c['options']:
                patch = EXTRA_OPT[key].get(o['id'])
                if not patch: continue
                for k,v in patch.items():
                    if k == '_delayed0_note':
                        o['delayed'][0]['note'] = v
                    else:
                        o[k] = v
    json.dump(d, open(path,'w',encoding='utf-8'), ensure_ascii=False, indent=2)
    open(path,'a',encoding='utf-8').write('\n')
    print('rewrote', fname, 'cards=%d'%len(d['cards']))

for f in ['ota.json','private.json','ambient.json','positive.json']:
    apply(f)
print('DONE')
