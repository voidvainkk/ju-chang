/**
 * 流程对账测试：TS 版 `loop.ts` vs Python 版 `loop.py`，**逐屏逐字段**比。
 *
 * 标准答案由 `tools/loop_trace.py` 生成（用 CPython 跑同一批种子、下同一串选择）。
 * 和 `trace.test.ts` 的区别：那份只比每周结算时的状态，这份比每一屏的标题、
 * 正文、按钮文案、数值增减——`loop.py` 里 4606 个汉字文案，少一个标点都算错。
 *
 * 跑法：
 *   node --experimental-strip-types app/test/loop.test.ts
 */

import { readFileSync, readdirSync, statSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import { Game, cleanStep } from "../src/core/loop.ts";
import type { RawFiles } from "../src/core/engine.ts";

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(HERE, "..", "..");
const DATA = join(ROOT, "data");

// ---------------------------------------------------------------- 读数据

function readJson(p: string): any {
  return JSON.parse(readFileSync(p, "utf8"));
}

/**
 * 和 `loop_trace.py` 里 Python 读到的文件集一致：
 * 引擎那 5 个 + cards/*.json + storylines/*.json + stances/outside + 结局.md。
 */
function loadDataFiles(): RawFiles {
  const files: RawFiles = {};
  for (const fn of ["intro.json", "endings.json", "ota_memory.json", "ota_pool.json", "idol_names.json", "stances.json", "outside.json"]) {
    files[fn] = readJson(join(DATA, fn));
  }
  for (const fn of readdirSync(join(DATA, "cards")).sort()) {
    if (fn.endsWith(".json")) files[`cards/${fn}`] = readJson(join(DATA, "cards", fn));
  }
  for (const fn of readdirSync(join(DATA, "storylines")).sort()) {
    const p = join(DATA, "storylines", fn);
    if (fn.endsWith(".json") && statSync(p).isFile()) {
      files[`storylines/${fn}`] = readJson(p);
    }
  }
  // 结局正文从 markdown 读（Python 版是 open('../结局.md')）。
  // Python 的文本模式做 universal newlines，会把 CRLF 折成 LF；Node 不会，
  // 不折的话结局正文每一处换行都会对不上（py="\n\n" vs ts="\r\n\r\n"）。
  files["结局.md"] = readFileSync(join(ROOT, "结局.md"), "utf8").replace(/\r\n/g, "\n");
  return files;
}

// ---------------------------------------------------------------- 归一化

/** 和 `loop_trace.py` 的 norm() 一一对应：set → 排序数组、浮点 9 位有效数字。 */
function norm(v: any): any {
  if (v instanceof Set) return [...v].map(String).sort();
  if (Array.isArray(v)) return v.map(norm);
  if (v && typeof v === "object") {
    const out: Record<string, any> = {};
    for (const k of Object.keys(v).sort()) out[String(k)] = norm(v[k]);
    return out;
  }
  if (typeof v === "number" && !Number.isInteger(v)) return Number(v.toPrecision(9));
  return v;
}

// ---------------------------------------------------------------- 比对

let fails = 0;
let checks = 0;

function fail(msg: string): void {
  fails += 1;
  if (fails <= 30) console.log("  ✗ " + msg);
}

function diff(path: string, a: any, b: any): string | null {
  checks += 1;
  if (a === b) return null;
  const ta = a === null ? "null" : typeof a;
  const tb = b === null ? "null" : typeof b;
  if (ta !== tb) {
    return `${path}: 类型不同 py=${ta}(${JSON.stringify(a)?.slice(0, 120)}) ts=${tb}(${JSON.stringify(b)?.slice(0, 120)})`;
  }
  if (Array.isArray(a) && Array.isArray(b)) {
    if (a.length !== b.length) return `${path}: 数组长度 py=${a.length} ts=${b.length}`;
    for (let i = 0; i < a.length; i++) {
      const d = diff(`${path}[${i}]`, a[i], b[i]);
      if (d) return d;
    }
    return null;
  }
  if (ta === "object") {
    const ka = Object.keys(a);
    const kb = Object.keys(b);
    for (const k of ka) if (!(k in b)) return `${path}.${k}: TS 缺这个键`;
    for (const k of kb) if (!(k in a)) return `${path}.${k}: TS 多这个键`;
    for (const k of ka) {
      const d = diff(`${path}.${k}`, a[k], b[k]);
      if (d) return d;
    }
    return null;
  }
  if (typeof a === "number" && typeof b === "number") {
    if (Math.abs(a - b) < 1e-9) return null;
    return `${path}: 数值 py=${a} ts=${b} (差 ${Math.abs(a - b)})`;
  }
  if (typeof a === "string" && typeof b === "string") {
    if (a === b) return null;
    // 指出第一处不同，方便定位是哪个文案写错了
    let i = 0;
    while (i < a.length && i < b.length && a[i] === b[i]) i++;
    const s = Math.max(0, i - 18);
    return (
      `${path}: 文案 py=${JSON.stringify(a.slice(s, s + 60))} ts=${JSON.stringify(b.slice(s, s + 60))}` +
      ` @${i}`
    );
  }
  return `${path}: py=${JSON.stringify(a)} ts=${JSON.stringify(b)}`;
}

// ---------------------------------------------------------------- 落子

/**
 * 脚本化落子：和 `loop_trace.py` 的 `_choose()` 逐条对应。
 * 两边只要屏幕一致、这里规则一致，就会走出同一条路。
 */
function choose(g: Game, step: Record<string, any>, n: number): void {
  const t = step.type;
  if (t === "name") {
    if (step.stage === "style") g.pickStyle(step.styles[0].id);
    else g.setName(step.candidates[0]);
    return;
  }
  if (t === "stance") {
    g.chooseStance(step.stances[0].id);
    return;
  }
  if (t === "end") return;
  if (t === "text" || t === "live" || t === "receipt" || t === "panel" || t === "bill") {
    g.advance();
    return;
  }
  if (t === "choice") {
    const opts = step.options || [];
    if (!opts.length) {
      g.advance();
      return;
    }
    const oid = opts[n % opts.length].id;
    const kind = step.kind;
    if (kind === "act") g.chooseAct(oid);
    else if (kind === "leave") g.chooseLeave(oid);
    else if (kind === "empty") g.chooseEmpty(oid);
    else if (kind === "offer") g.chooseOffer(oid);
    else g.advance();
    return;
  }
  if (t === "card" || t === "chat") {
    const opts = step.options || [];
    if (!opts.length) {
      g.advance();
      return;
    }
    const oid = step.rtalk
      ? // 恋爱谈一谈脚本局选第二项「只看当下」：季必须继续跑完，
        // 收场拍（前夜/撞破/办公室）才进得了基准——第一项现在是当场结季。
        opts[1 % opts.length].id
      : opts[n % opts.length].id;
    if (step.talk) g.chooseTalk(oid);
    else if (step.line) g.chooseStory(oid);
    else g.chooseCard(oid);
    return;
  }
  g.advance();
}

// ---------------------------------------------------------------- 主流程

const expectedPath = join(HERE, "loop_expected.json");
let raw = "";
try {
  raw = readFileSync(expectedPath, "utf8");
} catch {
  console.error(`缺标准答案：${expectedPath}`);
  console.error("先跑：python tools/loop_trace.py app/test/loop_expected.json");
  process.exit(1);
}
const expected = JSON.parse(raw);

const files = loadDataFiles();
const WORLD_SEED = expected.runs[0].seed;

for (const run of expected.runs) {
  const g = new Game(files, run.seed);
  const py = run.screens as any[];
  let i = 0;
  let stopped = false;

  for (; i < py.length; i++) {
    const cur = g.current();
    if (cur === null) {
      fail(`seed${run.seed}.s${i}: TS 没有第 ${i} 屏了（Python 还有 ${py.length - i} 屏）`);
      stopped = true;
      break;
    }
    const exp = py[i];
    if (exp.i !== i) {
      fail(`seed${run.seed}.s${i}: 标准答案的序号是 ${exp.i}`);
      stopped = true;
      break;
    }
    const dStep = diff(`seed${run.seed}.s${i}.step`, exp.step, norm(cleanStep(cur)));
    if (dStep) {
      fail(dStep);
      stopped = true;
      break;
    }
    const dSnap = diff(`seed${run.seed}.s${i}.snap`, exp.snap, norm(g.snapshot()));
    if (dSnap) {
      fail(dSnap);
      stopped = true;
      break;
    }
    if (cur.type === "end") break;
    // 落子用「这一屏的序号 + 1」当按钮下标——和 loop_trace.py 的
    // `n += 1; _choose(g, cur, n)` 同一条规则。别在这里再 i += 1，
    // for 语句自己会加（加两次就会隔屏跳过）。
    choose(g, cur, i + 1);
  }

  if (!stopped) {
    if (g.state?.ending !== run.ending) {
      fail(`seed${run.seed}.ending: py=${run.ending} ts=${g.state?.ending}`);
    }
    if (g.state?.week !== run.week) {
      fail(`seed${run.seed}.week: py=${run.week} ts=${g.state?.week}`);
    }
  }
  void WORLD_SEED;
}

const totalScreens = (expected.runs as any[]).reduce((a: number, r: any) => a + r.screens.length, 0);
if (fails === 0) {
  console.log(`✓ loop: ${checks} 项全对（${expected.runs.length} 个种子、${totalScreens} 屏）`);
} else {
  console.log(`\n✗ loop: ${fails} 处不一致（共比对 ${checks} 项）`);
  process.exit(1);
}
