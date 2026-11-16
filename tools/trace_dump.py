# -*- coding: utf-8 -*-
"""把 Python 引擎跑一季，逐周 dump 状态快照 —— 给 TS 移植版当标准答案。

用法：
    python tools/trace_dump.py > app/test/trace_expected.json

移植后 `app/test/trace.test.ts` 会用同样的种子跑 TS 版，逐周逐字段比对。
任何一处算法漂了，第一周就会对不上（因为 rng 调用次数一变，后面全错位）。

**必须用捆绑解释器**（PATH 里的 python.exe 是 Microsoft Store 假壳）：
    C:\\Users\\kk\\.dsh\\dsh-runtimes\\dsh-primary-runtime\\dependencies\\python\\python.exe
"""
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
GAME = os.path.join(os.path.dirname(HERE), "game")
sys.path.insert(0, GAME)

import engine as E  # noqa: E402

E.DATA = os.path.join(os.path.dirname(HERE), "data")

# 状态里不该进快照的：rng 对象（不可 JSON）、以及纯界面用的临时量
SKIP = {"_rng"}


def norm(v):
    """把状态里的 Python 特有点（set / 嵌套 dict）变成可比较的 JSON 形状。"""
    if isinstance(v, set):
        return sorted(str(x) for x in v)
    if isinstance(v, dict):
        return {str(k): norm(x) for k, x in sorted(v.items(), key=lambda kv: str(kv[0]))}
    if isinstance(v, (list, tuple)):
        return [norm(x) for x in v]
    if isinstance(v, float):
        # 浮点按 9 位有效数字收口：Python 和 JS 的 double 都是 IEEE754，
        # 但打印/中间的乘法顺序可能让最后一位不同。
        return float(f"{v:.9g}")
    if isinstance(v, bool) or v is None or isinstance(v, (int, str)):
        return v
    return str(v)


def snap(s):
    out = {}
    for k, v in s.items():
        if k in SKIP:
            continue
        out[k] = norm(v)
    return out


def run(seed):
    world = E.load_world()
    rng = __import__("random").Random(seed)
    s = E.new_state(world, rng=rng)
    weeks = []
    weeks.append({"week": 0, "state": snap(s)})
    total = int(s["weeks_total"])
    for i in range(total):
        info = E.do_week(s, world, rng)
        weeks.append({
            "week": i + 1,
            "tier": info["tier"],
            "score": float(f"{info['score']:.9g}"),
            "report": norm(info["report"]),
            "state": snap(s),
        })
    name, early = E.judge(s, world, s.get("true_talk", 0))
    return {"seed": seed, "total": total, "weeks": weeks, "ending": name, "early": early}


def main():
    seeds = [0, 1, 7, 42]
    out = {"days": len(E.load_world()["cards"]), "runs": [run(sd) for sd in seeds]}
    text = json.dumps(out, ensure_ascii=False, separators=(",", ":"))
    if len(sys.argv) > 1:
        # 直接写文件：PowerShell 的 `>` 重定向会写成 UTF-16LE，Node 的 JSON.parse 读不了。
        with open(sys.argv[1], "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
            f.write("\n")
    else:
        sys.stdout.write(text + "\n")


if __name__ == "__main__":
    main()
