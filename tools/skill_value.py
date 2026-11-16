# -*- coding: utf-8 -*-
"""舞/唱/live 练上去到底换了什么：跑三组对照（不练 / 练一点 / 练满），看差异。

用户 2026-11-14 问：「舞蹈歌唱提升之后有什么用」。
"""
import sys, os, statistics

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "game"))
import engine as E
import policy as P


class Fixed(P.Policy):
    """固定六天的动作，用来做对照。"""

    def __init__(self, acts, rng=None):
        P.Policy.__init__(self, rng)
        self.acts = acts

    def act(self, s, options=None):
        i = (s.get("week", 1) - 1) * 6 + s.get("_act_i", 0)
        s["_act_i"] = s.get("_act_i", 0) + 1
        return self.acts[i % len(self.acts)]


def run(acts, n=30):
    w = E.load_world()
    fame, tiers, money, stage, maxsingle = [], {}, [], [], []
    for seed in range(n):
        st, name, early = E.run_season(w, seed=seed, policy=Fixed(acts))
        fame.append(st["fame"])
        money.append(st["money"])
        stage.append(E.stage_score(st))
        maxsingle.append(st["max_single"])
        # 一季里有几场进了「神场/好场」
    return dict(fame=statistics.mean(fame), money=statistics.mean(money),
                stage=statistics.mean(stage), maxsingle=statistics.mean(maxsingle))


CASES = {
    "全躺（不练）": ["rest"] * 6,
    "只练舞（一晚）": ["dance"] + ["rest"] * 5,
    "练舞三晚": ["dance"] * 3 + ["rest"] * 3,
    "舞唱live 各一晚": ["dance", "sing", "mc"] + ["rest"] * 3,
    "全练（六晚都练）": ["dance", "sing", "mc", "dance", "sing", "mc"],
}
print("%-18s %8s %8s %8s %8s" % ("打法", "人气", "钱", "舞台分", "最高单场"))
for k, v in CASES.items():
    r = run(v)
    print("%-18s %8.1f %8.0f %8.1f %8.1f" % (k, r["fame"], r["money"], r["stage"], r["maxsingle"]))
