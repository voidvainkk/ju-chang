# -*- coding: utf-8 -*-
"""跑局看分布。用法：python tools\\run_policies.py [局数]"""
import os, sys, collections

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "game"))
import engine as E
import policy as P


def main(n=100):
    w = E.load_world()
    for cls in (P.Policy, P.Greedy, P.Reckless, P.Flirty):
        pol = cls()
        dist = collections.Counter()
        agg = [0.0] * 6
        for seed in range(n):
            pol.rng.seed(seed)
            s, name, early = E.run_season(w, seed=seed, policy=pol)
            dist[name] += 1
            agg[0] += s["psyche"]; agg[1] += E.stage_score(s); agg[2] += s["money"]
            agg[3] += s["enjou"]; agg[4] += s["max_single"]; agg[5] += sum(o["stick"] for o in s["ota"]) / len(s["ota"])
        print("\n== %s (%d 局) ==" % (cls.__name__, n))
        for k, v in dist.most_common():
            print("   %-18s %3d  %5.1f%%" % (k, v, 100.0 * v / n))
        print("   均值: 心理 %.0f 舞台 %.1f 钱 %.0f 炎上 %.0f 最高单场 %.1f 均黏性 %.0f"
              % tuple(x / n for x in agg))


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 100)
