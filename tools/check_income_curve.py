# -*- coding: utf-8 -*-
"""对比特典收入公式：旧版线性 vs 新版黏性加权（W_POW）。
看两点：(1) 五个 OTA 都 50 时的基准收入别崩；(2) 高黏的人贡献占比明显更高。
"""
import importlib.util, os
here = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("sb", os.path.join(here, "economy_sandbox.py"))
sb = importlib.util.module_from_spec(spec)
# 避免执行 __main__ 块
import sys
sys.argv = ["x"]
spec.loader.exec_module(sb)

def income_old(otas, fame):
    return sum((x/100)*280 for x in otas) * (1 + fame/100)

def income_new(otas, fame, W_STICK=1.414, W_POW=1.5):
    return sum(280 * W_STICK * (x/100)**W_POW for x in otas) * (1 + fame/100)

def share_new(otas):
    """高黏贡献占比：把 OTA 按黏性排序，前两名贡献占总额比例"""
    vals = sorted([280 * 1.414 * (x/100)**1.5 for x in otas], reverse=True)
    return sum(vals[:2]) / sum(vals)

def share_old(otas):
    vals = sorted([(x/100)*280 for x in otas], reverse=True)
    return sum(vals[:2]) / sum(vals)

cases = [
    ("五人均 50（开局基线）", [50,50,50,50,50], 5),
    ("五人均 70（都养起来）", [70,70,70,70,70], 20),
    ("两人 90 其余 40（集中养）", [90,90,40,40,40], 20),
    ("一人 95 其余 45（死忠一人）", [95,45,45,45,45], 20),
    ("五人均 30（都在流失）", [30,30,30,30,30], 5),
]

print(f"{'情形':<26}{'旧收入':>9}{'新收入':>9}{'变化':>9}{'前2名占比旧':>10}{'新':>7}")
for name, otas, fame in cases:
    o = income_old(otas, fame); n = income_new(otas, fame)
    print(f"{name:<26}{o:>9.0f}{n:>9.0f}{(n/o-1)*100:>8.0f}%{share_old(otas)*100:>9.0f}%{share_new(otas)*100:>6.0f}%")

print("\n高黏贡献占比（同人气 20）：")
for name, otas, fame in cases:
    o = income_old(otas, fame); n = income_new(otas, fame)
    print(f"  {name}: 新= {n:.0f} / 人均 {n/5:.0f}")

# 沙盒 11 策略跑一遍，确认结局仍全可达
print("\n=== 沙盒 11 策略复核 ===")
reach = {}
for name, p in sb.PROFILES.items():
    s = sb.run(p, seed=1)
    e = sb.judge(s)
    reach[e] = reach.get(e, 0) + 1
    print(f"{name:<8}-> {e:<8} 钱{s['money']:>6.0f} 心理{s['psyche']:>4.0f} 舞台{s['stage']:>4.0f}")
all_endings = ['被吞噬','执念成魔','交易孤立','空心','连累','成为系统','高光一瞬','幸存','被留下','主动下车','平凡退场']
missing = [x for x in all_endings if x not in reach]
print("覆盖 %d/11" % len([x for x in all_endings if x in reach]), "未覆盖:", missing if missing else "无")
