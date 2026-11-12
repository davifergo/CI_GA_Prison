// Correctly rounded fused multiply-add, a*b + c with a single rounding.
//
// NumPy's matrix products go through OpenBLAS kernels that use FMA instructions. To get the
// same payoff matrix and fitness values as main.py to the last bit (which decides exact ties
// in tournaments when there is no noise), the port has to round the same way. JavaScript has
// no Math.fma, so it is emulated with error-free transformations and rounding to odd
// (Boldo & Melquiond, "Emulation of FMA and correctly rounded sums: proved algorithms using
// rounding to odd", IEEE Trans. Computers 57(4), 2008).

const SPLIT = 134217729; // 2^27 + 1 (Veltkamp split)

const f64 = new Float64Array(1);
const u64 = new BigUint64Array(f64.buffer);

/** Exact product: a*b = hi + lo (Dekker). */
function twoProd(a: number, b: number): [number, number] {
  const hi = a * b;
  let t = SPLIT * a;
  const ah = t - (t - a), al = a - ah;
  t = SPLIT * b;
  const bh = t - (t - b), bl = b - bh;
  const lo = al * bl - (hi - ah * bh - al * bh - ah * bl);
  return [hi, lo];
}

/** Exact sum: a + b = s + e (Knuth). */
function twoSum(a: number, b: number): [number, number] {
  const s = a + b;
  const bb = s - a;
  const e = (a - (s - bb)) + (b - bb);
  return [s, e];
}

/** x + y rounded to odd: if inexact, the neighbour (towards the exact value) with an odd last bit. */
function addRoundOdd(x: number, y: number): number {
  const [s, e] = twoSum(x, y);
  if (e === 0 || !Number.isFinite(s)) return s;
  f64[0] = s;
  if ((u64[0] & 1n) === 1n) return s; // already odd
  // move one ulp towards e (towards the exact sum); for s != 0 that flips the last bit to odd
  const towardsLarger = (e > 0) === (s > 0);
  u64[0] = towardsLarger ? u64[0] + 1n : u64[0] - 1n;
  return f64[0];
}

export function fma(a: number, b: number, c: number): number {
  const [uh, ul] = twoProd(a, b);
  if (ul === 0) return uh + c;
  const [th, tl] = twoSum(c, uh);
  return th + addRoundOdd(tl, ul);
}
