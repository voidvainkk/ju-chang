# -*- coding: utf-8 -*-
"""舞/唱/live 对「台上一场」的边际收益曲线：每一档技能值对应的单场分数。

用户 m05878 问「舞蹈歌唱提升之后有什么用」——先把换算关系摆出来。
"""
import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "game"))
import engine as E


def score_of(dance, sing, mc, rel=50):
    return 0.32 * dance + 0.28 * sing + 0.22 * mc + 0.18 * rel


base = E.new_state.__globals__["BASE"] if "BASE" in E.new_state.__globals__ else None
print("舞台分 = 舞×0.32 + 唱×0.28 + 话术×0.22 + 队友关系×0.18")
print("单场 = 舞台分 + 今晚剩多少力气(±5) + 运气(±5)   ±10 的噪声")
print("档位：神场≥64  好场≥54  平场≥44  冷场≥34  翻车<34\n")

print("开局的四个数：舞45 唱40 话术35 关系50")
print("  舞台分 = %.1f   → 最低 %.1f，最高 %.1f" % (
    score_of(45, 40, 35), score_of(45, 40, 35) - 10, score_of(45, 40, 35) + 10))
print()

print("%-6s %-6s %-6s %-6s %8s %8s" % ("舞", "唱", "话术", "关系", "舞台分", "神场概率"))
import random
rng = random.Random(0)
for d in (45, 50, 55, 60, 65, 70, 75, 82):
    sc = score_of(d, d - 2, 35, 50)
    n = 4000
    hits = sum(1 for _ in range(n) if sc + rng.uniform(-10, 10) >= 64)
    print("%-6d %-6d %-6d %-6d %8.1f %8.1f%%" % (d, d - 2, 35, 50, sc, 100.0 * hits / n))
print()
print("练一晚：舞 +2.5（连做会减半）。一季六晚全练舞，最多 +15 → 舞台分 +4.8。")
print("要从「平场」稳定跳到「神场」，舞台分得从 40 涨到 64，差 24 分。")
print("舞占 0.32：24 / 0.32 = 需要 75 点舞。而 SKILL_CAP = 82。")
