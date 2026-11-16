# -*- coding: utf-8 -*-
"""gap 卡点完后：队列里如果还排着动作选择，就别再 push 一张新的（会变成两张排队）。">
"""
import io, os

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
LOOP = os.path.join(ROOT, "game", "loop.py")
s = io.open(LOOP, encoding="utf-8").read()

old = '''        if origin == "gap":
            # 这张卡插在两张 act 选择之间：下一张 act 选择本来就还在队列里，别重建
            has_act = any(x.get("type") == "choice" and x.get("kind") == "act"
                          for x in self.queue)
            if not has_act and not settled:
                self._build_weekday()'''
new = '''        if origin == "gap":
            # 这张卡插在两张 act 选择之间：下一张 act 选择本来就还在队列里，别重建。
            # 注意队列里排着的「回执 + 下一张动作选择」要原样留着，不能再 push 第二张。
            has_act = any(x.get("type") == "choice" and x.get("kind") == "act"
                          for x in self.queue)
            if not has_act and not settled:
                self._build_weekday()'''
assert old in s
s = s.replace(old, new)
io.open(LOOP, "w", encoding="utf-8").write(s)
print("OK")
