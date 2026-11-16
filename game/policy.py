# -*- coding: utf-8 -*-
"""自动玩家（用于跑局看结局分布）。每个策略是一个可调用对象 + 可选 .act(state)。"""
import random


class Policy:
    def __init__(self, rng=None):
        self.rng = rng or random.Random(0)

    def act(self, s):
        return self.rng.choice(["dance", "sing", "mc", "content", "work", "rest"])

    def __call__(self, s, card, options):
        return self.rng.randrange(len(options))


class Greedy(Policy):
    """会算账的玩家：优先拉舞台、护心理、不碰越界。"""
    ACT_ORDER = ["dance", "sing", "mc", "content", "rest", "work"]

    def act(self, s):
        if s["stamina"] < 40:
            return "rest"
        # 练最弱的那个（不再用拍内容垫体力：那是白给）
        low = min(("dance", "sing", "mc"), key=lambda k: s[k])
        return low

    def __call__(self, s, card, options):
        best, bi = -1e9, 0
        for i, o in enumerate(options):
            sc = 0.0
            for k, v in (o.get("immediate") or {}).items():
                if k.startswith("@") or k == "ota_all":
                    sc += v * 1.2
                elif k == "relation_all":
                    sc += v * 1.0
                elif k in ("enjou", "kaibox", "banzi", "shiroi", "shiren", "zhongs"):
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


class Reckless(Policy):
    """拼命型：只求舞台和钱，不要命。"""
    ACT_ORDER = ["dance", "dance", "sing", "content"]

    def act(self, s):
        # 灯亮之前先把腿练到不抖——体力不够也硬上
        return self.rng.choice(self.ACT_ORDER)

    def __call__(self, s, card, options):
        best, bi = -1e9, 0
        for i, o in enumerate(options):
            sc = 0.0
            for k, v in (o.get("immediate") or {}).items():
                if k in ("dance", "sing", "mc", "fame", "stage"):
                    sc += v * 2.0
                elif k in ("enjou", "kaibox", "banzi", "shiroi"):
                    sc -= v * 0.2
                elif k == "psyche":
                    sc -= v * 0.5      # 反着选：让人难受的那条才够用力
                elif k == "stamina":
                    sc -= v * 0.2      # 多干一点
                elif k == "money":
                    sc += v * 0.003
            if sc > best:
                best, bi = sc, i
        return bi


class Flirty(Policy):
    """把人哄住型：不练功，靠拍内容和特典会上那套现成的话把人留着。"""
    def act(self, s):
        if s["stamina"] < 30:
            return "rest"
        if s["money"] < 800:
            return "work"
        return "content"

    def __call__(self, s, card, options):
        best, bi = -1e9, 0
        for i, o in enumerate(options):
            sc = 0.0
            for k, v in (o.get("immediate") or {}).items():
                if k.startswith("@") or k in ("ota_all", "psyche"):
                    sc += v * 2.0
                elif k in ("enjou", "kaibox"):
                    sc -= v * 0.4
                elif k == "stamina":
                    sc += v * 0.3
                elif k == "fame":
                    sc += v * 0.8
            if sc > best:
                best, bi = sc, i
        return bi


class Hollow(Policy):
    """空心：不练功、不拒绝、什么都顺着说，只想把这一季平稳地过完。"""
    def act(self, s):
        if s["money"] < 700:
            return "work"
        return "content"

    def __call__(self, s, card, options):
        best, bi = -1e9, 0
        for i, o in enumerate(options):
            sc = 0.0
            for k, v in (o.get("immediate") or {}).items():
                if k.startswith("@") or k == "ota_all":
                    sc += v * 1.5
                elif k in ("dance", "sing", "mc"):
                    sc -= v * 0.8          # 不练
                elif k == "psyche":
                    sc += v * 1.2          # 只挑让自己好受的
                elif k in ("enjou", "kaibox", "banzi"):
                    sc -= v * 2.0          # 不惹事
                elif k == "stamina":
                    sc += v * 0.3
            if sc > best:
                best, bi = sc, i
        return bi

