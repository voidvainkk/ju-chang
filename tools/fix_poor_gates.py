# -*- coding: utf-8 -*-
"""用户 m05878 选 c：把「穷」的门槛改成贴着真实分布。

实测（money_report.py，15 局）：一季手里的钱中位 1700 / 2100 / 1920 / 2180 / 2200 / 2420 / 2722；
最低到过 440、0。也就是说「钱 < 1500」只占 5% 的周，「钱 < 1000/800」更是几乎不可能。

改法：把「穷」理解为「比平时少」，按真实分布取到 1500~2400 这一段，
让「手头紧」变成一季里偶尔会发生的事，而不是永不发生的死门。
"""
import io, json, os

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "cards")

# id -> (旧 gate, 新 gate)
FIX = {
    # ambient：钱 < 1000 → 2600（周中位数附近，常见的拮据）
    ("ambient.json", "钱 < 1000"): "钱 < 2600",
    # daily：店长又问你
    ("daily.json", "本周已选打工 或 钱 < 800（手头紧）"): "本周已选打工 或 钱 < 2200（手头紧）",
    # daily：这周的账（本来就是房租周）
    ("daily.json", "周 ≥ 2 且 钱 < 2400（房租那周）"): "周 ≥ 2 且 钱 < 2200（房租那周）",
    # daily：排班和加练撞了
    ("daily.json", "钱 < 1500（手头有点紧）"): "钱 < 2400（手头有点紧）",
    # ota：这个月我多买几张
    ("ota.json", "任一 OTA 黏性 ≥ 70 且 钱 < 1800"): "任一 OTA 黏性 ≥ 70 且 钱 < 2600",
}

# 只改 gate，不动 condition（condition 是延迟后果的触发条件，误改会连带改语义）
done = []
for (fn, old), new in FIX.items():
    p = os.path.join(BASE, fn)
    s = io.open(p, encoding="utf-8").read()
    # 只替换出现在 "gate": 行里的那一处
    line_old = '"gate": "%s"' % old
    line_new = '"gate": "%s"' % new
    if line_old not in s:
        print("MISS", fn, old)
        continue
    s = s.replace(line_old, line_new, 1)
    io.open(p, "w", encoding="utf-8").write(s)
    json.loads(s)
    done.append((fn, old, new))

for d in done:
    print("OK  %-14s %s  →  %s" % d)
print("共改 %d 处" % len(done))
