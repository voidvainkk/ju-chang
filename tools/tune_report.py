# -*- coding: utf-8 -*-
"""数值手感审计：不是跑结局，是看「一个动作值多少分、一季能攒多少」。
游戏设计的问题永远是量级问题：卡库一格 1~6 点、结局门槛 20~90，
中间的差要由动作和事件来补。这个脚本就是量那笔账。

用法：python tools/tune_report.py
"""
import os, sys, random, collections

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "game"))
import engine as E
import policy as P


def action_gain():
    print("== 动作（每周三拍，连做第二周打折）==")
    s = E.new_state(E.load_world())
    for a, d in E.ACTS.items():
        print("  %-7s %s" % (a, {k: v for k, v in d.items() if k != "weibo"}))


def card_magnitude():
    print("\n== 卡面上的数值（267 个选项的绝对值）==")
    w = E.load_world()
    per = collections.defaultdict(list)
    for c in w["cards"]:
        for o in c.get("options") or []:
            for k, v in (o.get("immediate") or {}).items():
                if isinstance(v, (int, float)):
                    per[k].append(abs(v))
    for k in sorted(per, key=lambda x: -max(per[x]))[:14]:
        xs = per[k]
        print("  %-10s n=%3d  最大 %5.1f  平均 %4.1f" % (k, len(xs), max(xs), sum(xs) / len(xs)))


def season_streams(n=40):
    print("\n== 一季的净流（%d 局随机打法）==" % n)
    w = E.load_world()
    keys = ("enjou", "banzi", "kaibox", "shiren", "true_talk", "bold", "gorshou",
            "template", "low_income_weeks")
    acc = collections.defaultdict(list)
    for seed in range(n):
        pol = P.Policy()
        pol.rng.seed(seed)
        s, got, _ = E.run_season(w, seed=seed, policy=pol)
        for k in keys:
            acc[k].append(s.get(k, 0))
        for k in ("psyche", "stamina"):
            acc[k].append(s.get(k, 0))
    for k in keys + ("psyche", "stamina"):
        xs = acc[k]
        print("  %-16s 平均 %6.1f  中位 %6.1f  最大 %6.1f" % (
            k, sum(xs) / len(xs), sorted(xs)[len(xs) // 2], max(xs)))


def thresholds():
    print("\n== 结局门槛（engines/endings.json）==")
    w = E.load_world()
    for f in w["endings"]["flow"]:
        print("  %2d %-10s %s" % (f["n"], f["name"], f["cond"]))


if __name__ == "__main__":
    action_gain()
    card_magnitude()
    season_streams()
    thresholds()
