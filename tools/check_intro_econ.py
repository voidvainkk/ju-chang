# -*- coding: utf-8 -*-
"""开场三选一的经济重跑：初始值按 data/intro.json 覆盖后，12 个季末结局是否仍全部可达。
不改 economy_sandbox.py 的 judge/PROFILES，只把自己的主循环按 sandbox 的逻辑复刻一遍，
把起始状态换成 intro 的 base_state + 该选择的 delta。
"""
import json, os, random, sys
sys.path.insert(0, os.path.dirname(__file__))
import economy_sandbox as es

BASE = r"C:\Users\kk\Documents\deepseek-harness\default-workspace\聚场\data"
intro = json.load(open(os.path.join(BASE, "intro.json"), encoding="utf-8"))


def start_state(choice):
    """base_state 已经是『选完之后』的状态（序章结算：钱1700/心理66/人气12/舞45），
    所以这里只取 base_state，不再叠 choice 的 effect；choice.effect 是相对通用初值的增量，
    只用来核对 base_state 与它一致。"""
    b = intro["base_state"]
    return dict(money=b["money"], stamina=b["stamina"], psyche=b["psyche"], fame=b["fame"],
                dance=b["dance"], sing=b["sing"], mc=b["mc"],
                relation=list(b["relation"]), ota=list(b["ota"]))


def sim(p, seed, start):
    rng = random.Random(seed)
    s = dict(start)
    s.update(shiroi=0, kaibox=0, banzi=0, enjou=0,
             shiren=0, template=p.get('template', 0.2), gorshou=0, rent_missed=False)
    for wk in range(1, 7):
        for a in p['actions'](wk):
            for k, v in es.ACTIONS[a].items():
                if k == 'money':
                    s['money'] += v
                else:
                    s[k] += v
        ev = p.get('weekly_event', {})
        for k, v in ev.items():
            if k == 'relation_all':
                s['relation'] = [x + v for x in s['relation']]
            elif k == 'ota_all':
                s['ota'] = [x + v for x in s['ota']]
            elif k in s:
                s[k] += v
        es.clamp(s)
        t = es.tier_of(es.stage_score(s), rng)
        if t == '神场':
            s['gorshou'] += 1; s['fame'] += 8; s['psyche'] += 5
            s['ota'] = [x + 6 for x in s['ota']]
        elif t == '好场':
            s['fame'] += 5; s['psyche'] += 3; s['ota'] = [x + 4 for x in s['ota']]
        elif t == '平场':
            s['fame'] += 2; s['ota'] = [x + 1 for x in s['ota']]
        elif t == '冷场':
            s['psyche'] -= 4; s['ota'] = [x - 3 for x in s['ota']]
        else:
            s['psyche'] -= 8; s['ota'] = [x - 5 for x in s['ota']]; s['enjou'] += 3
        es.clamp(s)
        income = sum(280 * es.W_STICK * (x / 100) ** es.W_POW for x in s['ota']) * (1 + s['fame'] / 100)
        s['_income_last'] = income
        s['money'] += income
        s['money'] -= 900
        if s['money'] < 0:
            s['rent_missed'] = True; s['psyche'] -= 10; s['money'] = 0; s['stamina'] -= 5
        es.clamp(s)
    if p.get('force_gorshou'):
        s['gorshou'] = max(s['gorshou'], 1)
    s['chose_leave'] = p.get('leave', False)
    s['system_flags'] = p.get('system_flags', 0)
    s['beibao'] = p.get('beibao', False)
    s['true_cog'] = p.get('true_cog', False)
    s['shiren'] = p.get('shiren', 0)
    s['max_share'] = max(s['ota']) / max(1, sum(s['ota']))
    s['left_ota'] = sum(1 for x in s['ota'] if x < 40)
    s['relavg'] = sum(s['relation']) / 3
    s['stage'] = es.stage_score(s)
    s['money_drop'] = p.get('money_drop', s.get('_income_last', 0) < 1800)
    return s


def main():
    """两种跑法：
    A. 精确 —— 用 PROFILES 原样跑（每场心理掉多少、结果如何都写死在档案里）；
    B. 带宽 —— 把档案的心理消耗按 ±BW 浮动（模拟真实事件强度不确定），看结局的分布。
    """
    BW = [0.7, 1.0, 1.3]
    for c in intro["choices"]:
        start = start_state(c)
        print(f"\n=== 开场：{c['label']} ===")
        for name, p in es.PROFILES.items():
            # A 精确
            got0 = {}
            for seed in range(30):
                r = es.judge(sim(p, seed, start), p)
                got0[r] = got0.get(r, 0) + 1
            # B 带宽
            gotw = {}
            for k in BW:
                pw = dict(p)
                ev = dict(p.get("weekly_event") or {})
                if "psyche" in ev:
                    ev["psyche"] = round(ev["psyche"] * k)
                pw["weekly_event"] = ev
                for seed in range(10):
                    r = es.judge(sim(pw, seed, start), pw)
                    gotw[r] = gotw.get(r, 0) + 1
            ok = got0.get(name, 0)
            print(f"  精确 {'OK ' if ok == 30 else 'ERR'} {name:12s} {ok}/30"
                  + ("" if ok == 30 else f" 实际{got0}")
                  + f"  ｜带宽 {dict(sorted(gotw.items(), key=lambda x: -x[1]))}")


if __name__ == "__main__":
    main()
