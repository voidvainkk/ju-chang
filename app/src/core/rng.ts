/**
 * CPython `random.Random` 的精确移植（MT19937）。
 *
 * 为什么要一模一样：游戏里所有随机（抽卡、OTA 取名、回考真值、结局判定里的骰子）
 * 都是 `random.Random(seed)`。移植成 JS 以后，只要算法一致，
 * 同一个种子就该产出同一局——这就是翻译引擎时唯一的对账手段：
 * Python 跑 seed=7 到第 12 屏，TS 也跑 seed=7 到第 12 屏，两边状态逐字段比。
 *
 * 覆盖到的 API（game/ 里用到的全部）：
 *   random() choice() choices() shuffle() sample() randrange() uniform()
 *   getrandbits() seed() getstate() setstate()
 *
 * 未覆盖：gauss / betavariate 等分布采样（项目里没用）。
 */

const N = 624;
const M = 397;
const MATRIX_A = 0x9908b0df;
const UPPER_MASK = 0x80000000;
const LOWER_MASK = 0x7fffffff;

export class PyRandom {
  private mt: Uint32Array;
  private mti: number;

  constructor(seed?: number | string) {
    this.mt = new Uint32Array(N);
    this.mti = N + 1; // 未初始化
    if (seed !== undefined) this.seed(seed);
  }

  /* ---------------------------------------------------------------- 种子 */

  seed(arg: number | string): void {
    if (typeof arg === 'string') {
      // CPython：str 走 sha512 摘要成 32 位字数组
      throw new Error('PyRandom: 字符串种子没实现，项目里只用整数');
    }
    // CPython random_seed：把整数按小端 32 位字切成 key 数组
    let n = Math.abs(Math.trunc(arg));
    const key: number[] = [];
    if (n === 0) key.push(0);
    while (n > 0) {
      key.push(n % 0x100000000);
      n = Math.floor(n / 0x100000000);
    }
    this.initByArray(key);
  }

  /** MT19937 的 init_genrand */
  private initGenrand(s: number): void {
    this.mt[0] = s >>> 0;
    for (let i = 1; i < N; i++) {
      const prev = this.mt[i - 1];
      this.mt[i] = (Math.imul(prev ^ (prev >>> 30), 1812433253) + i) >>> 0;
    }
    this.mti = N;
  }

  /** MT19937 的 init_by_array */
  private initByArray(key: number[]): void {
    this.initGenrand(19650218);
    let i = 1;
    let j = 0;
    let k = Math.max(N, key.length);
    for (; k; k--) {
      const prev = this.mt[i - 1];
      this.mt[i] =
        (((this.mt[i] ^ Math.imul(prev ^ (prev >>> 30), 1664525)) >>> 0) +
          key[j] +
          j) >>>
        0;
      i++;
      j++;
      if (i >= N) {
        this.mt[0] = this.mt[N - 1];
        i = 1;
      }
      if (j >= key.length) j = 0;
    }
    for (k = N - 1; k; k--) {
      const prev = this.mt[i - 1];
      this.mt[i] =
        (((this.mt[i] ^ Math.imul(prev ^ (prev >>> 30), 1566083941)) >>> 0) - i) >>>
        0;
      i++;
      if (i >= N) {
        this.mt[0] = this.mt[N - 1];
        i = 1;
      }
    }
    this.mt[0] = 0x80000000;
    this.mti = N;
  }

  /* ------------------------------------------------------------ 核心取值 */

  /** genrand_uint32：一个 32 位无符号随机数 */
  private nextUint32(): number {
    let y: number;
    if (this.mti >= N) {
      if (this.mti === N + 1) this.initGenrand(5489); // 默认种子
      let kk = 0;
      for (; kk < N - M; kk++) {
        y = (this.mt[kk] & UPPER_MASK) | (this.mt[kk + 1] & LOWER_MASK);
        this.mt[kk] = this.mt[kk + M] ^ (y >>> 1) ^ (y & 1 ? MATRIX_A : 0);
      }
      for (; kk < N - 1; kk++) {
        y = (this.mt[kk] & UPPER_MASK) | (this.mt[kk + 1] & LOWER_MASK);
        this.mt[kk] =
          this.mt[kk + (M - N)] ^ (y >>> 1) ^ (y & 1 ? MATRIX_A : 0);
      }
      y = (this.mt[N - 1] & UPPER_MASK) | (this.mt[0] & LOWER_MASK);
      this.mt[N - 1] = this.mt[M - 1] ^ (y >>> 1) ^ (y & 1 ? MATRIX_A : 0);
      this.mti = 0;
    }
    y = this.mt[this.mti++];
    // 搅动
    y ^= y >>> 11;
    y ^= (y << 7) & 0x9d2c5680;
    y ^= (y << 15) & 0xefc60000;
    y ^= y >>> 18;
    return y >>> 0;
  }

  /** random()：53 位精度，等价于 CPython 的 genrand_res53 */
  random(): number {
    const a = this.nextUint32() >>> 5;
    const b = this.nextUint32() >>> 6;
    return (a * 67108864.0 + b) / 9007199254740992.0;
  }

  /** getrandbits(k)：完全照 CPython 的位拼法 */
  getrandbits(k: number): number {
    if (k <= 0) throw new Error('getrandbits: k 必须为正');
    if (k <= 32) {
      return this.nextUint32() >>> (32 - k);
    }
    const words = Math.ceil(k / 32);
    const lastBits = k % 32;
    let v = BigInt(0);
    for (let i = 0; i < words; i++) {
      let r = this.nextUint32();
      if (i === words - 1 && lastBits !== 0) {
        r = r >>> (32 - lastBits);
      }
      v |= BigInt(r) << BigInt(32 * i);
    }
    return Number(v);
  }

  /** _randbelow_with_getrandbits：拒绝采样，跟 CPython 逐位一致 */
  private randBelow(n: number): number {
    if (n <= 0) throw new Error('randBelow: n 必须为正');
    const k = bitLength(n);
    let r = this.getrandbits(k);
    while (r >= n) r = this.getrandbits(k);
    return r;
  }

  /* -------------------------------------------------------------- 公开 API */

  randrange(
    start: number,
    stop?: number,
    step: number = 1,
  ): number {
    let lo = 0;
    let hi: number;
    if (stop === undefined) {
      hi = start;
    } else {
      lo = start;
      hi = stop;
    }
    const width = hi - lo;
    if (step === 1) return lo + this.randBelow(width);
    const nn = Math.floor((width + step - 1) / step);
    return lo + step * this.randBelow(nn);
  }

  choice<T>(seq: ArrayLike<T>): T {
    if (seq.length === 0) throw new Error('choice: 序列为空');
    return seq[this.randBelow(seq.length)];
  }

  shuffle<T>(x: T[]): void {
    for (let i = x.length - 1; i > 0; i--) {
      const j = this.randBelow(i + 1);
      const tmp = x[i];
      x[i] = x[j];
      x[j] = tmp;
    }
  }

  /**
   * sample(population, k)：CPython 按 setsize 走两条路，取出的数不同，必须照抄。
   *   setsize = 21，k > 5 时再加 4 ** ceil(log(k*3, 4))
   *   n <= setsize → pool 算法（复制一份，抽中的换到末尾）
   *   否则 → set 算法（反复抽直到不重复）
   */
  sample<T>(population: T[], k: number): T[] {
    const n = population.length;
    if (k < 0 || k > n) throw new Error('sample: k 越界');
    let setsize = 21;
    if (k > 5) setsize += Math.pow(4, Math.ceil(Math.log(k * 3) / Math.log(4)));
    const result: T[] = new Array(k);
    if (n <= setsize) {
      const pool = population.slice();
      for (let i = 0; i < k; i++) {
        const j = this.randBelow(n - i);
        result[i] = pool[j];
        pool[j] = pool[n - i - 1];
      }
      return result;
    }
    const selected = new Set<number>();
    for (let i = 0; i < k; i++) {
      let j = this.randBelow(n);
      while (selected.has(j)) j = this.randBelow(n);
      selected.add(j);
      result[i] = population[j];
    }
    return result;
  }

  /** choices(population, weights, k)：无权重走 floor(random()*n)，有走累积二分 */
  choices<T>(population: ArrayLike<T>, weights?: ArrayLike<number>, k = 1): T[] {
    const n = population.length;
    if (n === 0) throw new Error('choices: 序列为空');
    const out: T[] = new Array(k);
    if (!weights) {
      for (let i = 0; i < k; i++) {
        out[i] = population[Math.floor(this.random() * n)];
      }
      return out;
    }
    const cum: number[] = new Array(n);
    let acc = 0;
    for (let i = 0; i < n; i++) {
      acc += weights[i];
      cum[i] = acc;
    }
    const total = cum[n - 1];
    for (let i = 0; i < k; i++) {
      out[i] = population[bisectRight(cum, this.random() * total)];
    }
    return out;
  }

  uniform(a: number, b: number): number {
    return a + (b - a) * this.random();
  }

  /* ------------------------------------------------------------ 存档状态 */

  getstate(): { mt: number[]; mti: number } {
    return { mt: Array.from(this.mt), mti: this.mti };
  }

  setstate(st: { mt: number[]; mti: number }): void {
    this.mt.set(st.mt);
    this.mti = st.mti;
  }
}

/** CPython int.bit_length() */
function bitLength(n: number): number {
  if (n <= 0) return 0;
  return Math.floor(Math.log2(n)) + 1;
}

/** bisect.bisect_right */
function bisectRight(a: number[], x: number): number {
  let lo = 0;
  let hi = a.length;
  while (lo < hi) {
    const mid = (lo + hi) >>> 1;
    if (x < a[mid]) hi = mid;
    else lo = mid + 1;
  }
  return lo;
}
