/**
 * CPython random 的移植自检。
 *
 * 参考值由 Python 3 的 random.Random(seed) 生成，见 test/rng_expected.json。
 * 只要这里的断言全绿，TS 版随机数就和 Python 逐位一致，
 * 后面移植引擎时「同种子跑同一局」才成立。
 *
 * 跑：node --experimental-strip-types app/test/rng.test.ts
 * （Node 22+ 可以直接跑 TS）
 */
import { strict as assert } from 'node:assert';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { PyRandom } from '../src/core/rng.ts';

const here = dirname(fileURLToPath(import.meta.url));
const expected = JSON.parse(
  readFileSync(join(here, 'rng_expected.json'), 'utf-8'),
) as Record<string, any>;

let checks = 0;
function eq(actual: unknown, want: unknown, label: string): void {
  checks++;
  try {
    assert.deepEqual(actual, want);
  } catch {
    console.error(`✗ ${label}`);
    console.error('  want:', JSON.stringify(want));
    console.error('  got :', JSON.stringify(actual));
    throw new Error(`rng mismatch: ${label}`);
  }
}

function r17(x: number): number {
  // Python round(x, 17) 与 JS 的双精度打印可能差最后一位，按 1e-15 比
  return Math.round(x * 1e15) / 1e15;
}

for (const [seed, want] of Object.entries(expected)) {
  const s = Number(seed);
  const tag = `seed=${s}`;

  {
    const r = new PyRandom(s);
    const got = [];
    for (let i = 0; i < 5; i++) got.push(r17(r.random()));
    eq(got, (want.first5_random as number[]).map(r17), `${tag} random()`);
  }
  {
    const r = new PyRandom(s);
    const got = [];
    for (let i = 0; i < 5; i++) got.push(r.getrandbits(32));
    eq(got, want.first5_int, `${tag} getrandbits(32)`);
  }
  {
    const r = new PyRandom(s);
    const got = [];
    for (let i = 0; i < 5; i++) got.push(r.getrandbits(16));
    eq(got, want.bits16, `${tag} getrandbits(16)`);
  }
  {
    const r = new PyRandom(s);
    const got = [];
    for (let i = 0; i < 3; i++) got.push(r.getrandbits(64));
    eq(got, want.bits64, `${tag} getrandbits(64)`);
  }
  {
    const r = new PyRandom(s);
    const got = [];
    for (let i = 0; i < 8; i++) got.push(r.randrange(0, 100));
    eq(got, want.randrange, `${tag} randrange(0,100)`);
  }
  {
    const r = new PyRandom(s);
    const got = [];
    for (let i = 0; i < 6; i++) got.push(r.randrange(3, 90, 5));
    eq(got, want.randrange_step, `${tag} randrange(3,90,5)`);
  }
  {
    const r = new PyRandom(s);
    const arr = Array.from({ length: 12 }, (_, i) => i);
    r.shuffle(arr);
    eq(arr, want.shuffle12, `${tag} shuffle`);
  }
  {
    const r = new PyRandom(s);
    const pool = Array.from({ length: 10 }, (_, i) => i);
    eq(r.sample(pool, 3), want.sample_small, `${tag} sample(n=10,k=3)`);
  }
  {
    const r = new PyRandom(s);
    const pool = Array.from({ length: 200 }, (_, i) => i);
    eq(r.sample(pool, 30), want.sample_big, `${tag} sample(n=200,k=30)`);
  }
  {
    const r = new PyRandom(s);
    const pool = ['a', 'b', 'c', 'd', 'e', 'f', 'g'];
    const got = [];
    for (let i = 0; i < 10; i++) got.push(r.choice(pool));
    eq(got, want.choice, `${tag} choice`);
  }
  {
    const r = new PyRandom(s);
    const pool = Array.from({ length: 6 }, (_, i) => i);
    eq(
      r.choices(pool, [1, 2, 3, 4, 5, 6], 10),
      want.choices_w,
      `${tag} choices(weights)`,
    );
  }
  {
    const r = new PyRandom(s);
    const pool = Array.from({ length: 6 }, (_, i) => i);
    eq(r.choices(pool, undefined, 8), want.choices_now, `${tag} choices(no weights)`);
  }
  {
    const r = new PyRandom(s);
    const got = [];
    for (let i = 0; i < 5; i++) got.push(r17(r.uniform(-3, 7)));
    eq(got, (want.uniform as number[]).map(r17), `${tag} uniform`);
  }
  {
    // 存档往返：getstate/setstate 之后必须接着原来的序列
    const r = new PyRandom(s);
    for (let i = 0; i < 7; i++) r.random();
    const st = r.getstate();
    const a = [r.random(), r.random(), r.random()];
    r.setstate(st);
    const b = [r.random(), r.random(), r.random()];
    checks++;
    assert.deepEqual(a, b, `${tag} getstate/setstate 不连续`);
  }
}

console.log(`✓ rng: ${checks} 项全对（${Object.keys(expected).length} 个种子）`);
