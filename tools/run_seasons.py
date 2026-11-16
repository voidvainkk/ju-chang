# -*- coding: utf-8 -*-
"""跑局：不同打法的自动玩家，跑 200 局看结局分布。
用法：python tools\run_seasons.py [局数]
"""
import os, sys, json, random, collections

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "game"))
import engine as E


def pick_best(s, card, options):
    """看 immediate 打分挑最优，模拟一个会算账的玩家。"""
    best, bi = -1e9, 0
    for i, o in enumerate(options):
        sc = 0.0
        for k, v in (o.get("immediate") or {}).items():
            if k.startswith("@") or k == "ota_all":
                sc += v * 1.2
            elif k == "relation_all":
                sc += v * 1.0
            elif k in ("enjou", "kaibox", "banzi", "shiroi"):
                sc -= v * 1.5
            elif k == "psyche":
                sc += v * 1.4
            elif k == "stamina":
                sc += v * 0.6
            elif k == "money":
                sc += v * 0.004
            else:
                sc += v * 0.8
        if sc > best:
            best, bi = sc, i
    return bi


def pick_worst(s, card, options):
    return 1 - (pick_best(s, card, options) or 0) if len(options) == 2 else len(options) - 1 - pick_best(s, card, options)


def pick_rand(s, card, options):
    return random.randrange(len(options))


POLICIES = {
    "算账型": pick_best,
    "瞎选型": pick_rand,
    "反向型": pick_worst,
}


def main(n=200):
    w = E.load_world()
    for pname, pol in POLICIES.items():
        dist = collections.Counter()
        stats = []
        for seed in range(n):
            s, name, early = E.run_season(w, seed=seed, policy=pol)
            dist[name] += 1
            stats.append((s["psyche"], s["stage"], s["money"], s["enjou"], s["max_single"]))
        avg = [sum(x[i] for x in stats) / len(stats) for i in range(5)]
        print("\n== %s (%d 局) ==" % (pname, n))
        for k, v in dist.most_common():
            print("   %-16s %3d  %5.1f%%" % (k, v, 100.0 * v / n))
        print("   均值: 心理 %.1f 舞台 %.1f 钱 %.0f 炎上 %.1f 最高单场 %.1f"
              % tuple(avg))


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 200)
