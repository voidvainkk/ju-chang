# -*- coding: utf-8 -*-
"""盘点：一局里每个资源键的实际总流量（玩家能拿到多少），用来校准经济。
用法：python tools\\audit_flow.py [局数]
"""
import os, sys, collections, random

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "game"))
import engine as E
import policy as P


def main(n=40):
    w = E.load_world()
    total = collections.Counter()
    cnt = collections.Counter()
    for seed in range(n):
        pol = P.Greedy(); pol.rng.seed(seed)
        s = E.new_state(w); rng = random.Random(seed)
        for _ in range(6):
            before = dict((k, s.get(k, 0)) for k in s if isinstance(s.get(k), (int, float)))
            E.do_week(s, w, rng, pol)
            for k in before:
                d = s.get(k, 0) - before[k]
                if abs(d) > 1e-9:
                    total[k] += d
                    cnt[k] += 1
    print("资源键           出现次数(局)  总变化    每局平均")
    for k, v in total.most_common():
        print("  %-12s %6d  %10.1f  %8.2f" % (k, cnt[k], v, v / n))


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 40)
