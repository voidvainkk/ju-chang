/**
 * 《聚场》引擎 —— `game/engine.py` 的 TypeScript 移植。
 *
 * 移植原则：**逐行对齐，不"顺手优化"**。
 * 这个引擎里几乎每个常数都是调过的（FAME_SOFT=40、ENJOU_FADE_RATE=0.08、
 * 重线 base=1.0+(0.45 if…)），任何一处"看起来可以简化"的改写都会让
 * 同一颗种子走出不同的局。对账手段是 `app/test/trace.test.ts`：Python 跑
 * 一遍、TS 跑一遍，逐屏逐字段比状态。
 *
 * 与 Python 版的三处结构性差异（都不改变行为）：
 * 1. 数据不从磁盘读，由 `loadWorld(files)` 传入一张 `相对路径 -> JSON` 的表。
 *    浏览器里 `fetch`、测试里 `fs.readFileSync`，引擎本身不管 IO。
 * 2. `s["flags"]` 是 `Set<string>`（Python 也是 set，顺序无关，读法一致）。
 * 3. 随机数走 `PyRandom`（CPython MT19937 的精确移植，见 rng.ts）。
 *
 * Python 语义的移植注意点（都已在下面逐处处理）：
 * * `int(x)` 是向零截断 → `Math.trunc`；`//` 是向下取整 → `Math.floor`。
 * * `round(x, n)` 是银行家舍入 → `pyRound`。
 * * `s.get(k, d)` 只在键**不存在**时给 d（键存在但值为 None 时仍返回 None）→ `g(s,k,d)`。
 * * `s.get(k) or 0` 把 None/0/"" 都当假 → `n0(v)`。
 * * `k in s` 是字典键检查 → `hasOwn`。
 */

import { PyRandom } from "./rng.ts";
import { weeklyBill } from "./bill.ts";
import type {
  Card,
  Delayed,
  LineStage,
  MemClue,
  Option,
  Ota,
  Policy,
  State,
  StoryLine,
  World,
} from "./types.ts";

// ------------------------------------------------------------------ 小工具

const hasOwn = (o: any, k: string): boolean =>
  o != null && Object.prototype.hasOwnProperty.call(o, k);

/** Python `d.get(k, dflt)`：键不存在才给默认值。 */
function g<T = any>(o: any, k: string, dflt?: T): any {
  if (o == null) return dflt;
  return hasOwn(o, k) ? o[k] : dflt;
}

/** Python `v or 0`：None / undefined / 0 / "" / false 都归 0。 */
const n0 = (v: any): number => (v ? Number(v) : 0);

/** Python `int(x)`：向零截断。 */
const pyInt = (v: any): number => {
  const n = Number(v);
  return Number.isFinite(n) ? Math.trunc(n) : 0;
};

/**
 * Python `round(x, nd)`。
 *
 * Python 的 round 对 float 是「按这个 double 的精确十进制值」做舍入、.5 向偶。
 * 不能写成「先乘 10^nd 再用 Math.round」——`0.1949999999999999` 乘 100 会得到
 * `19.49999999999999`，看似正好在 .5 上，其实真实值低于 .5，Python 给 0.19、
 * 天真实现会给 0.20（这条错了整个 template 曲线差 0.01）。
 * 也不能用容差判 .5：容差会把「差 1e-14 的不等」误判成「相等」。
 * 这里把 double 拆成 尾数 × 2^指数 的精确有理数，再按 BigInt 做整数除法舍入。
 */
export function pyRound(x: number, nd = 0): number {
  if (!Number.isFinite(x)) return x;
  if (x === 0) return 0;
  const sign = x < 0 ? -1 : 1;
  const ax = Math.abs(x);

  // IEEE754 double → m * 2^e（精确）
  const buf = new DataView(new ArrayBuffer(8));
  buf.setFloat64(0, ax);
  const hi = buf.getUint32(0);
  const lo = buf.getUint32(4);
  const expBits = (hi >>> 20) & 0x7ff;
  let m = (BigInt(hi & 0xfffff) << 32n) | BigInt(lo);
  let e: number;
  if (expBits === 0) {
    e = -1074; // 次正规数
  } else {
    m |= 1n << 52n;
    e = expBits - 1075;
  }

  // 目标：round(m * 2^e * 10^nd)，.5 向偶
  const ten = 10n ** BigInt(Math.max(0, nd));
  let num = m * ten;
  let den = 1n;
  if (e >= 0) num <<= BigInt(e);
  else den <<= BigInt(-e);
  if (nd < 0) den *= 10n ** BigInt(-nd);

  let q = num / den;
  const r = num % den;
  const twice = r * 2n;
  if (twice > den) q += 1n;
  else if (twice === den && q % 2n === 1n) q += 1n; // 真正的中点才向偶

  // 除法本身是正确舍入的，所以这一步给出的就是离十进制值最近的那个 double
  return sign * (Number(q) / Math.pow(10, nd));
}

/** 按码点排序（对应 Python `sorted()` 对文件名）。 */
function cmpCodepoint(a: string, b: string): number {
  const ac = Array.from(a);
  const bc = Array.from(b);
  const n = Math.min(ac.length, bc.length);
  for (let i = 0; i < n; i++) {
    const x = ac[i].codePointAt(0)!;
    const y = bc[i].codePointAt(0)!;
    if (x !== y) return x - y;
  }
  return ac.length - bc.length;
}

// ------------------------------------------------------------------ 读取数据

/** `相对路径 -> 已解析的 JSON`。`cards/x.json`、`storylines/y.json`、`intro.json`… */
export type RawFiles = Record<string, any>;

let _FILES: RawFiles | null = null;

export function loadFiles(files: RawFiles): void {
  _FILES = files;
  _MEM = null;
}

function _load(name: string): any {
  const f = _FILES;
  if (!f) throw new Error("data not loaded: 先调 loadWorld(files) 或 loadFiles(files)");
  if (!hasOwn(f, name)) throw new Error(`data file not found: ${name}`);
  return f[name];
}

let _MEM: Record<string, MemClue> | null = null;

/** `ota_memory.json` 的线索表（key -> clue）。回考的真值要从 set 里抽。 */
export function memoryTable(): Record<string, MemClue> {
  if (_MEM === null) {
    _MEM = {};
    const clues = _load("ota_memory.json").clues ?? [];
    for (const c of clues) _MEM[c.key] = c;
  }
  return _MEM;
}

/**
 * 锁定这一个细节的「真值」：她这次说的是三选一里的哪一个。
 *
 * ota_memory 的 design_note 要求「值在本局锁定」——同一局反复回考必须问同一个，
 * 重开才重掷。
 */
function _pickTruth(rng: PyRandom, cid: string): string {
  const c = memoryTable()[cid] ?? {};
  const pool = [...(c.set ?? [])];
  return pool.length ? rng.choice(pool) : "";
}

/**
 * 取这条线索本局的真值；还没掷过就掷一次死。
 *
 * 「说」的那张卡正文里就写着「我想吃{truth}」——真值必须在显示那一刻就定下来。
 */
export function ensureTruth(s: State, cid: string, rng: PyRandom): string {
  if (!s._truth) s._truth = {};
  const tb = s._truth;
  if (!hasOwn(tb, cid)) tb[cid] = _pickTruth(rng, cid);
  return tb[cid];
}

/** 回考三选一的显示顺序：本局固定，跨局不同。 */
export function askOrder(s: State, cid: string, n: number, rng: PyRandom): number[] {
  if (!s._ask_order) s._ask_order = {};
  const ao = s._ask_order;
  if (!hasOwn(ao, cid) || ao[cid].length !== n) {
    const idx = Array.from({ length: n }, (_, i) => i);
    rng.shuffle(idx);
    ao[cid] = idx;
  }
  return ao[cid];
}

export function loadWorld(files?: RawFiles): World {
  if (files) loadFiles(files);
  const world: World = {
    cards: [],
    lines: [],
    intro: _load("intro.json"),
    endings: _load("endings.json"),
    memory: _load("ota_memory.json"),
    pool: _load("ota_pool.json"),
    names: _load("idol_names.json"),
  };
  const all = Object.keys(_FILES!);
  const cardFiles = all.filter((n) => n.startsWith("cards/") && n.endsWith(".json")).sort(cmpCodepoint);
  for (const fn of cardFiles) {
    const j = _load(fn);
    for (const c of j.cards ?? []) world.cards.push(c);
  }
  const lineFiles = all.filter((n) => n.startsWith("storylines/") && n.endsWith(".json")).sort(cmpCodepoint);
  for (const fn of lineFiles) world.lines.push(_load(fn));
  return world;
}

// ------------------------------------------------------------------ 状态

export const BASE: Record<string, number> = {
  money: 1800,
  stamina: 100,
  psyche: 70,
  fame: 5,
  enjou: 0,
  kaibox: 0,
  banzi: 0,
  shiroi: 0,
  shiren: 0,
  relation_A: 50,
  relation_B: 50,
  relation_C: 50,
};

export const STATE_KEYS = [
  "money",
  "stamina",
  "psyche",
  "fame",
  "stage",
  "dance",
  "sing",
  "mc",
  "enjou",
  "kaibox",
  "banzi",
  "shiroi",
  "shiren",
  "relation_A",
  "relation_B",
  "relation_C",
];

export function newState(
  world: World,
  _choice_id: string | null = null,
  name_style: string | null = null,
  _rng?: PyRandom,
): State {
  const intro = world.intro;
  const b = intro.base_state;
  const s: any = { ...BASE };
  s.money = b.money;
  s.stamina = b.stamina;
  s.psyche = b.psyche;
  s.fame = b.fame;
  s.dance = b.dance;
  s.sing = b.sing;
  s.mc = b.mc;
  s.relation_A = b.relation[0];
  s.relation_B = b.relation[1];
  s.relation_C = b.relation[2];

  s.ota = [];
  for (const seed of world.pool.seeds) {
    s.ota.push({
      id: seed.id,
      name: seed.name,
      stick: Number(seed.stickiness),
      archetype: seed.archetype,
      fan_type: seed.fan_type,
      gender: g(seed, "gender", "女"),
      risk: g(seed, "risk", 0.1),
      spend: pyInt(g(seed, "spend", 3)),
      weeks_known: 6,
    });
  }

  s.week = 1;
  s.weeks_total = pyInt(g(intro, "weeks_total", 8));
  s.beat = 0;
  s.flags = new Set<string>();
  s.delayed = [];
  s.cooldown = {};
  s.seen = [];
  s.log = [];
  s.chose_leave = false;
  s.last_live_choice = null;
  s.max_single = 0.0;
  s.template = 0.3;
  s.clues = {};
  s.clues_said = 0;
  s.story = {};
  s.name = null;
  s.name_style = name_style;
  s.ended = null;
  s.okawari = [];
  s.acting = null;
  return s as State;
}

export function clamp(s: State): State {
  s.psyche = softCapPsyche(s.psyche);
  // 断联之后那一段，炎上和板子不归这套数管了：它要涨到 999。
  const runaway = Boolean(s._collapse) || (s.flags?.has("final_collapse") ?? false);
  for (const k of ["stamina", "psyche", "enjou", "shiroi", "kaibox", "banzi"]) {
    if (runaway && (k === "enjou" || k === "banzi")) {
      s[k] = Math.max(0, s[k]);
      continue;
    }
    s[k] = Math.max(0, Math.min(100, s[k]));
  }
  for (const k of ["dance", "sing", "mc"]) {
    s[k] = Math.max(0, Math.min(SKILL_CAP, s[k]));
  }
  for (const k of [
    "bold",
    "kuyang_count",
    "heat",
    "heart",
    "zhong",
    "zhongs",
    "gorshou",
    "true_talk",
    "clues_said",
    "low_income_weeks",
    "max_single",
  ]) {
    if (hasOwn(s, k) && typeof s[k] === "number") {
      s[k] = Math.max(0, s[k]);
    }
  }
  for (const o of s.ota) {
    o.stick = Math.max(0.0, Math.min(100.0, o.stick));
  }
  return s;
}

// ------------------------------------------------------------------ 派生量

/** 我这一季练成了什么。体力不在这里：它是「这一场还剩多少力气」。 */
export function stageScore(s: State): number {
  const relavgV = (s.relation_A + s.relation_B + s.relation_C) / 3;
  return 0.32 * s.dance + 0.28 * s.sing + 0.22 * s.mc + 0.18 * relavgV;
}

export function relavg(s: State): number {
  return (s.relation_A + s.relation_B + s.relation_C) / 3;
}

/** 补几个「算出来的量」：剧情线闸门会读「舞台」，但 state 里从来没有这个键。 */
function _derive(s: State): void {
  if (!s.stage) {
    try {
      s.stage = pyRound(stageScore(s), 1);
    } catch {
      s.stage = 0;
    }
  }
}

export function stickValues(s: State): number[] {
  return s.ota.map((o) => o.stick);
}

export function maxShare(s: State): number {
  const vs = stickValues(s);
  const t = vs.reduce((a, b) => a + b, 0) || 1.0;
  return Math.max(...vs) / t;
}

// ------------------------------------------------------------------ OTA 槽

/** 按 casting.select 选一个当前在场的 OTA；选不到返回 null。 */
export function pickOta(s: State, sel?: Record<string, any> | null, rng?: PyRandom): Ota | null {
  sel = sel ?? {};
  const cand: Ota[] = [];
  for (const o of s.ota) {
    // 剧情对象不跑龙套：她只在自己那条线里出现
    if (o.is_storyline) continue;
    if ("archetype" in sel && o.archetype !== sel.archetype) continue;
    if ("fan_type" in sel && o.fan_type !== sel.fan_type) continue;
    if ("gender" in sel && o.gender !== sel.gender) continue;
    if (o.stick < n0(g(sel, "min_stickiness", 0))) continue;
    cand.push(o);
  }
  if (!cand.length) return null;
  const weights = cand.map((o) => Math.max(1.0, o.stick));
  return rng!.choices(cand, weights, 1)[0];
}

/** 给一个 casting.select，找出能拿来孵化的原型。 */
function _matchArchetype(pool: any, sel: Record<string, any>): any {
  const archs = pool.archetypes ?? [];
  const want = sel.archetype;
  if (want) {
    for (const a of archs) if (a.id === want) return a;
  }
  const ft = sel.fan_type;
  if (ft) {
    for (const a of archs) if ((a.fan_types ?? []).includes(ft)) return a;
  }
  const gd = sel.gender;
  if (gd && archs.length) {
    const tag = gd === "女" ? "女友粉" : gd === "男" ? "男友粉" : "";
    if (tag) {
      const poolG = archs.filter((a: any) => (a.fan_types ?? []).includes(tag));
      if (poolG.length) return poolG[0];
    }
  }
  if (sel.any_archetype && archs.length) return archs[0];
  if (!want && !ft) return null;
  return null;
}

function _genderFor(arch: any, rng: PyRandom): string {
  const fts = arch.fan_types ?? [];
  if (fts.includes("女友粉") && !fts.includes("男友粉")) return "女";
  if (fts.includes("男友粉") && !fts.includes("女友粉")) return "男";
  return rng.choice(["女", "女", "男"]);
}

/**
 * 生一个新 OTA：她第一次出现。一季最多 hatch_max 个
 * （「带朋友来」这种剧情触发的可以 ignore_cap=true 绕过）。
 */
export function hatch(
  s: State,
  world: World | null,
  sel: Record<string, any> | null,
  rng: PyRandom,
  ignore_cap = false,
  base_stick?: number | null,
): Ota | null {
  sel = sel ?? {};
  const pool = world?.pool ?? (world as any)?.ota_pool ?? {};
  if (!ignore_cap && n0(g(s, "hatch_n", 0)) >= n0(g(s, "hatch_max", 3))) return null;
  const arch = _matchArchetype(pool, sel);
  if (arch == null) return null;
  const gender = sel.gender ?? _genderFor(arch, rng);
  const used = new Set(s.ota.map((o) => o.name));
  const names: string[] = ((pool.name_pools ?? {})[gender] ?? []).filter((n: string) => !used.has(n));
  if (!names.length) return null;
  const name = rng.choice(names);
  const fts: string[] = arch.fan_types ?? [];
  const ft = sel.fan_type && fts.includes(sel.fan_type) ? sel.fan_type : fts.length ? fts[0] : "事业粉";
  const base = Number(g(arch, "base_stickiness", 60));
  const need = Number(n0(g(sel, "min_stickiness", 0)));
  let stick = need ? Math.min(need, base) : base;
  if (base_stick != null) stick = Number(base_stick);
  stick = Math.max(0.0, Math.min(100.0, stick));
  const o: any = {
    id: `hatch_${n0(g(s, "hatch_n", 0)) + 1}`,
    name,
    gender,
    fan_type: ft,
    archetype: arch.id,
    spend: pyInt(g(arch, "base_spend", 3)),
    stick,
    weeks_known: 1,
    is_seed: false,
    met_week: s.week,
    notes: sel.notes ?? "第一次来。",
  };
  s.ota.push(o);
  s.hatch_n = n0(g(s, "hatch_n", 0)) + 1;
  if (!s.hatched) s.hatched = [];
  s.hatched.push(name);
  return o;
}

/** 给这一季的私联对象掷一套「她自己的细节」（kind=choice 的项）。 */
function _protaPreset(mem_def: any, rng: PyRandom): Record<string, string> {
  const out: Record<string, string> = {};
  for (const [key, item] of Object.entries(mem_def ?? {})) {
    if ((item as any)?.kind !== "choice") continue;
    const pool = [...((item as any)?.pool ?? [])];
    if (pool.length) out[key] = rng.choice(pool);
  }
  return out;
}

/**
 * 这一季的专属私联对象：第一次上场前生成，之后整季都是她。
 *
 * 同时作为 is_storyline 的 OTA 挂进 s.ota（这样 ota_all 一类效果也落在她身上），
 * 但 pick_ota 会跳过 is_storyline，她不会跑去别的卡里串场。
 */
export function protagonist(s: State, world: World, rng: PyRandom): Ota | null {
  const p0 = s._prota;
  if (p0) return p0;
  const ln: any = shirenLine(world) ?? {};
  const mem_def = ln.memory_key ?? {};
  const pool = world.pool ?? {};
  const archs = pool.archetypes ?? [];
  if (!archs.length) return null;
  const arch: any = rng.choice(archs);
  const gender = _genderFor(arch, rng);
  const used = new Set((s.ota ?? []).map((o) => o.name));
  let names: string[] = ((pool.name_pools ?? {})[gender] ?? []).filter((n: string) => !used.has(n));
  if (!names.length) {
    names = ((pool.name_pools ?? {})["其他"] ?? []).filter((n: string) => !used.has(n));
  }
  if (!names.length) return null;
  const fts: string[] = arch.fan_types ?? [];
  const p: any = {
    id: "shiren_prota",
    name: rng.choice(names),
    gender,
    fan_type: fts.length ? fts[0] : "女友粉",
    archetype: arch.id,
    spend: pyInt(g(arch, "base_spend", 3)),
    // 越线门槛是「某个 OTA 黏性 ≥ 75」，她就是那个 75
    stick: 75.0,
    weeks_known: Math.max(2, pyInt(n0(g(s, "week", 1)))),
    is_seed: false,
    is_storyline: true,
    met_week: g(s, "week", 1),
    notes: "私下里认识的那个人。",
    memory: _protaPreset(mem_def, rng),
  };
  s._prota = p;
  if (!s.ota) s.ota = [];
  s.ota.push(p);
  return p;
}

/** 她这一季被记住的那些细节：{key: 值}。剧情文案拿它填占位符。 */
export function protaMemory(s: State): Record<string, string> {
  const p = s._prota ?? {};
  return p.memory ?? {};
}

/** 剧情选项的 `learns`：这一拍她讲出来的事，从此算「你知道」。 */
export function learnMemory(s: State, keys: string | string[] | null, text = ""): string[] {
  const p = s._prota;
  if (!p) return [];
  if (typeof keys === "string") keys = [keys];
  if (!p.memory) p.memory = {};
  const mem = p.memory;
  const got: string[] = [];
  for (const k of keys ?? []) {
    if (!k || hasOwn(mem, k)) continue;
    mem[k] = text || "";
    got.push(k);
  }
  return got;
}

/**
 * 剧情线选完之后的「后果」：那些只在数据里出现过、从来没人读的旗标。
 * 以前 cut_early / deleted_ta / denied / double_life 只会进 flags 这个集合，
 * 进完就算了——玩家选「当晚就跟她说以后别来了」，线照样往下走。
 */
export function applyStoryFlags(s: State, option: Option): void {
  const fl = option.flags ?? [];
  if (!fl.length) return;
  const got = new Set(fl);
  // 真的断线：这两条是「主动结束」，不是「这一拍没踩准」。
  if (got.has("cut_early") || got.has("deleted_ta")) s.flags.add("line_closed");
  if (got.has("knows_home")) s.kaibox = Number(n0(g(s, "kaibox", 0))) + 8;
  if (got.has("met_at_night")) s.kaibox = Number(n0(g(s, "kaibox", 0))) + 5;
  if (got.has("official_denial")) {
    s.banzi = Number(n0(g(s, "banzi", 0))) + 6;
    s.enjou = Number(n0(g(s, "enjou", 0))) + 5;
  }
  if (got.has("double_life")) s.psyche = Number(n0(g(s, "psyche", 0))) - 6;
  if (got.has("manager_leverage")) {
    s.fame = Number(n0(g(s, "fame", 0))) - 3;
    s.psyche = Number(n0(g(s, "psyche", 0))) - 3;
  }
  if (got.has("team_knows")) {
    s.relation_C = Number(n0(g(s, "relation_C", 0))) + 4;
    s._team_knows = pyInt(n0(g(s, "_team_knows", 0))) + 1;
  }
  if (got.has("denied")) {
    s.psyche = Number(n0(g(s, "psyche", 0))) - 4;
    s.relation_A = Number(n0(g(s, "relation_A", 0))) - 4;
  }
  if (got.has("dodged")) s.psyche = Number(n0(g(s, "psyche", 0))) - 3;
  if (got.has("promised_exclusive")) {
    s.psyche = Number(n0(g(s, "psyche", 0))) + 4;
    s.kaibox = Number(n0(g(s, "kaibox", 0))) + 6;
  }
  if (got.has("promised_offduty")) s.kaibox = Number(n0(g(s, "kaibox", 0))) + 6;
  if (got.has("promised_remember")) s.psyche = Number(n0(g(s, "psyche", 0))) + 3;
  if (got.has("refused_promise")) {
    s.psyche = Number(n0(g(s, "psyche", 0))) - 5;
    s.relation_A = Number(n0(g(s, "relation_A", 0))) - 3;
  }
  clamp(s);
}

/** 这张卡是不是「必须是个生面孔」：casting 里有 hatch_only 的槽。 */
export function wantsNewFace(card: Card): boolean {
  for (const cs of card.casting ?? []) {
    if (cs.hatch_only) return true;
  }
  return false;
}

/**
 * 执行一张卡的 casting，返回 slot -> ota 的映射。
 *
 * 2026-11-15：allow_hatch 只表示「找不到人可以生一个来顶」，force_hatch 才是
 * 「这张卡就是新人卡」；hatch_only 是 force_hatch 的严格版，**不先去现有 OTA 里找**。
 */
export function cast(
  s: State,
  card: Card,
  rng: PyRandom,
  world?: World | null,
): Record<string, Ota> | null {
  const out: Record<string, Ota> = {};
  for (const cs of card.casting ?? []) {
    const slot = cs.slot as string;
    let o: Ota | null;
    if (cs.hatch_only) o = null;
    else o = pickOta(s, cs.select, rng);
    if (o == null) {
      if (!(cs.force_hatch || cs.hatch_only)) return null; // 这个卡要求的人不在场
      if (world != null) o = hatch(s, world, cs.select ?? null, rng);
    }
    if (o == null) return null; // 新生儿也没生成出来（名额满了/没名字了）
    out[slot] = o;
  }
  return out;
}

// ------------------------------------------------------------------ 效果应用

/**
 * 「这件事会不会被外人看见」：卡面上没写，但它是整个游戏的重量所在。
 * Python 侧同样只定义未直接引用（判定走 `_seethe_cost` 里的显式分支），
 * 这里是按原样搬的，导出以免 lint 误报。
 */
export const BOLD_AXES = ["开盒", "板子", "炎上"];

/** 结局层要认的「这次是不是站到了台上」 */
const STAGE_TYPES = [
  "positive",
  "舞台事故",
  "外部舆论",
  "私生",
  "私生跟踪",
  "团内",
  "团内关系",
  "外部",
];

/**
 * 选项被看见的代价（内账，不进 immediate）。
 * - option.bold 是显式标记：开盒 / 板子 / 炎上，每标记一次记一次。
 * - 卡面文案里明写着「发到超话 / 公开 / 被拍到」的选项，也算一次被看见。
 * - 「欠人情」这类选项每做一次，就把一段关系往死里推一格。
 */
function _seetheCost(
  s: State,
  option: Option,
  card_type?: string | null,
  slots?: Record<string, Ota> | null,
): void {
  const kind = option.bold;
  if (kind) {
    s.bold = n0(g(s, "bold", 0)) + 1;
    if (kind === "开盒") s.kaibox = n0(g(s, "kaibox", 0)) + 4;
    else if (kind === "板子") s.banzi = n0(g(s, "banzi", 0)) + 4;
    else if (kind === "炎上") s.enjou = n0(g(s, "enjou", 0)) + 4;
  } else {
    const blob = ["id", "label", "desc", "note"]
      .map((k) => String(g(option, k, "") ?? ""))
      .join(" ");
    const words = ["公开", "发出去", "超话", "发到", "说出去", "写上", "发帖", "群里", "录下来", "被拍到"];
    if (words.some((w) => blob.includes(w))) {
      s.bold = pyInt(n0(g(s, "bold", 0))) + 1;
      // 话说出去会被截图，但「一句话」不是「一张照片」。卡类型决定分量。
      const heavy =
        card_type != null &&
        ["外部", "外部舆论", "舞台事故", "positive"].includes(card_type);
      s.banzi = Number(n0(g(s, "banzi", 0))) + (heavy ? 0.2 : 0.0);
    }
  }
  // 卡库的数额太小，撑不起「关系坏掉」这种一整季的走势：选了就走远 10 点
  for (const f of option.flags ?? []) {
    if (f === "crossed_line") {
      s.kuyang_count = n0(g(s, "kuyang_count", 0)) + 1;
      for (const r of ["relation_A", "relation_B", "relation_C"]) s[r] -= 10;
    } else if (f === "owe_team") {
      s.owe_team = pyInt(n0(g(s, "owe_team", 0))) + 1;
    } else if (f === "work_only" || f === "zhong_boundary") {
      s.relation_B = n0(g(s, "relation_B", 50)) - 10;
    } else if (f === "met_alone") {
      // 私下见过面：这才是「私联了几个人」真正数到的程度。
      s.met_alone_n = n0(g(s, "met_alone_n", 0)) + 1;
      s.kaibox = n0(g(s, "kaibox", 0)) + 5;
      // 数「人」不数「次数」：同一个人见了三次，是一段关系，不是三个人
      let who = "";
      for (const v of Object.values(slots ?? {})) {
        if (v && typeof v === "object" && (v as Ota).id) {
          who = (v as Ota).id;
          break;
        }
      }
      if (!who) {
        who = String(s._chaser ?? "") || who;
        if (!who) who = "line|" + String(g(option, "id", ""));
      }
      if (!s._met_people) s._met_people = new Set<string>();
      if (!s._met_people.has(who)) {
        s._met_people.add(who);
        s.shiren = n0(g(s, "shiren", 0)) + 1;
      }
    }
  }
  for (const [axis, key] of [
    ["开盒", "kaibox"],
    ["板子", "banzi"],
    ["炎上", "enjou"],
  ]) {
    const v = g(option, axis);
    if (typeof v === "number") s[key] = n0(g(s, key, 0)) + v;
  }
  // 舞台上那一下：卡库用 stage 写「这一场唱得更好/更差」，本季累计进 gorshou
  const v2 = g(option.immediate ?? {}, "stage");
  if (typeof v2 === "number" && card_type != null && STAGE_TYPES.includes(card_type)) {
    s.gorshou = n0(g(s, "gorshou", 0)) + v2;
  }
}

/**
 * 事件的放大系数：卡库写的是「一张卡的数额」（1~6 点），
 * 但它代表的是「这一周发生了什么」。不放大，整季下来炎上到不了 20。
 */
export class EventMult {
  static MULT: Record<string, number> = {
    enjou: 2.5,
    kaibox: 1.2,
    banzi: 2.5,
    shiroi: 2.0,
    psyche: 1.4,
    stamina: 1.2,
    fame: 1.5,
  };

  static apply(s: State, eff: Record<string, any> | null): void {
    for (const k of ["enjou", "kaibox", "banzi"]) {
      const v = g(eff ?? {}, k);
      if (typeof v === "number" && hasOwn(s, k)) {
        s[k] = n0(g(s, k, 0)) + v * (EventMult.MULT[k] - 1);
      }
    }
  }
}

/** 关系往坏处掉得比往好处涨快：一次伤人的话，比十次好话记得久。 */
function _rel(v: number): number {
  return v * (v < 0 ? 1.6 : 1.0);
}

export const FAME_CAP = 80.0; // 人气硬上限：地下场子就那么大
export const FAME_SOFT = 40.0; // 过了这条线，新增的人气只算三分之一

/**
 * 给人气加/减一点，返回实际变动量。
 * 软上限只压「这一帧新增的那一截」，绝不回缩存量。
 */
export function addFame(s: State, delta: number): number {
  const cur = Number(n0(g(s, "fame", 0)));
  if (delta <= 0) {
    s.fame = Math.max(0.0, cur + delta);
  } else if (cur >= FAME_SOFT) {
    s.fame = Math.min(FAME_CAP, cur + delta / 3.0);
  } else if (cur + delta > FAME_SOFT) {
    s.fame = Math.min(FAME_CAP, FAME_SOFT + (cur + delta - FAME_SOFT) / 3.0);
  } else {
    s.fame = Math.min(FAME_CAP, cur + delta);
  }
  return s.fame - cur;
}

export function applyEffect(
  s: State,
  eff: Record<string, any> | null,
  slots?: Record<string, Ota> | null,
  card?: Card | null,
): void {
  slots = slots ?? {};
  for (const [k, v] of Object.entries(eff ?? {})) {
    if (k.startsWith("@")) {
      const o = slots[k.slice(1)];
      if (o == null) continue;
      if (k === "@speaker") o.stick += Number(v) * 1.0;
      continue;
    }
    if (k === "ota_all") {
      for (const o of s.ota) o.stick += Number(v) * 0.5;
      if (Number(v) > 0) addFame(s, Number(v) * 0.6);
      continue;
    }
    if (k === "fame" && typeof v === "number") {
      addFame(s, v * g(EventMult.MULT, "fame", 1.0));
      continue;
    }
    if (k === "relation_all") {
      for (const r of ["relation_A", "relation_B", "relation_C"]) s[r] += _rel(Number(v));
      continue;
    }
    if (["relation_A", "relation_B", "relation_C"].includes(k) && typeof v === "number") {
      s[k] += _rel(v);
    } else if (hasOwn(s, k) && typeof s[k] === "number" && k !== "psyche") {
      let m = g(EventMult.MULT, k, 1.0) as number;
      // 环境卡是「渐渐积累」的量，不该跟一次性事件卡用同一个倍率
      if (card?.type === "ambient" && ["banzi", "enjou", "kaibox"].includes(k)) m = 1.0;
      s[k] += Number(v) * m;
    } else if (k === "psyche") {
      // 卡上的心理收益打六折再按事件放大
      s[k] += Number(v) * 0.6 * EventMult.MULT["psyche"];
    } else if (typeof v === "number") {
      s[k] = n0(g(s, k, 0)) + v; // zhong / zhongs 这类剧情线专属量：按需建键
    }
  }
  if (n0(g(s, "template", 0)) >= 0.8) s.psyche -= 2; // 一直说同一套话，心里会空
  clamp(s);
  s.stage = stageScore(s);
}

/** 二周目开局姿态：只加一点起始倾向，不锁任何线或结局。 */
export function applyStance(s: State, stance: any): void {
  if (!stance) return;
  const sid = stance.id ?? "";
  for (const [k, v] of Object.entries(stance.bonus ?? {})) {
    if (k === "relation_all") {
      for (const r of ["relation_A", "relation_B", "relation_C"]) s[r] = n0(g(s, r, 50)) + Number(v);
    } else if (k === "ota_all") {
      for (const o of s.ota) o.stick = n0(g(o, "stick", 50)) + Number(v);
    } else if (["psyche", "money", "dance", "sing", "mc"].includes(k)) {
      s[k] = n0(g(s, k, 0)) + Number(v);
    } else if (typeof v === "number") {
      s[k] = n0(g(s, k, 0)) + v;
    }
  }
  if (sid && sid !== "none") {
    s.stance = sid;
    s.stance_name = stance.name ?? sid;
  }
  clamp(s);
  s.stage = stageScore(s);
}

/** 应用一个选项：立即效果、flag、延迟、线索。返回事件描述列表。 */
export function applyOption(
  s: State,
  option: Option,
  rng: PyRandom,
  slots?: Record<string, Ota> | null,
  card?: Card | null,
): any[][] {
  const ev: any[][] = [];
  applyEffect(s, option.immediate ?? null, slots);
  // 选项自重：一张卡上「有人看到我」的代价是固定的，跟文案写多少点无关。
  _seetheCost(s, option, card?.type ?? null, slots);
  const fl = option.flags ?? [];
  for (const f of fl) s.flags.add(f);
  // 「真话率」只数带语气标记的选项。必须放在 flag 循环外——一个选项可能挂多个 flag。
  const tone = option.tone;
  if (tone === "truth") {
    s.truth_pick = pyInt(n0(g(s, "truth_pick", 0))) + 1;
    s.true_talk = pyInt(n0(g(s, "true_talk", 0))) + 1;
  } else if (tone === "safe") {
    s.safe_pick = pyInt(n0(g(s, "safe_pick", 0))) + 1;
  }
  if (fl.length) ev.push(["flag", fl.join(",")]);
  for (const dl of option.delayed ?? []) {
    const rec: Delayed = {
      when: g(dl, "when", null),
      cond: g(dl, "condition", null),
      effect: g(dl, "effect", null),
      note: g(dl, "note", null),
      slots: {},
    };
    for (const [k, v] of Object.entries(slots ?? {})) {
      if (v && (v as Ota).id) rec.slots[k] = (v as Ota).id;
    }
    for (const extra_key of ["hatch_friend", "base_stick"]) {
      if (g(dl, extra_key) != null) (rec as any)[extra_key] = g(dl, extra_key);
    }
    s.delayed.push(rec);
  }
  if (fl.length) {
    if (!s._fired) s._fired = new Set<string>();
    for (const f of fl) s._fired.add(f);
  }
  // 回考：锁定真值 / 用三选一
  if (option.rq_lock) {
    let cid: string | null = null;
    const rl = option.rq_lock;
    if (typeof rl === "object" && rl !== null) cid = rl.clue ?? null;
    if (cid && !hasOwn(s.clues, cid) && s.clues_said < n0(g(s, "max_clues", 6))) {
      s.clues[cid] = {
        state: "said",
        asked: false,
        said_week: s.week,
        who: null,
        // 用 ensure_truth 而不是再掷一次：她说那句话的时候真值就已经定了
        truth: ensureTruth(s, cid, rng),
      };
      s.clues_said += 1;
      ev.push(["clue_said", cid]);
    }
  }
  if (option.rq_drop || fl.includes("zhong_boundary")) {
    // 岔开话题 / 把她挡在门外（重线安静两周）
    lineCool(s, "zhong", 2);
  }
  if (option.rq_drop) {
    for (const [cid, info] of Object.entries(s.clues)) {
      if (info.state === "said") {
        info.state = "dropped";
        s.clues_said = Math.max(0, s.clues_said - 1);
        ev.push(["clue_dropped", cid]);
      }
    }
  }
  if (option.rq_pick) {
    const pick = option.rq_pick;
    const cid = pick.clue;
    // 答对与否只看「这一项是不是本局锁定的那个词」
    const truth = ensureTruth(s, cid, rng);
    const correct = Boolean(truth) && (option.label ?? "").trim() === truth;
    const who = pick.slot ?? "speaker";
    // 卡面 immediate 已经带了一次 @speaker 的加减，这里补齐「记住/忘掉」的余量
    const o = (slots ?? {})[who];
    if (o != null) {
      o.stick = Math.max(0.0, Math.min(100.0, o.stick + (correct ? 4 : -6)));
    }
    const info = (s.clues ?? {})[cid];
    if (info != null) {
      info.asked = true;
      info.state = correct ? "known" : "wrong";
      info.result = correct ? "ok" : "bad";
    }
    if (!s.rq_log) s.rq_log = [];
    s.rq_log.push({ clue: cid, ok: correct, week: s.week });
    if (correct) s.recall_ok = pyInt(n0(g(s, "recall_ok", 0))) + 1;
    ev.push(["rq", correct ? "ok" : "bad", cid]);
  }
  return ev;
}

// ------------------------------------------------------------------ gate 表达式

const _NUM: Record<string, string> = {
  钱: "money",
  体力: "stamina",
  心理: "psyche",
  人气: "fame",
  炎上: "enjou",
  开盒: "kaibox",
  板子关注度: "banzi",
  板子: "banzi",
  私生: "shiroi",
  私联人数: "shiren",
  // 「下次体力」是卡面里的写法，指的仍是 stamina
  下次体力: "stamina",
  队友关系均值: "relavg",
  zhongs: "zhongs",
  周: "week",
  认识周数: "weeks_known",
  阿棠关系: "relation_A",
  露露关系: "relation_B",
  小满关系: "relation_C",
  舞台: "stage",
  重线进度: "zhong",
  heat: "heat",
  热: "heat",
  心动: "relation_A",
  heart: "heart",
};

/** 从文本里抠出比较符与数值，如 '≥ 45' -> ('≥', 45.0) */
function _cmp(t: string): [string | null, number] {
  const m = /(≥|≤|=|>|<)\s*([\d.]+)/.exec(t);
  return m ? [m[1], parseFloat(m[2])] : [null, 0.0];
}

export function evalClause(s: State, textIn: string): boolean {
  let text = (textIn ?? "").trim();
  if (!text || text === "无") return true;
  if (text === "手头紧") return s.money < 800;
  if (text === "有一点余钱") return s.money >= 500;
  if (text === "不足两周房租") return s.money < 1200;
  // 这几种「曾经发生过」的状态，引擎其实一直在记，别再当 False
  if (["曾冷场或翻车", "曾冷场", "翻车", "舞台翻车"].includes(text)) {
    return pyInt(n0(g(s, "blew_it", 0))) >= 1;
  }
  if (text === "曾欠队友人情") return pyInt(n0(g(s, "owe_team", 0))) >= 1;
  if (
    s.flags.has(text) ||
    ["crossed_line", "romance_started", "final_cautioned", "final_intimate", "played_safe"].includes(text)
  ) {
    return s.flags.has(text);
  }
  if (text.includes("本周已选")) {
    // 书名号有没有都认；中文动作名映射到 do_act 落库的 id（s.acted 存的是 id）
    const m = /『(.+?)』/.exec(text);
    let name = m ? m[1] : text.split("本周已选").join("").replace(/^[\s　（）()]+|[\s　（）()]+$/g, "");
    const alias: Record<string, string> = {
      练舞: "dance",
      练唱: "sing",
      练营业: "mc",
      练话术: "mc",
      拍内容: "content",
      拍内容发微博: "content",
      开直播: "work",
      直播: "work",
      打工: "work",
      躺: "rest",
    };
    return g(s, "acted", undefined) === (alias[name] ?? name);
  }
  // 资源别名（「钱」vs「money」、「开盒风险」vs「kaibox」等）
  for (const [cn, en] of [
    ["开盒风险", "开盒"],
    ["私生跟踪", "私生"],
    ["舞台稳定", "舞台"],
    ["板子关注度", "板子"],
  ]) {
    text = text.split(cn).join(en);
  }
  // 剧本里同义不同写法：OTA黏性/OTA 黏性、私生跟踪/私生、舞台稳定/舞台
  let t = text.split("私生跟踪").join("私生").split("舞台稳定").join("舞台").split("开盒风险").join("开盒");
  t = t.replace(/\s*OTA\s*黏性/g, " OTA黏性 ").split("OTA黏性").join("@OTA");
  t = t.replace(/\s+/g, " ").trim();
  if (/^任一.*@OTA/.test(t)) {
    const kind = t.split("任一").join("").split("@OTA")[0].trim();
    const [op, val] = _cmp(t);
    if (op == null) return false;
    let pool = s.ota;
    if (kind === "女友粉") pool = pool.filter((o) => o.fan_type === "女友粉");
    else if (kind === "男性") pool = pool.filter((o) => o.gender === "男");
    else if (kind) return false;
    if (!pool.length) return false;
    const best = Math.max(...pool.map((o) => o.stick));
    return op.includes("≥") || op.includes(">") ? best >= val : best <= val;
  }
  const m = /^(.+?)\s*(≥|≤|=|>|<)\s*([\d.]+)$/.exec(t);
  if (m) {
    const key = _NUM[m[1].trim()];
    if (key === undefined) return false;
    let cur: number;
    if (key === "weeks_known") {
      cur = Math.min(...(s.ota.length ? s.ota.map((o) => o.weeks_known) : [6]));
    } else if (key === "shiren") {
      cur = s.shiren;
    } else if (key === "stage") {
      cur = stageScore(s);
    } else if (key === "relavg") {
      cur = relavg(s);
    } else {
      cur = Number(n0(g(s, key, 0)));
    }
    const val = parseFloat(m[3]);
    const op = m[2];
    if (op === "=") return Math.abs(cur - val) < 1e-6;
    return op === "≥" || op === ">" ? cur >= val : cur <= val;
  }
  return false;
}

/** 支持：无 / 单条 / 「A 且 B」/「A 或 B」/ 带中文括号注释 / 不带空格的比较。 */
export function evalGate(s: State, gate?: string | null): boolean {
  if (!gate) return true;
  const g2 = gate.replace(/（[^）]*）/g, "");
  if (g2.includes("且")) return g2.split("且").every((x) => evalClause(s, x));
  if (g2.includes("或")) return g2.split("或").some((x) => evalClause(s, x));
  return evalClause(s, g2);
}

// ------------------------------------------------------------------ 抽卡

/**
 * 回考两张卡的先后关系：没听过的事不能考，听过的事不用再「第一次听说」。
 */
function _rqReady(s: State, c: Card): boolean {
  const rq = g(c._meta ?? {}, "rq_stage");
  if (!rq) return true;
  const cid = g(c._meta ?? {}, "clue");
  const info = (s.clues ?? {})[cid];
  if (rq === "ask") {
    // 只有「说过了、还没考过」的细节才考
    return Boolean(info) && info.state === "said" && !info.asked;
  }
  if (rq === "say") {
    // 已经听过（锁定过 / 考过 / 岔开）的，不再重演「第一次跟我说」
    return !info;
  }
  return true;
}

/**
 * 「她说过的那些小事」攒得太少，收场就只剩一道题。
 * 按还差几条补权重：越到季末、缺得越多，就越该让她的日常占掉一个位置。
 */
function _memoryBoost(s: State): number {
  const total = pyInt(n0(g(s, "weeks_total", 8)));
  const left = total - pyInt(n0(g(s, "week", 1)));
  if (left <= 0) return TYPE_WEIGHT["OTA记忆"];
  const have = finaleCluePool(s).length;
  const want = 5; // 收场要 3 道题，留两条余量
  const gap = want - have;
  if (gap <= 0) return TYPE_WEIGHT["OTA记忆"];
  return Math.min(1.1, TYPE_WEIGHT["OTA记忆"] + 0.32 * gap);
}

/**
 * 二周目姿态的抽卡偏向：只把「这张卡最像哪条线」算出来，匹配就 ×1.3。
 * 一周目 s.stance 为空，返回值恒 1.0，分布不变。
 */
export function stanceWeight(s: State, c: Card): number {
  const st = s.stance;
  if (!st) return 1.0;
  const aff: Record<string, number> = { stage: 0.0, money: 0.0, self: 0.0, bond: 0.0 };
  for (const o of c.options ?? []) {
    if (o.tone === "truth") aff.self += 3;
    const effs: any[] = [o.immediate ?? {}, o.effect ?? {}];
    for (const dl of o.delayed ?? []) effs.push(dl.effect ?? {});
    for (const eff of effs) {
      if (!eff || typeof eff !== "object") continue;
      for (const [k, v] of Object.entries(eff)) {
        if (typeof v !== "number" || v <= 0) continue;
        if (["dance", "sing", "mc", "stage"].includes(k)) aff.stage += v;
        else if (k === "money" || k === "fame") aff.money += v;
        else if (k === "psyche") aff.self += v;
        else if (
          k === "relation_all" ||
          k.startsWith("relation_") ||
          k.startsWith("@") ||
          k.startsWith("ota") ||
          k === "heart" ||
          k === "zhong"
        )
          aff.bond += v;
      }
    }
  }
  let best = "stage";
  for (const k of Object.keys(aff)) if (aff[k] > aff[best]) best = k;
  if (aff[best] <= 0) return 1.0;
  return best === st ? 1.3 : 1.0;
}

/** 三层抽卡：硬闸门 → 权重 → cooldown。kind 过滤单个 type，kinds 过滤一组。 */
export function draw(
  s: State,
  world: World,
  rng: PyRandom,
  kind?: string | null,
  pool_ids?: Set<string> | null,
  kinds?: string[] | null,
): Card | null {
  const cands: Card[] = [];
  for (const c of world.cards) {
    if (kind && c.type !== kind) continue;
    if (kinds && !kinds.includes(c.type)) continue;
    if (pool_ids != null && !pool_ids.has(c.id)) continue;
    if (n0(g(s.cooldown, c.id, 0)) > 0) continue;
    if (!_rqReady(s, c)) continue;
    if (!evalGate(s, c.gate)) continue;
    cands.push(c);
  }
  if (!cands.length) return null;
  const mem_w = _memoryBoost(s);
  // 这一季已经上过屏的卡降权（不硬禁）
  const seen = new Set(s.seen ?? []);
  const weights = cands.map((c) => {
    const w = Math.max(0.05, Number(g(c, "weight", 1.0)));
    const tw = c.type === "OTA记忆" ? mem_w : g(TYPE_WEIGHT, c.type, 1.0);
    return w * tw * (seen.has(c.id) ? 0.25 : 1.0) * stanceWeight(s, c);
  });
  return rng.choices(cands, weights, 1)[0];
}

export const TYPE_WEIGHT: Record<string, number> = {
  OTA记忆: 0.15,
  OTA相处的瞬间: 0.6,
  ambient: 0.35,
  日常: 2.0,
  团内: 1.6,
  团内关系: 1.3,
  外部: 1.4,
  外部舆论: 1.2,
  私生: 0.8,
  私生跟踪: 1.0,
  private: 1.0,
  positive: 0.35,
  舞台事故: 1.0,
  私联恋爱: 1.0,
  OTA互动: 1.0,
};

export const OTA_TYPES = ["OTA互动", "OTA记忆", "私联恋爱", "私生"];

function _isOtaCard(c: Card): boolean {
  return OTA_TYPES.includes(c.type);
}

/** 周末谁会来：黏性越高越可能到场；黏性低到 30 以下的人直接不再来。 */
export function warmOta(s: State): Ota[] {
  const pool: Ota[] = [];
  const wts: number[] = [];
  for (const o of s.ota) {
    let p = Math.max(0.0, (o.stick - 30) / 55.0);
    p = Math.min(p, 0.95);
    if (p <= 0) continue;
    pool.push(o);
    wts.push(p);
  }
  if (!pool.length) return [];
  const n = s.fame >= 40 ? 3 : s.fame >= 20 ? 2 : 1;
  const out: Ota[] = [];
  for (let i = 0; i < Math.min(n, pool.length); i++) {
    const pick = randomPick(s, pool, wts);
    if (pick == null) break;
    if (out.includes(pick)) continue;
    out.push(pick);
  }
  // 买券的人不等于说上话的人：铁杆会自己来，跟人气无关
  const sorted = [...s.ota].sort((a, b) => b.stick - a.stick);
  for (const o of sorted) {
    if (o.stick < 72) break;
    if (!out.includes(o)) out.push(o);
  }
  return out;
}

/** 所有种子 OTA 都不再来了：这个团只剩我自己在台上。 */
export function everyoneGone(s: State): boolean {
  return s.ota.every((o) => o.stick < 30);
}

export function randomPick(s: State, pool: Ota[], wts: number[]): Ota | null {
  if (!pool.length) return null;
  const r = s._rng as PyRandom | null | undefined;
  if (r == null) return pool[0];
  const idx = Array.from({ length: pool.length }, (_, i) => i);
  const i = r.choices(idx, wts, 1)[0];
  return pool[i];
}

/**
 * 周日的特典会：先看今天会不会开出一张 OTA 卡（她来了才算），
 * 再决定『她今天想说什么』。同一个人一周只出现一次。
 *
 * 四桶：ask（回考第二拍）/ say（随口说出细节）/ ota（别的互动卡）/ other（相处日常）
 */
export function otaPick(
  s: State,
  world: World,
  rng: PyRandom,
  chosens: Ota[],
  _allow_newbie = false,
): [Card | null, Ota | null] {
  if (!chosens.length) return [null, null];

  const pick = (pool: Card[]): Card =>
    rng.choices(
      pool,
      pool.map((c) => Math.max(0.05, Number(g(c, "weight", 1.0)))),
      1,
    )[0];

  const byId: Record<string, Card> = {};
  for (const c of world.cards) byId[c.id] = c;
  if (!s.clue_cool) s.clue_cool = {};
  const cool = s.clue_cool;

  const asks: Card[] = [];
  const says: Card[] = [];
  for (const [cid, info] of Object.entries(s.clues ?? {})) {
    if (info.state !== "said") continue;
    if (n0(g(cool, cid, 0)) > 0) continue;
    const c = byId["ota_ask_" + cid];
    if (c && evalGate(s, c.gate)) asks.push(c);
  }

  if (n0(g(s, "clues_said", 0)) < n0(g(s, "max_clues", 6))) {
    for (const c of world.cards) {
      if (!c.id.startsWith("ota_say_")) continue;
      const cid = c.id.slice("ota_say_".length);
      if (hasOwn(s.clues ?? {}, cid)) continue;
      if (n0(g(cool, cid, 0)) > 0) continue;
      if (evalGate(s, c.gate)) says.push(c);
    }
  }

  // 已经冷却的线索也检查一下（只用来回收）
  for (const cid of Object.keys(cool)) {
    if (cool[cid] > 0) cool[cid] -= 1;
    else delete cool[cid];
  }

  const rest = world.cards.filter(
    (c) =>
      _isOtaCard(c) &&
      !c.id.startsWith("ota_say_") &&
      !c.id.startsWith("ota_ask_") &&
      evalGate(s, c.gate),
  );

  const r = rng.random();
  // 「她说」这一桶得能自己长：收场要三题，一季只有八次特典
  const have = finaleCluePool(s).length;
  const need = Math.max(0, 5 - have);
  const say_share = Math.min(0.58, 0.14 + 0.09 * need);
  let card: Card | null = null;
  if (asks.length && r < 0.2) card = pick(asks);
  else if (says.length && r < 0.2 + say_share) card = pick(says);
  else if (rest.length && r < 0.92) card = pick(rest);
  else if (asks.length || says.length || rest.length) {
    const pool = rest.length ? rest : asks.concat(says);
    card = pick(pool);
  }
  if (card == null) return [null, null];

  // 抽到的如果是回考卡，记住她是谁、并把这条线索压一周
  const who = chosens[0];
  if (card.id.startsWith("ota_ask_")) {
    const cid = card.id.slice("ota_ask_".length);
    cool[cid] = pyInt(n0(g(s, "ask_cooldown", 2)));
    const info = (s.clues ?? {})[cid];
    if (info != null) info.asked = true;
  }
  return [card, who];
}

// 舆论会淡：只要这周没继续加，板子和炎上每周回落一点。
export const FADE: Record<string, number> = { banzi: 6.0 };
export const ENJOU_FADE_RATE = 0.08;

/**
 * 到点的延迟后果：效果生效，顺便看看有没有「带朋友来」。
 * 返回新生的 OTA 名字列表，界面拿来写一句回执。
 */
export function settleDelayed(s: State, world: World, rng: PyRandom): string[] {
  const born: string[] = [];
  for (const d of [...(s.delayed ?? [])]) {
    const when = d.when;
    let fire = false;
    if (when === "本场结束" || when === "下周") fire = true;
    else if (when === "条件") {
      // 落进 s.delayed 的键叫 cond（见 apply_option），这里兼容原始写法 condition
      const cond = d.cond ?? d.condition;
      fire = Boolean(cond) && Boolean(evalGate(s, cond));
    }
    if (!fire) continue;
    if (d.effect) applyEffect(s, d.effect);
    if (d.hatch_friend) {
      const sel = { any_archetype: true, notes: "她带来的朋友。" };
      const an = hatch(s, world, sel, rng, true, d.base_stick ?? null);
      if (an != null) born.push(an.name);
    }
    const idx = s.delayed.indexOf(d);
    if (idx >= 0) s.delayed.splice(idx, 1);
  }
  return born;
}

export function coolDown(s: State): void {
  for (const [k, v] of Object.entries(FADE)) {
    if (hasOwn(s, k) && s[k]) s[k] = Math.max(0.0, Number(s[k]) - v);
  }
  if (s.enjou) s.enjou = Math.max(0.0, Number(s.enjou) * (1.0 - ENJOU_FADE_RATE));
  for (const k of Object.keys(s.cooldown)) {
    s.cooldown[k] -= 1;
    if (s.cooldown[k] <= 0) delete s.cooldown[k];
  }
}

// ------------------------------------------------------------------ 剧情线

/**
 * 剧情线的「投入量」：私联=heat(用 shiren 承接)、恋爱=心动(relation_A)、重线=zhong。
 * 拍0 的 enter 恒为 0，不看。
 */
function _enterValue(s: State, line: StoryLine, st: LineStage): number {
  const n = st.stage;
  if (line._meta.id === "romance") return n ? s.relation_A - 60 : 0;
  if (line._meta.id === "zhong") return n0(g(s, "zhong", 0));
  return n0(g(s, "heat", 0));
}

/**
 * gate 里出现「热」「心动」「重线进度」时，用剧情线自己的进度而不是通用资源。
 * 但拍 0（第一拍）例外：它写的是「阿棠关系 ≥ 60」这种真实数值门槛。
 */
function _gateOk(s: State, line: StoryLine, st: LineStage): boolean {
  const lid = line._meta.id;
  if (lid === "romance" && st.stage === 0) {
    return n0(g(s, "relation_A", 0)) >= 50 && s.week >= 2;
  }
  const g2 = st.gate ?? "";
  if (!evalGate(s, g2)) return false;
  const need = st.enter_heat;
  if (need == null) return true;
  return _enterValue(s, line, st) >= need;
}

/**
 * 记住「她」是谁：重线每一拍都跟着同一个人走。
 * 导出是因为 `loop.py` 直接调 `E._remember_chaser()`（L1745）——
 * 谁在场由流程决定，不是引擎自己算的，所以这条得让外面能叫。
 */
export function _rememberChaser(s: State, line: StoryLine, v?: any): void {
  if (!(line._meta?.chaser_schema || v?.select_chaser)) return;
  if (!s._chaser && s.ota?.length) {
    let best = s.ota[0];
    for (const o of s.ota) if (o.stick > best.stick) best = o;
    s._chaser = best.id;
  }
}

/**
 * 返回该线当前可进入的拍（stage）或 null。
 * 只认「下一拍」不许跳拍；同一周同一条线最多推一拍。
 */
export function lineStage(s: State, line: StoryLine): LineStage | null {
  const lid = line._meta.id;
  _derive(s);
  if (n0(g(s._line_cool ?? {}, lid, 0)) > s.week) return null;
  const prog = s.story[lid];
  const nxt = prog == null ? 0 : prog.stage + 1;
  for (const st of line.stages) {
    if (st.stage === nxt) {
      return _gateOk(s, line, st) && !_thisWeek(s, lid) ? st : null;
    }
  }
  return null;
}

export function lineCool(s: State, lid: string, weeks = 2): void {
  if (!s._line_cool) s._line_cool = {};
  s._line_cool[lid] = s.week + weeks;
}

/**
 * 同一周同一条线只推一拍。
 *
 * 不能直接比 s.week：do_week 中途会结算/换周，要用显式的「本次推线周期号」。
 */
function _thisWeek(s: State, lid: string): boolean {
  const tick = s._line_tick;
  if (tick == null) return false;
  return n0(g(s._line_week ?? {}, lid, 0)) === tick;
}

/** 到这一周还没人主动锁主线，就由已经在走的那条线接手。 */
export function MAINLINE_FALLBACK_WEEK(s: State): number {
  return Math.max(3, pyInt(n0(g(s, "weeks_total", 8))) - 3);
}

/** 按 flag 判断这条线是不是已经被玩家关掉了（不走 world 也能判）。 */
function _lineShut(s: State, lid: string): boolean {
  const fl = s.flags ?? new Set<string>();
  if (lid === "shiren") return fl.has("line_closed");
  if (lid === "romance") return fl.has("kept_wall");
  return false;
}

/**
 * 算出「这一季该走哪条线」，null 表示还没定。
 *
 * 三条线一季只能走一条。私联和恋爱是玩家伸手选的，重线是她压过来——
 * 它每一条选项都 +1，玩家没有「不推进」这个动作，所以重线只能兜底。
 */
function _mainlinePick(s: State): string | null {
  const fl = s.flags ?? new Set<string>();
  if (fl.has("crossed_line")) return "shiren";
  if (n0(g(s, "heart", 0)) >= 1) return "romance";
  if (pyInt(n0(g(s, "week", 1))) < MAINLINE_FALLBACK_WEEK(s)) return null;
  const story = s.story ?? {};
  let best: string | null = null;
  let bn = -1;
  for (const lid of ["shiren", "romance", "zhong"]) {
    // 只认「真的出过场」的线（story 里有记录）
    if (!hasOwn(story, lid) || _lineShut(s, lid)) continue;
    const n = g(story[lid] ?? {}, "stage", -1) as number;
    if (n > bn) {
      best = lid;
      bn = n;
    }
  }
  if (best != null) return best;
  // 一条都没走过：重线上场。她一直在那儿，是三条线里唯一不需要玩家先伸手的。
  return _lineShut(s, "zhong") ? null : "zhong";
}

/**
 * 这一季已经走上的那条线。定了就不再改——后面再越线也不算数了。
 * 写成落盘字段（_mainline）而不是每次现算，否则两条线会同时活着。
 */
export function mainline(s: State): string | null {
  const lid0 = s._mainline;
  if (lid0) return lid0;
  const lid = _mainlinePick(s);
  if (lid) {
    s._mainline = lid;
    s._mainline_week = g(s, "week", undefined);
  }
  return lid;
}

/** 这条线是否因为『不想走』而被玩家关掉。 */
export function lineLocked(s: State, line: StoryLine): boolean {
  const fl = s.flags;
  const lid = line._meta.id;
  if (lid === "shiren" && fl.has("line_closed")) return true;
  if (lid === "romance" && fl.has("kept_wall")) return true;
  return false;
}

// ------------------------------------------------------------------ 私联终局

export function shirenLine(world: World): StoryLine | null {
  for (const ln of world.lines) if (ln._meta.id === "shiren") return ln;
  return null;
}

export function romanceLine(world: World): StoryLine | null {
  for (const ln of world.lines) if (ln._meta.id === "romance") return ln;
  return null;
}

/**
 * 『决赛前一晚』：季末那一周的开头，必到，不等 stage4。
 * storyline_shiren 的设计说明写的是「唯一钉死的日历」。
 */
export function FINALE_WEEK(s: State): number {
  return pyInt(n0(g(s, "weeks_total", 8)));
}

/** 该不该进收场：越了线、还没收过、也没被玩家关掉，而且这一季走的就是私联。 */
export function shirenFinaleReady(s: State, world: World): boolean {
  if (!s.flags.has("crossed_line")) return false;
  if (s.flags.has("finale_done")) return false;
  // 一季只走一条线：越线发生在主线已经定给别人之后，这条就不算这一季的路
  if (mainline(s) !== "shiren") return false;
  const ln = shirenLine(world);
  if (ln == null || lineLocked(s, ln)) return false;
  return pyInt(n0(g(s, "week", 1))) >= FINALE_WEEK(s);
}

/** 终局能考哪些：她这一季说过、而且系统里锁着一个真值的细节。 */
export function finaleCluePool(s: State): string[] {
  const mem = memoryTable();
  const out: string[] = [];
  for (const [cid, info] of Object.entries(s.clues ?? {})) {
    if (!hasOwn(mem, cid)) continue;
    if (["said", "known", "wrong", "dropped"].includes(info.state as string)) out.push(cid);
  }
  return out;
}

/**
 * 从解锁的记忆点里抽 n 道拷问，做成可以直接上屏的卡。
 *
 * 题目直接复用 ota_memory 的 ask_q 与 set——这套台词本来就是为「你还记得吗」写的。
 */
export function finaleQuizCards(s: State, _world: World, rng: PyRandom, n = 3): Card[] {
  const mem = memoryTable();
  const pool = finaleCluePool(s);
  if (!pool.length) return [];
  rng.shuffle(pool);
  const picks = pool.slice(0, n);
  const cards: Card[] = [];
  for (const cid of picks) {
    const c = mem[cid] ?? ({} as MemClue);
    const vals = [...(c.set ?? [])];
    if (vals.length < 2) continue;
    const truth = ensureTruth(s, cid, rng);
    if (!vals.includes(truth)) continue;
    // 题干用 ask_q（一句天然的问法），不用 ask[]——那会把答案印在问句上
    const say = c.ask_q ?? rng.choice(c.ask ?? ["『你还记得我之前说过的那个吗？』"]);
    cards.push({
      id: `finale_quiz_${cid}`,
      type: "OTA记忆",
      title: "收场",
      _meta: {
        rq_stage: "ask",
        clue: cid,
        react_good: c.react_good ?? {},
        react_bad: c.react_bad ?? {},
        finale: true,
      },
      narrative: say.split("{truth}").join("那个"),
      // 选项按 set 原序排，上屏时由 loop._ask_options 按本局顺序重排
      options: vals.map((v, i) => ({
        id: `pick_${i}`,
        label: v,
        desc: "",
        rq_pick: { clue: cid, slot: "speaker", choice: v === truth ? "true" : "false" },
      })),
    });
  }
  return cards;
}

/**
 * 答对几道才算「真的看见过她」：三题要对两题，两题就得全对。
 * 以前两题也只要求答对一题，等于 50% 就能拿到「唯一」，比三题的 2/3 还松。
 */
export function finalePassN(nCards: number): number {
  if (nCards <= 0) return 0;
  if (nCards <= 2) return nCards;
  return 2;
}

/**
 * 按拷问成绩分岔：答不上来直接是「用完」，答上了才有得选。
 * 答对只记「答上了」，走哪条路由玩家自己选（loop.choose_card 里写 truly_seen 或 final_collapse）。
 */
export function applyFinaleOutcome(s: State, nOk: number, nAll: number): [string, boolean] {
  const need = finalePassN(nAll);
  const ok = nAll > 0 && nOk >= need;
  applyEffect(s, { psyche: ok ? 10 : -8 });
  if (!ok) {
    // 答不上来：这些深夜你记得的是「有人陪我」，不是「她是谁」。
    s.flags.add("used_as_tool");
    if (!s._fired) s._fired = new Set<string>();
    s._fired.add("used_as_tool");
  }
  s.flags.add("finale_done");
  if (!s._fired) s._fired = new Set<string>();
  s._fired.add("finale_done");
  clamp(s);
  return [ok ? "real_seen" : "fake_tool", ok];
}

/** 这一周有哪条线能往前推。一季只走一条线。 */
export function drawLineAll(s: State, world: World): [StoryLine, LineStage][] {
  const main = mainline(s);
  const opts: [StoryLine, LineStage][] = [];
  for (const line of world.lines) {
    const lid = line._meta.id;
    if (main && lid !== main) continue;
    if (lineLocked(s, line)) continue;
    const st = lineStage(s, line);
    if (st) opts.push([line, st]);
  }
  return opts;
}

export function drawLine(s: State, world: World, rng: PyRandom): [StoryLine, LineStage] | null {
  const opts = drawLineAll(s, world);
  if (!opts.length) return null;
  // 每条线每周都各自有机会推动（不按 stage 序号排队，否则一条线会把别的饿死）
  const wts = opts.map(([line, st]) => {
    const lid = line._meta.id;
    let base = 1.0 + 0.35 * st.stage;
    if (hasOwn(s.story, lid)) base += 1.2; // 已经在这条线里了
    if (lid === "zhong") {
      // 重线每出现一次就自动 +1 stage，若再按 stage 加权就会滚雪球
      base = 1.0 + (hasOwn(s.story, lid) ? 0.45 : 0.0);
    }
    if (lid === "shiren" && !s.flags.has("crossed_line")) {
      // 还没越线时，给私联一点「可能被搭话」的底量
      base += 0.6;
    }
    if (lid === "shiren" && s.flags.has("crossed_line")) {
      // 越了线就是真的在过另一种日子：这条线每一拍都得往前走
      base *= 2.6;
    }
    if (lid === "romance" && n0(g(s, "relation_A", 0)) >= 50) {
      base *= 2.4; // 阿棠关系够了就该轮到她
    }
    return base;
  });
  return rng.choices(opts, wts, 1)[0];
}

// ------------------------------------------------------------------ 一周三拍

export const ACTS: Record<string, Record<string, any>> = {
  dance: { name: "练舞", stamina: -18, dance: 6.0, money: -40, weibo: "练舞" },
  sing: { name: "练唱", stamina: -18, sing: 6.0, money: -40, weibo: "练唱" },
  mc: { name: "对着镜子练营业的话", stamina: -10, mc: 5.0, money: -20, weibo: "练话" },
  content: { name: "拍内容发微博", stamina: -8, fame: 1.5, psyche: -1.5, money: 0, weibo: "拍" },
  work: { name: "开直播", stamina: -22, money: 380, fame: 2.0, weibo: "" },
  rest: { name: "躺一整天", stamina: 28, psyche: 2.0, weibo: "" },
};

export const RENT = 900;
export const FEE = 620; // 一周的场租+分成（和 loop.py 里那一份保持一致）
export const FEE_FIRST = 160; // 场地第一次给新人便宜
export const SKILL_CAP = 82; // 舞/唱/live 话术的硬上限
export const ACT_REPEAT: Record<string, number> = {
  dance: 2.0,
  sing: 2.0,
  mc: 2.0,
  content: 0.8,
  work: 1.6,
  rest: 1.8,
};

/**
 * 一天做一件事。连续做同一件事会递减，但递减只削增益、不削体力消耗。
 */
export function doAct(s: State, act: string, _rng: PyRandom): void {
  const a = ACTS[act];
  if (!a) return;
  const last = s._last_act;
  const mult = last === act ? (ACT_REPEAT[act] ?? 1.0) : 1.0;
  for (const k of ["stamina", "money", "dance", "sing", "mc", "fame", "psyche"]) {
    if (!hasOwn(a, k)) continue;
    const v = a[k] * (k === "stamina" ? 1.0 : mult);
    if (k === "fame") addFame(s, v);
    else s[k] += v;
  }
  if (a.weibo) s.weibo_posts = n0(g(s, "weibo_posts", 0)) + 1;
  s.acted = act;
  s._last_act = act;
  // 硬上：体力已经见底还去练、还开播，这一下是从心理那里借的
  if (s.stamina <= 0 && ["dance", "sing", "mc", "work"].includes(act)) {
    s.psyche -= 5;
    s.pushed_while_spent = n0(g(s, "pushed_while_spent", 0)) + 1;
    s._last_act_spent = true; // 给界面用：这一下是硬上的
  }
  // 态度会走样：为了流量连着开播、靠拍内容维持热度，台上那套话就越说越像模板
  if (act === "work") s.template = Math.min(1.0, s.template + 0.018);
  else if (act === "dance" || act === "sing" || act === "mc") {
    s.template = Math.max(0.0, s.template - 0.015);
  } else if (act === "content") s.template = Math.min(1.0, s.template + 0.008);
  if (!s._acts_week) s._acts_week = [];
  s._acts_week.push(act);
  clamp(s);
}

/** 这一周开口的调子：说算数的实话，还是把话说好。 */
export function policyTone(s: State, policy: Policy | null): string {
  if (policy?.tone) return policy.tone(s);
  return n0(g(s, "true_talk", 0)) === 0 && s.template < 0.35 ? "truth" : "safe";
}

export const TALKS: [string, string, string][] = [
  ["tired", "下班的路上", "今天排完舞我坐在排练室的地上没起来，脚背磨破了。"],
  ["scared", "收工以后", "今天有一场我上台前一直在数拍子，怕忘。"],
  ["lonely", "回家的地铁上", "有时候我觉得这半年跟我说话的人很少。"],
  ["money", "算账的时候", "房租这次是勉强凑上的，还差一点。"],
  ["why", "睡不着的时候", "我也不知道我为什么要一直跳下去，可停下来我不知道做什么。"],
];

/** 版聊里发出去的那条：说真话，或者发一张好看的照片。 */
function _pickTalk(s: State, _rng: PyRandom, tone: string, report: any[][]): [string, string] {
  s.talk_seen = n0(g(s, "talk_seen", 0)) + 1;
  if (tone === "truth") {
    const [key, where, line] = TALKS[(s.talk_seen - 1) % TALKS.length];
    s.true_talk = pyInt(n0(g(s, "true_talk", 0))) + 1;
    s.true_talks = n0(g(s, "true_talks", 0));
    s.true_streak = n0(g(s, "true_streak", 0)) + 1;
    s.template = Math.max(0.0, s.template - 0.03);
    // 说得太难听，会有人不喜欢：说真话不是免费的
    addFame(s, -1);
    s.psyche = n0(g(s, "psyche", 0)) + 3;
    report.push(["talk", key]);
    return [where, line];
  }
  s.true_streak = 0;
  s.weibo_posts = n0(g(s, "weibo_posts", 0)) + 1;
  s.template = Math.min(1.0, s.template + 0.02);
  addFame(s, 1.5);
  report.push(["talk", "photo"]);
  return ["配图发出去以后", "今天也谢谢大家，明天见。"];
}

/** 调一次策略，返回选项下标（null/undefined → 0）。 */
function callPolicy(
  policy: Policy | null,
  s: State,
  card: any,
  options: Option[],
  rng: PyRandom,
): number {
  if (!policy?.choose) return rng.randrange(options.length);
  const oi = policy.choose(s, card, options);
  return oi == null ? 0 : oi;
}

/**
 * 跑一周：平日 3 个动作 → 版聊 → 组内/剧情线 → OTA 互动 → 周末 Live + 特典会。
 *
 * **这个方法里每一次 rng 调用都必须和 Python 一字不差**——多一次 `random()`
 * 后面所有卡都会错位，对账会从第 1 周就开始漂。
 */
export function doWeek(
  s: State,
  world: World,
  rng: PyRandom,
  policy: Policy | null = null,
): { tier: string; score: number; report: any[][] } {
  if (!s._acts_week) s._acts_week = [];
  s._acts_week = [];
  const report: any[][] = [];
  s.beat = 0;

  // ---- 平日：三个动作（真玩家不会天天三份工；钱够就先练）
  let rest_n = 0;
  for (let i = 0; i < 3; i++) {
    const act = policy?.act ? policy.act(s) : rng.choice(Object.keys(ACTS));
    doAct(s, act, rng);
    report.push(["act", act]);
    if (act === "rest") rest_n += 1;
  }
  // 最后一季的「躺」不是偷懒，是放手
  if (s.week >= n0(g(s, "weeks_total", 8)) && rest_n >= 2 && s.psyche >= 50) {
    s.chose_leave = true;
    report.push(["leave", "这季跳完就不跳了"]);
  }
  // 一周排满、身体一直空着：这周是从心理里借出来的
  if (s.stamina < 15) {
    s.psyche -= 5;
    s.spent_weeks = n0(g(s, "spent_weeks", 0)) + 1;
    clamp(s);
    report.push(["spent", "这一周身体一直是空的"]);
  }
  s._rng = rng;
  if (s.stamina < 25) s.nights_stamina_low = n0(g(s, "nights_stamina_low", 0)) + 1;
  // 没钱睡不好：体力清零的后半夜是拿心理换的
  if (s.stamina < 10) {
    s.psyche -= 6;
    clamp(s);
    report.push(["burnout", "体力见底"]);
  }
  // 房租：第八天要交，交不上就睡大街（先睡排练室，再睡车站）
  if (s.week % 2 === 1 && s.money < RENT) {
    s.psyche -= 18;
    s.stamina -= 10;
    s.rent_missed = true;
    clamp(s);
    report.push(["rent_due", "房租没交上"]);
  }

  // ---- 版聊：顺手发一条，回/不回
  {
    const r = rng.uniform(0, 1);
    if (r < 0.6) {
      const c = draw(s, world, rng, null, null, ["OTA互动", "OTA相处的瞬间"]);
      if (c && (c.options ?? []).length) {
        const slots = cast(s, c, rng, world) ?? {};
        const oi = callPolicy(policy, s, c, c.options!, rng);
        applyOption(s, c.options![oi], rng, slots, c);
        s.cooldown[c.id] = pyInt(g(c, "cooldown", 3));
        report.push(["bbs", c.id, c.options![oi].id]);
      }
    }
  }

  // ---- 剧情线（优先）否则抽一张团内/日常
  let o_line: string | null = null;
  s._line_tick = s.week;
  const lr = drawLine(s, world, rng);
  if (lr && rng.random() < 0.45) {
    const [line, st] = lr;
    const v = rng.choice(st.variants);
    const oi = callPolicy(policy, s, { _line: line, _stage: st }, v.options, rng);
    const o = v.options[oi];
    const snap: Record<string, number> = {};
    for (const k of ["zhong", "zhongs", "heat", "heart"]) snap[k] = Number(n0(g(s, k, 0)));
    _rememberChaser(s, line, v);
    applyOption(s, o, rng, {}, null);
    // 剧情线的推进量以前靠选项自己写 immediate.zhong，但那些选项绝大多数只写 zhongs，
    // 结果是重线永远停在 stage 0。推进量在引擎这一层补。
    const lid = line._meta.id;
    if ((snap.zhong || 0) >= n0(g(s, "zhong", 0))) s.zhong = n0(snap.zhong) + 1;
    if (lid === "shiren" && (snap.heat || 0) >= n0(g(s, "heat", 0))) s.heat = n0(snap.heat) + 1;
    if (lid === "romance" && (snap.heart || 0) >= n0(g(s, "heart", 0)) && o.advance) {
      s.heart = n0(snap.heart) + 1;
    }
    if (lid === "romance" && st.stage === 0 && n0(g(s, "heart", 0)) === 0) {
      s.heart = 1; // 她主动靠近这件事本身就是第一次心动
    }
    // 数值链：重线推进一拍，「私生」也跟着往前一点；私联则一点一点把开盒风险垫高。
    if (lid === "zhong") {
      const add = st.stage >= 3 ? 12 : 8;
      s.shiroi = Number(n0(g(s, "shiroi", 0))) + add;
    }
    if (lid === "shiren") s.kaibox = Number(n0(g(s, "kaibox", 0))) + 4;
    o_line = lid;
    s.story[lid] = { stage: st.stage };
    s._last_line = lid;
    if (!s._line_week) s._line_week = {};
    s._line_week[lid] = g(s, "_line_tick", s.week);
    report.push(["story", lid, st.stage, o.id]);
  } else if (drawLine(s, world, rng) != null && rng.random() < 0.55) {
    // 这周有剧情线能推，但这一轮没落下来：给点「正在发生」的份量
    const lr2 = drawLine(s, world, rng)!;
    const [line, st] = lr2;
    const lid = line._meta.id;
    if (lid === "zhong") s.shiroi = Number(n0(g(s, "shiroi", 0))) + 4;
    else if (lid === "shiren") {
      s.kaibox = Number(n0(g(s, "kaibox", 0))) + 3;
      s.heat = Number(n0(g(s, "heat", 0))) + 0.5;
    }
    report.push(["line_simmer", lid, st.stage]);
  }
  if (!o_line && s.week >= 2 && rng.random() < 0.55) {
    // 剧情线没落下来的那一周，这一拍的重量给「一句算数的实话」
    const tone = policyTone(s, policy) === "truth" ? "truth" : "safe";
    _pickTalk(s, rng, tone, report);
  }
  // 环境/日常是「这一周的天」，不该跟一张要我做选择的卡抢同一个位置
  for (const kinds of [["ambient"], ["日常"], ["private", "私联恋爱", "私生", "私生跟踪"]]) {
    const a = draw(s, world, rng, null, null, kinds);
    if (a != null && a.effect) {
      applyEffect(s, a.effect);
      s.cooldown[a.id] = pyInt(g(a, "cooldown", 3));
      report.push(["ambient", a.id]);
    }
  }
  // 团内的事 / 外部的压力 / 半夜的小事，各给一次独立机会
  for (const kinds of [
    ["团内", "团内关系"],
    ["外部", "external", "外部舆论", "舞台事故"],
    ["daily"],
    ["团内", "团内关系", "positive", "ota"],
    ["external", "外部", "外部舆论"],
  ]) {
    const d = draw(s, world, rng, null, null, kinds);
    if (d == null) continue;
    if (d.effect) {
      applyEffect(s, d.effect);
      report.push(["ambient", d.id]);
    } else if ((d.options ?? []).length) {
      const slots = cast(s, d, rng, world) ?? {};
      const oi = callPolicy(policy, s, d, d.options!, rng);
      applyOption(s, d.options![oi], rng, slots, d);
      report.push(["card", d.id, d.options![oi].id]);
    }
    s.cooldown[d.id] = pyInt(g(d, "cooldown", 3));
  }
  // 「外面在说我」：人气上来了就一定会被讨论
  if (report.some((r) => r[0] === "card" && typeof r[1] === "string" && r[1].startsWith("ext_"))) {
    const f = Number(n0(g(s, "fame", 0)));
    if (f > 0) {
      s.banzi = Number(n0(g(s, "banzi", 0))) + Math.min(6.0, f * 0.06);
      if (g(s, "bold") || g(s, "weibo_posts")) {
        s.enjou = Number(n0(g(s, "enjou", 0))) + Math.min(4.0, f * 0.04);
      }
    }
  }
  {
    const c = draw(s, world, rng, null, null, [
      "daily",
      "external",
      "ambient",
      "positive",
      "团内",
      "团内关系",
      "外部舆论",
      "舞台事故",
      "私生",
      "私生跟踪",
    ]);
    if (c != null) {
      if (c.effect) {
        applyEffect(s, c.effect);
        report.push(["ambient", c.id]);
      } else if ((c.options ?? []).length) {
        const slots = cast(s, c, rng, world) ?? {};
        const oi = callPolicy(policy, s, c, c.options!, rng);
        applyOption(s, c.options![oi], rng, slots, c);
        report.push(["card", c.id, c.options![oi].id]);
      }
      s.cooldown[c.id] = pyInt(g(c, "cooldown", 3));
    }
  }

  // ---- 特典会：她来了、她坐下、她开口（OTA 互动 / 回考）
  s.beat = 1;
  const chosens = warmOta(s);
  const used = new Set<string>();
  let day = 0;
  while (day < 2) {
    const [c, who] = otaPick(
      s,
      world,
      rng,
      chosens.filter((o) => !used.has(o.id)),
    );
    if (c == null || who == null) break;
    used.add(who.id);
    day += 1;
    let slots = cast(s, c, rng, world) ?? {};
    if (!Object.keys(slots).length) slots = { speaker: who };
    const opts = c.options!;
    const oi = callPolicy(policy, s, c, opts, rng);
    applyOption(s, opts[oi], rng, slots, c);
    s.cooldown[c.id] = pyInt(g(c, "cooldown", 3));
    report.push(["ota", c.id, opts[oi].id, who.name]);
  }

  // ---- Live 结算
  s.beat = 2;
  // 今晚还剩多少力气：体力归零扣 5 分，满体力加 0 分
  const fatigue = ((s.stamina - 50) / 50) * 5.0;
  const sc = stageScore(s) + fatigue + rng.uniform(-5, 5);
  let tier: string;
  if (sc >= 64) {
    tier = "神场";
    addFame(s, 8);
    s.psyche += 3;
    s.gorshou = n0(g(s, "gorshou", 0)) + 1;
    for (const o of s.ota) o.stick += 3;
  } else if (sc >= 54) {
    tier = "好场";
    addFame(s, 5);
    s.psyche += 1;
    for (const o of s.ota) o.stick += 2;
  } else if (sc >= 44) {
    tier = "平场";
    addFame(s, 2);
  } else if (sc >= 34) {
    tier = "冷场";
    s.psyche -= 4;
    for (const o of s.ota) o.stick -= 1.5;
  } else {
    tier = "翻车";
    s.psyche -= 8;
    s.enjou += 3;
    for (const o of s.ota) o.stick -= 2.5;
  }
  s.max_single = Math.max(s.max_single, sc);
  // 冷场/翻车要留档：外部卡「翻车那一下被拍下来了」就是靠这个开门的
  if (tier === "冷场" || tier === "翻车") s.blew_it = pyInt(n0(g(s, "blew_it", 0))) + 1;
  // 心气塌了还上台：一晚算一次
  if (s.psyche < 20) s.played_while_collapsing = true;
  clamp(s);
  // 特典收入
  const income = weeklyIncome(s);
  s.money += income - (s.week === 1 ? FEE_FIRST : FEE);
  if (s.money < 0) {
    // 欠款不能靠余额挡住：直接判「这一周撑不下去」
    s.psyche -= 10;
    s.stamina -= 5;
    s.money = 0;
  }
  s._income_last = income;
  if (income >= 560) s.psyche += 2; // 台下坐满的时候，人是会高兴的
  // 一条线的推进靠「钱/心理」这些共用资源表达不了，必须显式加一步
  if (o_line === "shiren") s.heat = n0(g(s, "heat", 0)) + 1;
  else if (o_line === "romance") s.heart = n0(g(s, "heart", 0)) + 1;
  else if (o_line === "zhong") s.zhong = n0(g(s, "zhong", 0)) + 1;
  if (income < 240) {
    s.low_income_weeks = n0(g(s, "low_income_weeks", 0)) + 1;
    s.psyche -= 6; // 台下空着回家的那个晚上
  }
  // 收入走势：骂声带来新人还是赶走老人，就看最后两周比峰值掉了多少
  const prevPeak = Number(n0(g(s, "income_peak", 0)));
  s.income_now = income;
  if (income > prevPeak) s.income_peak = income;
  else if (s.week >= 4 && prevPeak && income < prevPeak * 0.85) {
    s.income_falling = true; // 季末在掉：人正在走
  }
  if (everyoneGone(s)) s.psyche -= 10; // 所有人的黏性都掉到 30 以下
  // 「你是不是有点累」：只有「这一季一次真话都没说过」才会被问
  if (
    !g(s, "empty_asked") &&
    s.week >= 3 &&
    pyInt(n0(g(s, "truth_pick", 0))) + pyInt(n0(g(s, "safe_pick", 0))) >= 2 &&
    truthRate(s) <= 0.25
  ) {
    const warm = s.ota.filter((o) => o.stick >= 45);
    if (warm.length) {
      s.empty_asked = true;
      s.empty_asked_who = warm[0].name;
      report.push(["empty_asked", `${warm[0].name}：「你是不是有点累。」`]);
    }
  }
  // 运营递过来的那条会火的路：第一次是明确的拒绝时刻
  if (!g(s, "offer_seen") && s.week >= 4) {
    s.offer_seen = true;
    const offers = ["炒 CP", "讲以前那个团", "接一条擦边商务"];
    s.offer_kind = offers[(s.week - 3) % 3];
    report.push(["offer", `运营：${s.offer_kind} 这条能火，做不做？`]);
  }
  // 延迟队列：本场结束的先结，本周末发生的全部结
  settleDelayed(s, world, rng);
  coolDown(s);
  clamp(s); // 这一拍里所有散装加法都要收口
  // 最后一周，人已经累了，还是站上去把这一场跳完
  if (s.week >= n0(g(s, "weeks_total", 8))) s.last_live_choice = true;
  s.week += 1;
  for (const o of s.ota) o.weeks_known += 1;
  return { tier, score: sc, report };
}

// ------------------------------------------------------------------ 结局

export function _ids(world: World, types: string[]): Set<string> {
  return new Set(world.cards.filter((c) => types.includes(c.type)).map((c) => c.id));
}

/**
 * 「还没塌」。季末体力永远是 0，所以这里不看体力；说真话也不再是门槛。
 */
export function baoshou(s: State, _true_talk: number): boolean {
  return (
    s.psyche >= 45 &&
    relavg(s) >= 40 &&
    s.ota.filter((o) => o.stick >= 40).length >= 3
  );
}

/** 取条件字典里的第一个数值（Python 侧同样只定义未引用，按原样保留）。 */
export function _numOf(cond: Record<string, any>): number {
  for (const v of Object.values(cond)) return Number(v);
  return 0.0;
}

function _cmpWith(v: number, op: string, x: number): boolean {
  if (op === ">=") return v >= x;
  if (op === "<=") return v <= x;
  if (op === ">") return v > x;
  return v < x;
}

/**
 * 这一季开口的「真话率」：带 tone 标记的选项里，说实话占多少。
 * 分母只数玩家真的做过选择的语气点，不把版聊和回考算进去。
 */
export function truthRate(s: State): number {
  const t = pyInt(n0(g(s, "truth_pick", 0)));
  const f = pyInt(n0(g(s, "safe_pick", 0)));
  const n = t + f;
  return n ? t / n : 0.0;
}

function _extra(key: string, s: State, true_talk: number): any {
  switch (key) {
    case "truth_rate":
      return truthRate(s);
    case "shiren_stage": {
      // 私联线走到第几拍：-1 = 这一季根本没见过她
      const st = g(g(s.story ?? {}, "shiren", {}) ?? {}, "stage", -1);
      return pyInt(st);
    }
    case "truth_pick":
      return pyInt(n0(g(s, "truth_pick", 0)));
    case "tone_choices":
      return pyInt(n0(g(s, "truth_pick", 0))) + pyInt(n0(g(s, "safe_pick", 0)));
    case "empty_choice":
      // 「你是不是有点累」那一下我怎么回的：reply=还是用那套话（空心），truth=说了真的
      return g(s, "empty_choice", null) ?? "";
    case "relavg":
      return relavg(s);
    case "max_share":
      return maxShare(s);
    case "beibao":
      // 「被包养」只认显式的 flag：苦养计数数的是「欠了几次人情」
      return s.flags.has("beibao");
    case "true_cog":
      return true_talk >= 1;
    case "true_talk":
      return true_talk;
    case "offer_refused":
      // 运营递来那条会火的路，我当面拒了
      return g(s, "offer_choice", null) === "refuse";
    case "template":
      return s.template;
    case "chose_leave":
      return s.chose_leave;
    case "rent_missed":
      return Boolean(g(s, "rent_missed", false));
    case "ota_ge40_count":
      return s.ota.filter((o) => o.stick >= 40).length;
    case "max_single":
      return s.max_single;
    case "last_live":
      return Boolean(s.last_live_choice);
    case "played_while_collapsing":
      return Boolean(g(s, "played_while_collapsing"));
    case "money_drop":
      // 这一季特典收入在掉——季末最后两周明显低于本季峰值，或至少两周够不着最低线
      return Boolean(g(s, "income_falling")) || n0(g(s, "low_income_weeks", 0)) >= 2;
    case "money_kept":
      // 「恶劣」要的是钱没掉：被骂出来的热度真的换成了人和钱
      return !(Boolean(g(s, "income_falling")) || n0(g(s, "low_income_weeks", 0)) >= 2);
    case "not_baoshou":
      return !baoshou(s, true_talk);
    case "no_rent_missed":
      return !Boolean(g(s, "rent_missed", false));
    case "pushed":
      // 「硬上」次数：体力见底还在练/还开播
      return pyInt(n0(g(s, "pushed_while_spent", 0)));
    default:
      return g(s, key, 0);
  }
}

/**
 * 求值 endings.json 的 cond 结构：
 * {'field': {'>=':x}} / {'any':[{...}]} / {'all':[...]} / {'not_baoshou': True}
 */
export function checkCond(cond: any, s: State, true_talk: number): boolean {
  if (!cond || typeof cond !== "object") return true;
  for (const [k, v] of Object.entries(cond)) {
    if (k === "any") {
      if (!(v as any[]).some((x) => checkCond(x, s, true_talk))) return false;
    } else if (k === "all") {
      if (!(v as any[]).every((x) => checkCond(x, s, true_talk))) return false;
    } else if (k === "not_baoshou" || k === "no_rent_missed") {
      // 写 true = 要求成立；写 false = 这一项不做约束（不是「要求它为假」）
      const val = k === "not_baoshou" ? !baoshou(s, true_talk) : !Boolean(g(s, "rent_missed", false));
      if (Boolean(v) && !val) return false;
    } else if (v && typeof v === "object") {
      const cur = _extra(k, s, true_talk);
      for (const [op, x] of Object.entries(v as any)) {
        if ([">=", "<=", ">", "<", "=="].includes(op)) {
          const curN = typeof cur === "number" ? cur : Number(cur);
          const cmp =
            op === "==" ? curN === Number(x) : _cmpWith(curN, op, Number(x));
          if (!cmp) return false;
        }
      }
    } else if (typeof v === "boolean" || typeof v === "string") {
      // 写 false = 这一项不做约束，继续看后面的键
      if (!v) continue;
      const ex = _extra(k, s, true_talk);
      const want = typeof v === "string" ? v : true;
      if (!(ex === want)) return false;
    } else {
      return true;
    }
  }
  return true;
}

/** 按 data/endings.json 的判决表判定。提前结束先判。 */
export function judge(
  s: State,
  world: World,
  true_talk?: number | null,
): [string, boolean] {
  if (true_talk == null) true_talk = pyInt(n0(g(s, "true_talk", 0)));
  const fl = s.flags;
  for (const e of world.endings.early ?? []) {
    if (fl.has(e.trigger.flag)) return [e.name, true];
  }
  for (const f of world.endings.flow ?? []) {
    if (checkCond(g(f, "cond", null), s, true_talk)) return [f.name, false];
  }
  return ["散场", false];
}

/** 自动跑一季。empty_choice="reply" = 继续照那套话回（空心）。 */
export function runSeason(
  world: World,
  seed = 0,
  policy: Policy | null = null,
  _verbose = false,
  empty_choice = "reply",
  offer_choice = "refuse",
  weeks?: number | null,
): [State, string, boolean] {
  const rng = new PyRandom(seed);
  const s = newState(world, null, null, rng);
  for (let i = 0; i < pyInt(weeks || s.weeks_total); i++) {
    doWeek(s, world, rng, policy);
    if (g(s, "empty_asked") && g(s, "empty_choice") == null) s.empty_choice = empty_choice;
    if (g(s, "offer_seen") && g(s, "offer_choice") == null) {
      s.offer_choice = offer_choice;
      if (offer_choice === "take") {
        s.enjou = Math.min(100.0, s.enjou + 30); // 那条路真的会火，也真的会烧
        addFame(s, 12);
      }
    }
  }
  const [name, early] = judge(s, world, n0(g(s, "true_talk", 0)));
  s.ended = name;
  return [s, name, early];
}

// ------------------------------------------------------------------ 进度（给界面显示）

/**
 * 心理的软上限：过了 85 以后每加一点只算四分之一。
 * 这一行练习和钱一样是会边际递减的，不该到季末人人 100。
 */
export function softCapPsyche(v: number, cap = 85.0): number {
  if (v <= cap) return v;
  return cap + (v - cap) * 0.25;
}

/**
 * 这一场卖券的钱。人数由 warm_ota 定（人气决定来几个人，铁杆必到），
 * 每张 80 块——和界面账单用的是同一份 bill.ts。
 *
 * 注意：**这个函数会消耗 rng**（warm_ota → random_pick → s._rng）。
 * Python 版也是如此，do_week 里 warm_ota 因此被调了两次。不要"优化"掉。
 */
export function weeklyIncome(s: State): number {
  const who = warmOta(s);
  return Number(weeklyBill(s as any, who).yen);
}

/** 舞/唱/话术的统一档位：给玩家一个「现在算什么水平」。 */
export function tierName(v: number): string {
  if (v >= 70) return "压得住整场";
  if (v >= 60) return "站得住";
  if (v >= 50) return "像样了";
  if (v >= 40) return "能看";
  if (v >= 30) return "生疏";
  return "不会";
}

/** 离下一档还差多少（0 表示已经是最高档）。 */
export function nextTier(v: number): number {
  for (const t of [30, 40, 50, 60, 70]) {
    if (v < t) return t - v;
  }
  return 0;
}

/** 这个动作这一次会涨多少（连做就减半），给界面标「+4 / +2」用。 */
export function actGain(s: State, act: string): number {
  const a = ACTS[act] ?? {};
  const mult = s._last_act === act ? (ACT_REPEAT[act] ?? 1.0) : 1.0;
  const v = a[act];
  return v ? pyInt(pyRound(Number(v) * mult)) : 0;
}

/** 事件放大表（给界面/调试用）。 */
export const EVENT_MULT = EventMult.MULT;

/** 未使用但要保留：Python 里有一个 `_ota_cond`，数据里可能还有引用。 */
export function _otaCond(s: State, desc: string): boolean | null {
  const m = /任一(.*?)OTA 黏性\s*([≥<=]+)\s*([\d.]+)/.exec(desc);
  if (!m) return null;
  const kind = m[1].trim();
  const op = m[2];
  const val = parseFloat(m[3]);
  let pool = s.ota;
  if (kind === "女友粉") pool = pool.filter((o) => o.fan_type === "女友粉");
  else if (kind === "男性") pool = pool.filter((o) => o.gender === "男");
  else if (kind) return null;
  if (!pool.length) return false;
  const best = Math.max(...pool.map((o) => o.stick));
  return op.includes("≥") || op.includes(">") ? best >= val : best <= val;
}
