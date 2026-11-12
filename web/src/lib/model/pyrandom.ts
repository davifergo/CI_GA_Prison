// Python's `random` module (MT19937), ported so that a GA seeded with s here draws the same
// numbers as `random.seed(s)` in main.py. Only what DEAP's operators use is implemented:
// random(), getrandbits(k <= 32), randbelow(n) (behind randint and choice).

export class PyRandom {
  private mt = new Uint32Array(624);
  private idx = 625;

  constructor(seed: number) {
    this.seed(seed);
  }

  /** random.seed(int): init_by_array with the 32-bit words of |seed| (little-endian). */
  seed(seed: number): void {
    let n = BigInt(Math.abs(Math.trunc(seed)));
    const key: number[] = [];
    do {
      key.push(Number(n & 0xffffffffn));
      n >>= 32n;
    } while (n > 0n);
    this.initByArray(key);
  }

  private initGenrand(s: number): void {
    const mt = this.mt;
    mt[0] = s >>> 0;
    for (let i = 1; i < 624; i++) {
      const prev = mt[i - 1] ^ (mt[i - 1] >>> 30);
      mt[i] = (Math.imul(1812433253, prev) + i) >>> 0;
    }
    this.idx = 624;
  }

  private initByArray(key: number[]): void {
    const mt = this.mt;
    this.initGenrand(19650218);
    let i = 1, j = 0;
    for (let k = Math.max(624, key.length); k > 0; k--) {
      const prev = mt[i - 1] ^ (mt[i - 1] >>> 30);
      mt[i] = ((mt[i] ^ Math.imul(prev, 1664525)) + key[j] + j) >>> 0;
      i++; j++;
      if (i >= 624) { mt[0] = mt[623]; i = 1; }
      if (j >= key.length) j = 0;
    }
    for (let k = 623; k > 0; k--) {
      const prev = mt[i - 1] ^ (mt[i - 1] >>> 30);
      mt[i] = ((mt[i] ^ Math.imul(prev, 1566083941)) - i) >>> 0;
      i++;
      if (i >= 624) { mt[0] = mt[623]; i = 1; }
    }
    mt[0] = 0x80000000;
  }

  private genrand(): number {
    const mt = this.mt;
    if (this.idx >= 624) {
      let kk = 0;
      for (; kk < 624 - 397; kk++) {
        const y = (mt[kk] & 0x80000000) | (mt[kk + 1] & 0x7fffffff);
        mt[kk] = mt[kk + 397] ^ (y >>> 1) ^ (y & 1 ? 0x9908b0df : 0);
      }
      for (; kk < 623; kk++) {
        const y = (mt[kk] & 0x80000000) | (mt[kk + 1] & 0x7fffffff);
        mt[kk] = mt[kk + (397 - 624)] ^ (y >>> 1) ^ (y & 1 ? 0x9908b0df : 0);
      }
      const y = (mt[623] & 0x80000000) | (mt[0] & 0x7fffffff);
      mt[623] = mt[396] ^ (y >>> 1) ^ (y & 1 ? 0x9908b0df : 0);
      this.idx = 0;
    }
    let y = mt[this.idx++];
    y ^= y >>> 11;
    y ^= (y << 7) & 0x9d2c5680;
    y ^= (y << 15) & 0xefc60000;
    y ^= y >>> 18;
    return y >>> 0;
  }

  /** random.random(): 53-bit float in [0, 1). */
  random(): number {
    const a = this.genrand() >>> 5, b = this.genrand() >>> 6;
    return (a * 67108864 + b) / 9007199254740992;
  }

  getrandbits(k: number): number {
    return this.genrand() >>> (32 - k);
  }

  /** random._randbelow(n) for 0 < n < 2^32. */
  randbelow(n: number): number {
    const k = 32 - Math.clz32(n); // n.bit_length()
    let r = this.getrandbits(k);
    while (r >= n) r = this.getrandbits(k);
    return r;
  }

  randint(a: number, b: number): number {
    return a + this.randbelow(b - a + 1);
  }
}
