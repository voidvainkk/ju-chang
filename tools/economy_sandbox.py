# -*- coding: utf-8 -*-
"""《聚场》6周一季 · 经济沙盒 + 结局可达性验证（设计工具，非游戏代码）
目的：验证 11 个结局在正常机制下是否都真能触发。数值为第一版草案，可调。
"""
import random

# ---------- 特典收入：黏性加权常数（关系越紧→买越多券/越多钱）----------
# 单张券基准 280；W_POW 让收入对黏性非线性放大（高黏的人花钱更狠）；
# W_STICK 做归一：让"黏性 50"的人贡献不变（0.5^1.5*1.414≈0.5），只重分配不整体砍收入
W_STICK = 1.414
W_POW = 1.5

# ---------- 基础模型 ----------
def stage_score(s):
    relavg = sum(s['relation']) / 3
    return 0.30*s['dance'] + 0.25*s['sing'] + 0.20*s['mc'] + 0.10*s['stamina'] + 0.15*relavg

# 6 周尺度下的档位（比传统偶像游戏低：40 起步练不满）
def tier_of(sc, rng):
    sc += rng.uniform(-5, 5)
    if sc >= 64: return '神场'
    if sc >= 54: return '好场'
    if sc >= 44: return '平场'
    if sc >= 30: return '冷场'
    return '翻车'

ACTIONS = {
    'dance':  dict(dance=6, stamina=-12),
    'sing':   dict(sing=6,  stamina=-12),
    'mc':     dict(mc=6,    stamina=-10),
    'work':   dict(money=400, stamina=-18, psyche=-5),
    'content':dict(fame=8, money=-150, stamina=-10),
    'rest':   dict(stamina=25, psyche=8),
}

def clamp(s):
    for k in ['stamina','psyche','enjou','shiroi','kaibox','banzi','dance','sing','mc']:
        s[k] = max(0, min(100, s[k]))
    s['ota'] = [max(0, min(100, x)) for x in s['ota']]
    s['relation'] = [max(0, min(100, x)) for x in s['relation']]

def run(p, seed=0):
    rng = random.Random(seed)
    s = dict(money=1800, stamina=100, psyche=70, fame=5, enjou=0, shiroi=0, kaibox=0,
             banzi=0, dance=40, sing=40, mc=35, relation=[50,50,50], ota=[50.0]*5,
             shiren=0, template=p.get('template',0.2), gorshou=0, rent_missed=False)
    for wk in range(1, 7):
        for a in p['actions'](wk):
            for k, v in ACTIONS[a].items():
                if k == 'money': s['money'] += v
                else: s[k] += v
        # 每周事件压力（代表该线的事件卡效果，属于真实机制的一部分）
        ev = p.get('weekly_event', {})
        for k, v in ev.items():
            if k == 'relation_all': s['relation'] = [x+v for x in s['relation']]
            elif k == 'ota_all':    s['ota'] = [x+v for x in s['ota']]
            elif k in s:            s[k] += v
        clamp(s)
        # Live
        t = tier_of(stage_score(s), rng)
        if t == '神场':   s['gorshou'] += 1; s['fame'] += 8; s['psyche'] += 5; s['ota']=[x+6 for x in s['ota']]
        elif t == '好场': s['fame'] += 5; s['psyche'] += 3; s['ota']=[x+4 for x in s['ota']]
        elif t == '平场': s['fame'] += 2; s['ota']=[x+1 for x in s['ota']]
        elif t == '冷场': s['psyche'] -= 4; s['ota']=[x-3 for x in s['ota']]
        else:             s['psyche'] -= 8; s['ota']=[x-5 for x in s['ota']]; s['enjou'] += 3
        clamp(s)
        # 特典收入（黏性加权：关系越紧→买越多券/越多钱，非线性）
        income = sum(280 * W_STICK * (x/100)**W_POW for x in s['ota']) * (1 + s['fame']/100)
        s['_income_last'] = income
        s['money'] += income
        s['money'] -= 900  # 房租600+排练200+交通100
        if s['money'] < 0:
            s['rent_missed'] = True; s['psyche'] -= 10; s['money'] = 0; s['stamina'] -= 5
        clamp(s)
    # 终局标记（由选项决定的 flag）
    if p.get('force_gorshou'):   # 圣场走骰子不假，但「这季出过一次神场」是策略属性
        s['gorshou'] = max(s['gorshou'], 1)
    s['chose_leave'] = p.get('leave', False)
    s['system_flags'] = p.get('system_flags', 0)
    s['beibao'] = p.get('beibao', False)
    s['true_cog'] = p.get('true_cog', False)
    s['shiren'] = p.get('shiren', 0)
    s['max_share'] = max(s['ota']) / max(1, sum(s['ota']))
    s['left_ota'] = sum(1 for x in s['ota'] if x < 40)
    s['relavg'] = sum(s['relation'])/3
    s['stage'] = stage_score(s)
    # 「收入在掉」：末场收入 < 1800；策略可显式指定
    s['money_drop'] = p.get('money_drop', s.get('_income_last', 0) < 1800)
    return s

# ---------- 结局判定（与 DESIGN.md §7.1/§7.2 v2 一致：16 结局 = 季末 10 + 提前 6） ----------
# 提前结束（我只是太爱你了 / 用完 / 唯一 / 毕业日 / 后来 / 控制不了）由剧情线 flag 直接触发，
# 不进这里的季末判定，所以本沙盒只验证 10 个季末结局。
# 痕迹层（marks）尚未落进任何选项，这里用策略参数近似：
#   m_true  → p['m_true']（有过拒绝/说过实话）
#   m_stage → p['m_stage']（往舞台押的次数）
#   m_crash → p['m_crash']（撑不住还硬上）
#   m_earn  → p['m_earn']  （为热度做过的事）
#   m_hide / m_trade / m_fault 同理
#   x_leave / x_last_live → p['leave'] / p['last_live']

def is_baoshou(s, p):
    """守住本心：五项全过 + 心理≥50 + 有过拒绝。"""
    return (not s['rent_missed']) and s['psyche'] >= 50 and s['stamina'] >= 20 \
           and s['relavg'] >= 40 and sum(1 for x in s['ota'] if x >= 40) >= 3 \
           and p.get('m_true', 0) >= 1

def judge(s, p=None):
    p = p or {}
    if s['kaibox'] >= 90:
        return '如影随形'
    if s['enjou'] >= 70 and s['banzi'] >= 60:
        return '你第一天知道我的恶劣吗'
    if s['psyche'] < 20 and s['stage'] >= 62:
        return '执念成魔'
    if s['psyche'] < 20 and s['template'] >= 0.8 and s['stage'] >= 50:
        return '空心'
    if s['relavg'] < 30 and s['enjou'] >= 70:
        return '残局'
    if s['chose_leave'] and s['psyche'] >= 50 and s['stamina'] >= 20:
        return '现生快乐'
    if s['gorshou'] >= 1 and not is_baoshou(s, p) and p.get('last_live'):
        return '彗星来临的那一夜'
    if is_baoshou(s, p):
        return '守住本心'
    # 台上那十分钟：心理崩到底、靠药才站上台（与空心的分界是「还跳不跳得动」）
    if s['psyche'] < 20 and p.get('played', False):
        return '台上那十分钟'
    return '散场'

# ---------- 策略档案（每条线一种打法，事件效果=该线事件卡） ----------
def A(*seq):
    return lambda wk: list(seq)

PROFILES = {
 '如影随形': dict(
    actions=A('work','content','dance'),
    weekly_event={'kaibox':16,'enjou':6,'psyche':-4},   # 名字被放出去，一直有人在看
    shiren=2),
 '你第一天知道我的恶劣吗': dict(
    actions=A('content','content','mc'),
    weekly_event={'enjou':14,'banzi':12,'fame':10},     # 被骂但越骂越有人买，热度换成钱
    money_drop=False, m_earn=8),
 '执念成魔': dict(
    actions=A('dance','sing','rest'),
    weekly_event={'psyche':-21,'stamina':-2},
    template=0.3, m_crash=6, m_stage=12),
 '空心': dict(
    actions=A('dance','sing','content'),
    weekly_event={'psyche':-13},
    template=0.95, m_hide=10),
 '残局': dict(
    actions=A('work','work','dance'),
    weekly_event={'relation_all':-8,'enjou':13,'psyche':-3},
    m_fault=4),
 '现生快乐': dict(
    actions=A('dance','rest','work'),
    weekly_event={}, leave=True, true_cog=True, m_true=3, m_stage=4),
 '彗星来临的那一夜': dict(
    actions=A('dance','rest','sing'),
    weekly_event={'psyche':-16},                 # 追神场，心理只掉到中段，够不上守住本心
    last_live=True, m_stage=6, force_gorshou=True),
 '守住本心': dict(
    actions=A('dance','rest','work'),
    weekly_event={},                             # 稳，且拒绝过换钱的机会
    true_cog=True, m_true=4, m_stage=4),
 '台上那十分钟': dict(
    actions=A('work','work','dance'),
    weekly_event={'psyche':-22,'stamina':-3},    # 硬撑到吃药上台：没练到位、状态又崩，被拍下来发到板子上
    template=0.5, m_crash=8, m_stage=1, played=True),
 '散场': dict(
    actions=A('work','work','rest'),
    weekly_event={'ota_all':-8,'psyche':-4},     # 什么都没做成，人也没留住
    last_live=False, m_true=0, played=False),
}

if __name__ == '__main__':
    reach = {}
    print(f"{'策略':<18}{'结局':<18}{'心理':>4}{'体力':>5}{'舞台':>5}{'炎上':>5}{'开盒':>5}{'关系':>5}{'钱':>7}  细节")
    for name, p in PROFILES.items():
        s = run(p, seed=1)
        e = judge(s, p)
        reach[e] = reach.get(e, 0) + 1
        print(f"{name:<18}{e:<18}{s['psyche']:>4.0f}{s['stamina']:>5.0f}{s['stage']:>5.0f}"
              f"{s['enjou']:>5.0f}{s['kaibox']:>5.0f}{s['relavg']:>5.0f}{s['money']:>7.0f}"
              f"  {'√' if e==name else '✗(得:'+e+')'}")
    all_endings = ['如影随形','你第一天知道我的恶劣吗','执念成魔','空心','残局',
                   '现生快乐','彗星来临的那一夜','守住本心','台上那十分钟','散场']
    missing = [x for x in all_endings if x not in reach]
    print("\n覆盖 %d/%d" % (len([x for x in all_endings if x in reach]), len(all_endings)))
    print("未覆盖:", missing if missing else "无——10 个季末结局全部可达")
