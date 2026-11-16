# -*- coding: utf-8 -*-
"""《聚场》本地服务：给界面一个很薄的一层 HTTP。

只用标准库，不装任何东西。启动：
    python game/server.py            # 默认 http://127.0.0.1:8765
参数：--port 8765 --open

路由
    GET  /                → web/index.html（以及同目录静态文件）
    POST /api/new         → 新开一局 {"seed": 可选}
    GET  /api/state       → 当前 step + 数值快照
    POST /api/advance     → 继续（文字/回执/演出/面板）
    POST /api/choose      → {"id": "..."} 选择（选项/动作/卡/取名/风格）
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import io
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import loop  # noqa: E402

WEB = os.path.join(HERE, "..", "web")
LANG = {".html": "text/html; charset=utf-8", ".css": "text/css; charset=utf-8",
        ".js": "application/javascript; charset=utf-8", ".json": "application/json; charset=utf-8"}


SAVE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_save.json")
# 结局图鉴：跨周目保留，删档/重开都不清它。想清就自己删 _gallery.json。
GALLERY = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_gallery.json")
_GALLERY_LOCK = threading.Lock()


def _load_gallery():
    try:
        with io.open(GALLERY, encoding="utf-8") as f:
            d = json.load(f)
        if isinstance(d, dict) and isinstance(d.get("endings"), dict):
            return d
    except Exception:
        pass
    return {"endings": {}}


def _save_gallery(d):
    tmp = GALLERY + ".tmp"
    with io.open(tmp, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=1)
    os.replace(tmp, GALLERY)


def _record_ending(g):
    """一局走到结局时记一次图鉴。同一局只记一次（save 每步都调）。"""
    s = g.state or {}
    name = s.get("ending")
    if not name:
        return
    import time
    with _GALLERY_LOCK:
        d = _load_gallery()
        rec = d["endings"].get(name) or {"count": 0, "first_at": "", "last_at": ""}
        rec["count"] = int(rec.get("count") or 0) + 1
        rec["last_at"] = time.strftime("%Y-%m-%d %H:%M")
        if not rec.get("first_at"):
            rec["first_at"] = rec["last_at"]
        try:
            rec["last_echo"] = g._echo()
        except Exception:
            pass
        d["endings"][name] = rec
        _save_gallery(d)


def _gallery_payload():
    got = _load_gallery().get("endings") or {}
    try:
        with io.open(os.path.join(loop.DATA, "endings.json"), encoding="utf-8") as f:
            end = json.load(f)
        with io.open(os.path.join(loop.DATA, "endings_lore.json"), encoding="utf-8") as f:
            lore = json.load(f)
    except Exception:
        end, lore = {"flow": [], "early": []}, {}
    rows = []
    for e in list(end.get("flow") or []) + list(end.get("early") or []):
        name = e.get("name")
        lo = lore.get(name) or {}
        rec = got.get(name)
        if rec:
            rows.append({"n": e.get("n"), "name": name, "locked": False,
                         "core": lo.get("core", ""), "style": lo.get("style", ""),
                         "count": rec.get("count", 1), "first_at": rec.get("first_at", ""),
                         "last_at": rec.get("last_at", ""), "last_echo": rec.get("last_echo")})
        else:
            rows.append({"n": e.get("n"), "name": "？？？", "locked": True,
                         "hint": lo.get("hint", ""), "count": 0})
    return {"endings": rows, "total": len(rows), "unlocked": len(got),
            "seen": sorted(got.keys())}


def _rng_state(st):
    ver, internal, gauss = st
    return [ver, list(internal), gauss]


def _rng_load(st):
    ver, internal, gauss = st
    return (int(ver), tuple(int(x) for x in internal), gauss)


def _dump_game(g):
    if g.state is None:          # 序章阶段：还没开周
        return {"state": None, "queue": g.queue, "pending": g.pending,
                "wk": g.wk, "acts_done": g.acts_done, "over": g.over,
                "rng": _rng_state(g.rng.getstate()),
                "name": g.name, "name_style": g.name_style, "name_options": g.name_options}
    s = dict(g.state)
    s["flags"] = sorted(s.get("flags") or [])
    for k in ("_fired", "_met_people", "_weeks_seen"):
        if isinstance(s.get(k), set):
            s[k] = sorted(s[k])
    return {"state": s, "queue": g.queue, "pending": g.pending,
            "wk": g.wk, "acts_done": g.acts_done, "over": g.over,
            "rng": _rng_state(g.rng.getstate())}


def _last_season():
    """最近解锁的那个结局 + 它的回响，作为二周目开局姿态屏的上一季。"""
    got = _load_gallery().get("endings") or {}
    if not got:
        return None
    name, rec = max(got.items(), key=lambda kv: kv[1].get("last_at") or "")
    e = rec.get("last_echo") or {}
    return {"name": name, "week": e.get("week"), "stage": e.get("stage"),
            "psyche": e.get("psyche"), "truth_rate": e.get("truth_rate"),
            "stance_name": e.get("stance_name")}


def _fresh_game(seed=None):
    g = loop.Game(seed=seed)
    prev = _last_season()
    if prev:
        g.allow_stance = True
        g.prev_season = prev
    return g


def _load_game(doc):
    g = loop.Game(seed=0)      # 世界照样要建，状态全用存档覆盖
    s = doc.get("state")
    if s is not None:
        s["flags"] = set(s.get("flags") or [])
    for k in ("_fired", "_met_people", "_weeks_seen"):
        if s is not None and isinstance(s.get(k), list):
            s[k] = set(s[k])
    g.state = s if s is not None else None
    if g.state is not None:
        # 名字/风格存在 state 里；重启后要把 Game.name 补回来，
        # 否则快照的 name 会变 null（像素小人和部分文案会以为还没取名）。
        g.name = s.get("name") or g.name
        g.name_style = s.get("name_style") or g.name_style
    if g.state is None:
        g.queue = doc.get("queue") or []
        g.name = doc.get("name")
        g.name_style = doc.get("name_style")
        g.name_options = doc.get("name_options") or []
        g.rng.setstate(_rng_load(doc["rng"])) if doc.get("rng") else None
        return g
    g.queue = doc.get("queue") or []
    g.pending = doc.get("pending")
    g.wk = doc.get("wk") or {}
    g.acts_done = doc.get("acts_done", 0)
    g.over = doc.get("over", False)
    if doc.get("rng"):
        g.rng.setstate(_rng_load(doc["rng"]))
    return g


class Session:
    """单进程单局；每次操作都落盘，服务重启（改代码）也不会丢进度。"""

    def __init__(self):
        self.lock = threading.Lock()
        self.game = None
        self._recorded = None
        try:
            if os.path.exists(SAVE):
                doc = json.load(io.open(SAVE, encoding="utf-8"))
                self.game = _load_game(doc)
                if self.game.over and (self.game.state or {}).get("ending"):
                    self._recorded = self.game.state["ending"]
                print("已读档：第 %s 周" % (self.game.state.get("week") if self.game.state else "序章"))
        except Exception as e:
            print("读档失败，新开一局：", e)
        if self.game is None:
            self.game = _fresh_game(seed=None)

    def save(self):
        try:
            doc = _dump_game(self.game)
            tmp = SAVE + ".tmp"
            with io.open(tmp, "w", encoding="utf-8") as f:
                json.dump(doc, f, ensure_ascii=False)
            os.replace(tmp, SAVE)
        except Exception as e:
            print("存档失败：", e)
        # 结局图鉴：走到结局那一步记一次，同一局不重复记
        g = self.game
        end = (g.state or {}).get("ending") if g.over else None
        if end and end != self._recorded:
            self._recorded = end
            try:
                _record_ending(g)
            except Exception as e:
                print("图鉴记录失败：", e)

    def payload(self):
        g = self.game
        cur = g.current()
        return {"step": cur, "snapshot": g.snapshot(), "over": g.over}

    def journal(self):
        g = self.game
        s = (g.state if g else {}) or {}
        return {"log": s.get("log") or [], "over": bool(g and g.over),
                "ending": s.get("ending") or ""}

    def new(self, seed=None):
        self.game = _fresh_game(seed=seed)
        self._recorded = None
        self.save()
        return self.payload()

    def advance(self):
        self.game.advance()
        self.save()
        return self.payload()

    def choose(self, oid):
        g = self.game
        cur = g.current()
        if cur is None:
            return self.payload()
        t = cur["type"]
        if t == "name":
            if cur.get("stage") == "style":
                g.pick_style(oid)
            else:
                g.set_name(oid)
        elif t == "choice":
            kind = cur.get("kind")
            if kind == "intro":
                g.choose_intro(oid)
            elif kind == "act":
                g.choose_act(oid)
            elif kind == "empty":
                g.choose_empty(oid)
            elif kind == "offer":
                g.choose_offer(oid)
            elif kind == "leave":
                g.choose_leave(oid)
        elif t in ("card", "chat"):
            if cur.get("talk"):
                g.choose_talk(oid)
            else:
                g.choose_card(oid)
        elif t == "stance":
            g.choose_stance(oid)
        self.save()
        return self.payload()


SESSION = Session()


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, code, body, ctype="application/json; charset=utf-8"):
        if isinstance(body, str):
            body = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, obj, code=200):
        self._send(code, json.dumps(obj, ensure_ascii=False).encode("utf-8"))

    def _body(self):
        n = int(self.headers.get("Content-Length") or 0)
        if not n:
            return {}
        try:
            return json.loads(self.rfile.read(n).decode("utf-8"))
        except Exception:
            return {}

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/api/state":
            with SESSION.lock:
                return self._json(SESSION.payload())
        if path == "/api/gallery":
            return self._json(_gallery_payload())
        if path == "/api/journal":
            with SESSION.lock:
                return self._json(SESSION.journal())
        if path == "/":
            path = "/index.html"
        fp = os.path.normpath(os.path.join(WEB, path.lstrip("/")))
        if not fp.startswith(os.path.normpath(WEB)) or not os.path.isfile(fp):
            return self._send(404, "not found", "text/plain; charset=utf-8")
        ext = os.path.splitext(fp)[1].lower()
        with open(fp, "rb") as f:
            self._send(200, f.read(), LANG.get(ext, "application/octet-stream"))

    def do_POST(self):
        path = urlparse(self.path).path
        data = self._body()
        try:
            with SESSION.lock:
                if path == "/api/new":
                    seed = data.get("seed")
                    return self._json(SESSION.new(seed=int(seed) if seed not in (None, "") else None))
                if path == "/api/advance":
                    return self._json(SESSION.advance())
                if path == "/api/choose":
                    return self._json(SESSION.choose(str(data.get("id", ""))))
        except Exception as exc:      # 单次失误不要把整个局带崩：把错误回给界面
            import traceback
            traceback.print_exc()
            return self._json({"error": "%s: %s" % (type(exc).__name__, exc)}, 500)
        return self._send(404, "not found", "text/plain; charset=utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--open", action="store_true")
    a = ap.parse_args()
    srv = ThreadingHTTPServer(("127.0.0.1", a.port), Handler)
    url = "http://127.0.0.1:%d/" % a.port
    print("聚场 →", url, flush=True)
    if a.open:
        webbrowser.open(url)
    srv.serve_forever()


if __name__ == "__main__":
    main()
