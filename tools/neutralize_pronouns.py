# -*- coding: utf-8 -*-
"""把指向 OTA 的「他/她」统一改成「ta」。

为什么要有这个：OTA 的性别是开局按原型掷的（engine._gender_for 可能给男或女），
但卡面文案里写死的是「他」或「她」，同一个 OTA 在不同卡里性别会打架。
玩家看到的就是「性别错乱」。主角固定女（用「我」）、队友固定女（阿棠/露露/小满）、
private.json 里搬器材的男生固定男——这些不该动。

用法：
    python tools/neutralize_pronouns.py data/ota_memory.json
    python tools/neutralize_pronouns.py --dry data/cards/ota.json

也可以被生成器 import：`from neutralize_pronouns import neutralizer`。
"""

import json
import re
import sys

# 不能被替换的词。替换前先换成一个不会出现在文案里的占位符，处理完再还原。
GUARD = {
    "其他": "\x01QT\x01",
    "吉他": "\x01GT\x01",
    "他处": "\x01TC\x01",
    "利他": "\x01LT\x01",
}

# 复数先处理，否则「他们」会被拆成「ta们」之前先命中单体规则也没关系，
# 但显式写出来更清楚：他们/她们 都变成 ta们。
PLURAL = {"他们": "ta们", "她们": "ta们"}


def neutralizer(text):
    """单个字符串：把指人的他/她换成 ta，保护「其他」这类复合词。"""
    if not isinstance(text, str):
        return text
    # 先把「他/她」这种并列写法收掉
    text = text.replace("他/她", "ta").replace("她/他", "ta")
    for k, v in GUARD.items():
        text = text.replace(k, v)
    for k, v in PLURAL.items():
        text = text.replace(k, v)
    text = text.replace("他", "ta").replace("她", "ta")
    for k, v in GUARD.items():
        text = text.replace(v, k)
    return text


def walk(obj):
    """递归处理 dict/list 里的所有字符串（键名不动）。"""
    if isinstance(obj, str):
        return neutralizer(obj)
    if isinstance(obj, list):
        return [walk(x) for x in obj]
    if isinstance(obj, dict):
        return {k: walk(v) for k, v in obj.items()}
    return obj


def detect_indent(raw):
    """照原文件的缩进风格写回，避免整份 diff。"""
    m = re.search(r"\n(\s+)\"", raw)
    if not m:
        return 2
    return len(m.group(1))


def run(path, dry=False):
    raw = open(path, encoding="utf-8").read()
    doc = json.loads(raw)
    out = walk(doc)
    indent = detect_indent(raw)
    new = json.dumps(out, ensure_ascii=False, indent=indent) + "\n"
    if new == raw or new == raw.rstrip("\n") + "\n":
        print("  %s: 无变化" % path)
        return 0
    changed = sum(
        1 for a, b in zip(re.findall(r"[\u4ed6\u5979]", raw), re.findall(r"[\u4ed6\u5979]", new))
        if a != b
    )
    print("  %s: indent=%d, 剩余他/她 %d → %d"
          % (path, indent, len(re.findall(r"[\u4ed6\u5979]", raw)),
             len(re.findall(r"[\u4ed6\u5979]", new))))
    if not dry:
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(new)
    return 1


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    dry = "--dry" in sys.argv
    for p in args:
        run(p, dry=dry)
