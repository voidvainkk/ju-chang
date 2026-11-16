# -*- coding: utf-8 -*-
"""结局可达性审计：给每个结局写一个「目标档案」，让策略朝那个方向走，
跑 N 局看命中率。这是给引擎调数值用的，不是给玩家看的。

用法：python tools/probe_endings.py [局数]
"""
import os, sys, random, collections

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "game"))
import engine as E
import policy as P


class Targeted(P.Policy):
    """按目标结局的参数改行为：
    goal= 欲求的资源键列表（选卡时偏好），act= 每周三个动作的序列（循环取）。"""

    def __init__(self, goal=(), act=None, avoid=(), rng=None):
        super().__init__(rng)
        self.goal = tuple(goal)
        self.avoid = tuple(avoid)
        self.act_seq = list(act or [])
        self._i = 0

    def act(self, s):
        if self.act_seq:
            a = self.act_seq[self._i % len(self.act_seq)]
            self._i += 1
            return a
        return super().act(s)

    def __call__(self, s, card, options):
        best, bi = -1e9, 0
        for i, o in enumerate(options):
            v = 0.0
            for k, d in (o.get("immediate") or {}).items():
                if not isinstance(d, (int, float)):
                    continue
                if k in self.goal:
                    v += d * 2.0
                if k in self.avoid:
                    v -= d * 2.0
            if v > best:
                best, bi = v, i
        return bi


GOALS = {
    # 名字: (goal 资源, 每周动作, 备注)
    "如影随形": (("kaibox",), ["content", "content", "work"]),
    "你第一天知道我的恶劣吗": (("enjou", "banzi", "fame"), ["content", "content", "mc"]),
    "执念成魔": (("stage",), ["dance", "dance", "sing"]),
    "空心": (("template",), ["work", "work", "work"]),
    "残局": (("relation_all",), ["dance", "dance", "mc"]),
    "现生快乐": (("psyche",), ["rest", "rest", "work"]),
    "彗星来临的那一夜": (("stage",), ["dance", "dance", "sing"]),
    "守住本心": (("psyche",), ["rest", "dance", "sing"]),
    "台上那十分钟": (("psyche",), ["dance", "sing", "work"]),
    "散场": (("enjou",), ["work", "rest", "work"]),
}


def main(n=30):
    w = E.load_world()
    total = collections.Counter()
    for name, (goal, acts) in GOALS.items():
        hit = collections.Counter()
        for seed in range(n):
            pol = Targeted(goal=goal, act=acts, rng=random.Random(seed))
            s, got, _ = E.run_season(w, seed=seed, policy=pol)
            hit[got] += 1
        total.update(hit)
        top = hit.most_common(3)
        flag = "" if top[0][0] == name else "   <<< 没打中目标"
        print("%-10s %s%s" % (name, ", ".join("%s %d" % (k, v) for k, v in top), flag))
    print("\n合计：", dict(total))


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 30)
