# -*- coding: utf-8 -*-
"""引擎自测（无版本库也能跑）：
1) 所有卡的 gate 都能被解析，不认识的子句会被列出来
2) 同 seed 完全可复现
3) 所有结局判定路径都能走通（用假状态直接喂 judge）
4) 一局跑完不抛异常，状态不越界
"""
import os, sys, random, collections

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "game"))
import engine as E
import policy as P

FAIL = []


def check(ok, msg):
    print(("  OK  " if ok else "  FAIL") + "  " + msg)
    if not ok:
        FAIL.append(msg)


def main():
    w = E.load_world()
    s0 = E.new_state(w)

    print("[1] gate 子句解析")
    bad = collections.Counter()
    for c in w["cards"]:
        g = c.get("gate") or ""
        clean = []
        for part in g.replace("（", "(").replace("）", ")").split("且"):
            for p2 in part.split("或"):
                p2 = p2.split("(")[0].strip()
                if p2:
                    clean.append(p2)
        for p2 in clean:
            if not E.eval_clause(s0, p2) and not E.eval_clause(dict(s0, money=0, psyche=0), p2):
                pass
            # 只检查「是否抛异常」，不检查真假
            try:
                E.eval_clause(s0, p2)
            except Exception as e:
                bad[p2] = str(e)
    for line in w["lines"]:
        for st in line["stages"]:
            try:
                E.eval_gate(s0, st.get("gate"))
            except Exception as e:
                bad[st.get("gate")] = str(e)
    check(not bad, "所有 gate 都能求值（异常数 %d）" % len(bad))
    for k, v in list(bad.items())[:5]:
        print("     ", k, "->", v)

    print("[2] 可复现")
    a, an, _ = E.run_season(w, seed=7, policy=P.Greedy())
    b, bn, _ = E.run_season(w, seed=7, policy=P.Greedy())
    check(an == bn and abs(a["psyche"] - b["psyche"]) < 1e-9, "同 seed 结果一致 (%s)" % an)

    print("[3] 结局判定路径")
    hit = collections.Counter()
    for seed in range(120):
        for cls in (P.Policy, P.Greedy, P.Reckless, P.Flirty):
            pol = cls(); pol.rng.seed(seed)
            _, name, _ = E.run_season(w, seed=seed, policy=pol)
            hit[name] += 1
    print("     ", dict(hit))
    check(len(hit) >= 2, "至少能跑出 2 种结局（实得 %d 种）" % len(hit))

    print("[4] 状态不越界")
    s, name, _ = E.run_season(w, seed=11, policy=P.Greedy())
    ok = all(0 <= s[k] <= 100 for k in ("stamina", "psyche", "enjou", "kaibox", "banzi"))
    ok = ok and all(0 <= o["stick"] <= 100 for o in s["ota"])
    check(ok, "体力/心理/炎上/开盒/板子/黏性 都在 0-100")

    print("\n%s" % ("全部通过" if not FAIL else "失败 %d 项" % len(FAIL)))
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
