/**
 * 引擎对账测试：TS 版 vs Python 版，逐周逐字段比。
 *
 * 标准答案由 `tools/trace_dump.py` 生成（用 CPython 跑同一批种子）。
 * 任何一处算法漂了，**第一周就会对不上**——因为 rng 调用次数一变，后面全部错位。
 *
 * 跑法：
 *   node --experimental-strip-types app/test/trace.test.ts
 *
 * 数据直接从 ../data 读盘（不在浏览器里，所以可以用 node:fs）。
 */

import { readFileSync, readdirSync, statSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import { PyRandom } from "../src/core/rng.ts";
import {
  loadWorld,
  newState,
  doWeek,
  judge,
  type RawFiles,
} from "../src/core/engine.ts";
import type { State } from "../src/core/types.ts";

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(HERE, "..", "..");
const DATA = join(ROOT, "data");

// ---------------------------------------------------------------- 读数据

function readJson(p: string): any {
  return JSON.parse(readFileSync(p, "utf8"));
}

/** 把 data/ 摊平成 `相对路径 -> JSON`，键的形状和 Python 的 open 调用一致。 */
function loadDataFiles(): RawFiles {
  const files: RawFiles = {};
  files["intro.json"] = readJson(join(DATA, "intro.json"));
  files["endings.json"] = readJson(join(DATA, "endings.json"));
  files["ota_memory.json"] = readJson(join(DATA, "ota_memory.json"));
  files["ota_pool.json"] = readJson(join(DATA, "ota_pool.json"));
  files["idol_names.json"] = readJson(join(DATA, "idol_names.json"));
  for (const fn of readdirSync(join(DATA, "cards")).sort()) {
    if (fn.endsWith(".json")) files[`cards/${fn}`] = readJson(join(DATA, "cards", fn));
  }
  for (const fn of readdirSync(join(DATA, "storylines")).sort()) {
    const p = join(DATA, "storylines", fn);
    // Python 的 os.listdir 只列文件名，目录会被 .endswith(".json") 挡掉；
    // 但 node 的 readdirSync 也会返回目录名，所以要显式判一下。
    if (fn.endsWith(".json") && statSync(p).isFile()) {
      files[`storylines/${fn}`] = readJson(p);
    }
  }
  return files;
}

// ---------------------------------------------------------------- 归一化

/** 和 trace_dump.py 的 norm() 一一对应：set → 排序数组、浮点 9 位有效数字。 */
function norm(v: any): any {
  if (v instanceof Set) return [...v].map(String).sort();
  if (Array.isArray(v)) return v.map(norm);
  if (v && typeof v === "object") {
    const out: Record<string, any> = {};
    for (const k of Object.keys(v).sort()) out[String(k)] = norm(v[k]);
    return out;
  }
  if (typeof v === "number" && !Number.isInteger(v)) {
    // Python: float(f"{v:.9g}")
    return Number(v.toPrecision(9));
  }
  return v;
}

function snap(s: State): Record<string, any> {
  const out: Record<string, any> = {};
  for (const k of Object.keys(s)) {
    if (k === "_rng") continue;
    out[k] = norm(s[k]);
  }
  return out;
}

// ---------------------------------------------------------------- 比对

let fails = 0;
let checks = 0;

function fail(msg: string): void {
  fails += 1;
  if (fails <= 40) console.log("  ✗ " + msg);
}

/** 递归比对两个 JSON 形状的值，报出第一条差异路径。 */
function diff(path: string, a: any, b: any): string | null {
  checks += 1;
  if (a === b) return null;
  const ta = a === null ? "null" : typeof a;
  const tb = b === null ? "null" : typeof b;
  if (ta !== tb) return `${path}: 类型不同 py=${ta}(${JSON.stringify(a)}) ts=${tb}(${JSON.stringify(b)})`;
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
    for (const k of ka) {
      if (!(k in b)) return `${path}.${k}: TS 缺这个键（py 有）`;
    }
    for (const k of kb) {
      if (!(k in a)) return `${path}.${k}: Python 缺这个键（ts 有）`;
    }
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
  return `${path}: py=${JSON.stringify(a)} ts=${JSON.stringify(b)}`;
}

// ---------------------------------------------------------------- 主流程

const expectedPath = join(HERE, "trace_expected.json");
let raw: string;
try {
  raw = readFileSync(expectedPath, "utf8");
} catch {
  console.error(`缺标准答案：${expectedPath}`);
  console.error("先跑：python tools/trace_dump.py > app/test/trace_expected.json");
  process.exit(1);
}
const expected = JSON.parse(raw);

const files = loadDataFiles();
const world = loadWorld(files);
console.log(`世界载入：${world.cards.length} 张卡、${world.lines.length} 条剧情线`);

for (const run of expected.runs) {
  const seed = run.seed;
  const rng = new PyRandom(seed);
  const s = newState(world, null, null, rng);
  const weeks = run.weeks as any[];

  const d0 = diff(`seed${seed}.w0.state`, weeks[0].state, snap(s));
  if (d0) fail(d0);

  const total = Number(s.weeks_total);
  for (let i = 0; i < total; i++) {
    const info = doWeek(s, world, rng, null);
    const w = weeks[i + 1];
    if (!w) {
      fail(`seed${seed}.w${i + 1}: 标准答案里没有这一周`);
      break;
    }
    if (info.tier !== w.tier) fail(`seed${seed}.w${i + 1}.tier: py=${w.tier} ts=${info.tier}`);
    if (Math.abs(Number(info.score.toPrecision(9)) - w.score) > 1e-9) {
      fail(`seed${seed}.w${i + 1}.score: py=${w.score} ts=${info.score}`);
    }
    const dReport = diff(`seed${seed}.w${i + 1}.report`, w.report, norm(info.report));
    if (dReport) {
      fail(dReport);
      // 报告一错，后面状态必然全错，这一局到此为止，省得刷屏
      break;
    }
    const d = diff(`seed${seed}.w${i + 1}.state`, w.state, snap(s));
    if (d) {
      fail(d);
      break;
    }
  }

  const [name, early] = judge(s, world, s.true_talk ?? 0);
  if (name !== run.ending) fail(`seed${seed}.ending: py=${run.ending} ts=${name}`);
  if (early !== run.early) fail(`seed${seed}.early: py=${run.early} ts=${early}`);
}

if (fails === 0) {
  console.log(`✓ trace: ${checks} 项全对（${expected.runs.length} 个种子 × ${expected.runs[0].total} 周）`);
} else {
  console.log(`\n✗ trace: ${fails} 处不一致（共比对 ${checks} 项）`);
  process.exit(1);
}
