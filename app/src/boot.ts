// 《聚场》浏览器入口：把 Python 版的 `game/server.py` 那一层换成纯前端。
//
// 对界面暴露的接口和原来的 HTTP 路由一一对应，所以 `web/app.js` 里
// 那八个 `/api/*` 调用点一个字都不用改：
//     GET  /api/state   → call("/api/state")
//     POST /api/advance → call("/api/advance", {})
//     POST /api/choose  → call("/api/choose", {id})
//     POST /api/new     → call("/api/new", {})
//     GET  /api/gallery → call("/api/gallery")
//     GET  /api/journal → call("/api/journal")
//
// 存档从 `game/_save.json` 改成 localStorage，图鉴同理。

import * as E from "./core/engine.ts";
import { Game } from "./core/loop.ts";

const SAVE_KEY = "ju-chang.save.v1";
const GAL_KEY = "ju-chang.gallery.v1";

/* ------------------------------------------------------------------ 数据 */

/**
 * 把 `data/` 下的 JSON 与 `结局.md` 收成 `相对路径 -> 内容`。
 * 键名必须和 `engine.loadWorld` 认的相对路径一致（`cards/x.json`、`intro.json`…）。
 */
function loadDataFiles(): Record<string, any> {
  const files: Record<string, any> = {};
  const put = (mods: Record<string, any>, strip: string) => {
    for (const [k, v] of Object.entries(mods)) {
      files[k.slice(strip.length)] = v;
    }
  };
  put(import.meta.glob("../../data/*.json", { eager: true, import: "default" }), "../../data/");
  put(import.meta.glob("../../data/cards/*.json", { eager: true, import: "default" }), "../../data/");
  put(import.meta.glob("../../data/storylines/*.json", { eager: true, import: "default" }), "../../data/");
  const md = import.meta.glob("../../结局.md", { eager: true, query: "?raw", import: "default" }) as Record<string, string>;
  const mdKey = Object.keys(md)[0];
  if (mdKey) files["结局.md"] = md[mdKey];
  return files;
}

const FILES = loadDataFiles();

/* ------------------------------------------------------------------ 存档 */

type Setish = { __set: unknown[] };

/** 存档里的 Set（flags / _fired / _met_people / _weeks_seen）要能过 JSON。 */
function replacer(_k: string, v: any) {
  return v instanceof Set ? ({ __set: [...v] } as Setish) : v;
}
function reviver(_k: string, v: any) {
  return v && typeof v === "object" && Array.isArray((v as Setish).__set) ? new Set((v as Setish).__set) : v;
}

function dumpDoc(g: Game, seed: number): Record<string, any> {
  // 先 stringify 再过一遍 parse，把 Set 变成数组（否则 localStorage 里是 "{}"）
  return JSON.parse(
    JSON.stringify(
      {
        v: 1,
        seed,
        state: g.state,
        queue: g.queue,
        pending: g.pending,
        wk: g.wk,
        acts_done: g.acts_done,
        over: g.over,
        name: g.name,
        name_style: g.name_style,
        name_options: g.name_options,
        allow_stance: g.allow_stance,
        prev_season: g.prev_season,
        rng: g.rng.getstate(),
      },
      replacer,
    ),
  );
}

function restoreDoc(doc: Record<string, any>): Game {
  const g = new Game(FILES, Number(doc.seed ?? 0));
  // 构造函数会把序章重新铺进 queue，下面全用存档覆盖掉
  g.state = doc.state ?? null;
  g.queue = doc.queue ?? [];
  g.pending = doc.pending ?? null;
  g.wk = doc.wk ?? {};
  g.acts_done = Number(doc.acts_done ?? 0);
  g.over = Boolean(doc.over);
  g.name = doc.name ?? null;
  g.name_style = doc.name_style ?? null;
  g.name_options = doc.name_options ?? [];
  g.allow_stance = Boolean(doc.allow_stance);
  g.prev_season = doc.prev_season ?? null;
  if (doc.rng) g.rng.setstate(doc.rng);
  return g;
}

/* ------------------------------------------------------------------ 图鉴 */

interface GalRec {
  count: number;
  first_at: string;
  last_at: string;
  last_echo?: any;
}
interface GalDoc {
  endings: Record<string, GalRec>;
}

function loadGallery(): GalDoc {
  try {
    const raw = localStorage.getItem(GAL_KEY);
    if (raw) {
      const d = JSON.parse(raw);
      if (d && typeof d === "object" && d.endings && typeof d.endings === "object") return d as GalDoc;
    }
  } catch {
    /* 坏档就当空的 */
  }
  return { endings: {} };
}

function saveGallery(d: GalDoc): void {
  localStorage.setItem(GAL_KEY, JSON.stringify(d));
}

function stamp(): string {
  const t = new Date();
  const p = (n: number) => String(n).padStart(2, "0");
  return `${t.getFullYear()}-${p(t.getMonth() + 1)}-${p(t.getDate())} ${p(t.getHours())}:${p(t.getMinutes())}`;
}

/** 一局走到结局时记一次。同一局只记一次，靠 `_recorded` 挡。 */
function recordEnding(name: string, echo: any): void {
  const d = loadGallery();
  const rec: GalRec = d.endings[name] ?? { count: 0, first_at: "", last_at: "" };
  rec.count = Number(rec.count || 0) + 1;
  rec.last_at = stamp();
  if (!rec.first_at) rec.first_at = rec.last_at;
  rec.last_echo = echo ?? rec.last_echo;
  d.endings[name] = rec;
  saveGallery(d);
}

/** 二周目姿态屏的「上一季」：取最近解锁的那个结局。 */
function lastSeason(): any {
  const got = loadGallery().endings;
  const names = Object.keys(got);
  if (!names.length) return null;
  const name = names.reduce((a, b) => ((got[a].last_at || "") >= (got[b].last_at || "") ? a : b));
  const e = got[name].last_echo || {};
  return {
    name,
    week: e.week,
    stage: e.stage,
    psyche: e.psyche,
    truth_rate: e.truth_rate,
    stance_name: e.stance_name,
  };
}

function galleryPayload() {
  const got = loadGallery().endings;
  const end: any = FILES["endings.json"] ?? { flow: [], early: [] };
  const lore: any = FILES["endings_lore.json"] ?? {};
  const rows: any[] = [];
  for (const e of [...(end.flow || []), ...(end.early || [])]) {
    const name = e.name as string;
    const lo = lore[name] || {};
    const rec = got[name];
    if (rec) {
      rows.push({
        n: e.n, name, locked: false,
        core: lo.core || "", style: lo.style || "",
        count: rec.count || 1, first_at: rec.first_at || "", last_at: rec.last_at || "",
        last_echo: rec.last_echo,
      });
    } else {
      rows.push({ n: e.n, name: "？？？", locked: true, hint: lo.hint || "", count: 0 });
    }
  }
  return { endings: rows, total: rows.length, unlocked: Object.keys(got).length, seen: Object.keys(got).sort() };
}

/* ------------------------------------------------------------------ 单局 */

let GAME: Game | null = null;
let SEED = 0;
let RECORDED: string | null = null;

function save(): void {
  if (!GAME) return;
  try {
    localStorage.setItem(SAVE_KEY, JSON.stringify(dumpDoc(GAME, SEED)));
  } catch (e) {
    console.warn("存档失败：", e);
  }
}

/** 结局那一步记图鉴；同一局不重复记。 */
function noteEnding(): void {
  const g = GAME;
  if (!g || !g.over) return;
  const name = (g.state as any)?.ending;
  if (!name || name === RECORDED) return;
  RECORDED = name;
  const head: any = g.queue[0];
  recordEnding(name, head && head.type === "end" ? head.echo : null);
}

function payload() {
  const g = GAME!;
  const snap = g.snapshot();
  // `name_style` 不在 `loop.py` 的 `snapshot()` 里（那份是逐屏对账的基准，
  // 多一个字段就让 85115 项全红），所以在 payload 这一层补——Python 版的
  // `server.py:124` 也是这么处理的。立绘靠它选四张精灵图之一。
  if (snap) (snap as any).name_style = g.name_style;
  return { step: g.current(), snapshot: snap, over: g.over };
}

/** 新开一局。`seed` 为 null 时自己掷一个整数——`PyRandom` 不收 None。 */
function freshGame(seed: number): Game {
  const g = new Game(FILES, seed);
  const prev = lastSeason();
  if (prev) {
    g.allow_stance = true;
    g.prev_season = prev;
  }
  return g;
}

function rollSeed(): number {
  return Math.floor(Math.random() * 1e9);
}

function boot(): void {
  try {
    const raw = localStorage.getItem(SAVE_KEY);
    if (raw) {
      const doc = JSON.parse(raw, reviver);
      GAME = restoreDoc(doc);
      SEED = Number(doc.seed ?? 0);
      const end = (GAME.state as any)?.ending;
      if (GAME.over && end) RECORDED = end;
      return;
    }
  } catch (e) {
    console.warn("读档失败，新开一局：", e);
  }
  SEED = rollSeed();
  GAME = freshGame(SEED);
  save();
}

function newGame(seed?: number | null) {
  SEED = seed == null ? rollSeed() : Number(seed);
  GAME = freshGame(SEED);
  RECORDED = null;
  save();
  return payload();
}

/** 界面点按钮：和 `server.py` 的 `Session.choose` 一一对应。 */
function choose(oid: string) {
  const g = GAME!;
  const cur: any = g.current();
  if (cur === null) return payload();
  const t = cur.type;
  if (t === "name") {
    if (cur.stage === "style") g.pickStyle(oid);
    else g.setName(oid);
  } else if (t === "choice") {
    const kind = cur.kind;
    // `intro` 那一支在 Python 侧调的 choose_intro 早就删了，是死分支，这里不再照抄
    if (kind === "act") g.chooseAct(oid);
    else if (kind === "empty") g.chooseEmpty(oid);
    else if (kind === "offer") g.chooseOffer(oid);
    else if (kind === "leave") g.chooseLeave(oid);
  } else if (t === "card" || t === "chat") {
    if (cur.talk) g.chooseTalk(oid);
    else g.chooseCard(oid);
  } else if (t === "stance") {
    g.chooseStance(oid);
  }
  save();
  noteEnding();
  return payload();
}

function advance() {
  GAME!.advance();
  save();
  noteEnding();
  return payload();
}

/* ------------------------------------------------------------------ 路由 */

/** `web/app.js` 唯一的入口：用法和原来的 `api(path, body)` 完全一样。 */
export async function call(path: string, body?: any): Promise<any> {
  try {
    if (!GAME) boot();
    if (path === "/api/state") return payload();
    if (path === "/api/advance") return advance();
    if (path === "/api/choose") return choose(String(body?.id ?? ""));
    if (path === "/api/new") return newGame(body?.seed ?? null);
    if (path === "/api/gallery") return galleryPayload();
    if (path === "/api/journal") {
      const s: any = GAME!.state || {};
      return { log: s.log || [], over: Boolean(GAME!.over), ending: s.ending || "" };
    }
    return { error: "unknown path " + path };
  } catch (e: any) {
    console.error(e);
    return { error: `${e?.name || "Error"}: ${e?.message || e}` };
  }
}

// 引擎的全局数据表在模块加载时就绪，顺便把世界建一次，
// 这样 `memoryTable()` 之类的懒加载在读档之前就是对的。
E.loadWorld(FILES);
