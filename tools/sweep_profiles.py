# -*- coding: utf-8 -*-
"""跑一批档案，看一圈分布（改了体力之后要重新确认结局还够得着）。"""
import os
import sys
import random
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "game"))

import engine as E  # noqa: E402

world = E.load_world()
WEEKS = 6


class Arch:
    def __init__(self, name, order, choice, like=(), avoid=()):
        self.name, self.order, self.choice = name, list(order), choice
        self.like, self.avoid = set(like), set(avoid)
        self.i = 0

    def act(self, s):
        try:
            return self.order[self.i % len(self.order)]
        finally:
            self.i += 1

    def __call__(self, s, card, opts):
        best, bv = 0, -1e9
        for i, o in enumerate(opts):
            v = 0.0
            for k, dv in (o.get("immediate") or {}).items():
                w = 1.0
                if k in self.like:
                    w = 2.0
                elif k in self.avoid:
                    w = -2.0
                v += dv * w
            if v > bv:
                best, bv = i, v
        return best


PROFILES = {
    "熬":    Arch("熬", ["dance", "sing", "mc"] * 2, lambda s, c, o: 0, like=("fame", "stage"), avoid=("psyche",)),
    "躺":    Arch("躺", ["rest"] * 6, lambda s, c, o: 0),
    "直播":  Arch("直播", ["work", "work", "dance"] * 2, lambda s, c, o: 0, like=("money",)),
    "哄人":  Arch("哄人", ["content", "rest", "work"] * 2, lambda s, c, o: 0, like=("@speaker", "ota_all", "fame")),
    "说真话": Arch("说真话", ["dance", "rest", "sing"] * 2, lambda s, c, o: 0, like=("psyche",), avoid=("enjou",)),
    "混":    Arch("混", ["content", "mc", "rest"] * 2, lambda s, c, o: 0),
}


def run(arch, seed):
    s = E.new_state(world, rng=random.Random(seed))
    name = E.run_season(world, seed=seed, policy=arch)
    return name


def main(n=40):
    for pname, arch in PROFILES.items():
        arch.i = 0
        c = Counter()
        st = []
        for k in range(n):
            arch.i = 0
            r = E.run_season(world, seed=k, policy=arch)
            if isinstance(r, tuple):
                st0, nm, early = r
            else:
                st0, nm, early = r, r.get("ending"), False
            c[nm if isinstance(nm, str) else str(nm)] += 1
        print(pname, dict(c.most_common()))


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 40)
