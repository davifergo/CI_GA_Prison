<script lang="ts">
  import type { SweepPoint } from '../lib/ga.worker';
  import { ORDER, STYLE, type Column } from '../lib/strategies';
  import Swatch from './Swatch.svelte';

  let { points }: { points: SweepPoint[] } = $props();
  let cw = $state(680);
  const W = $derived(Math.max(300, Math.min(820, cw)));
  const L = 36, R = 14, T = 14, H1 = 190, GAP = 34, CELL = 9;
  const runs = $derived(points[0]?.payoffs.length ?? 0);
  const H2 = $derived(runs * (CELL + 2));
  const H = $derived(T + H1 + GAP + H2 + 22);
  const pMax = $derived(points[points.length - 1]?.p || 0.1);
  const x = (p: number) => L + 14 + (p / pMax) * (W - L - R - 28);
  const y = (v: number) => T + (1 - (v - 0.5) / 2.75) * H1; // 0.5 .. 3.25
  const med = (a: number[]) => { const s = [...a].sort((p, q) => p - q); const m = s.length >> 1; return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2; };
  const medPath = $derived('M' + points.map((pt) => `${x(pt.p).toFixed(1)} ${y(med(pt.payoffs)).toFixed(1)}`).join('L'));
  const present = $derived(ORDER.filter((c) => points.some((pt) => pt.dominant.includes(c))));
  const m2 = $derived(points.some((pt) => pt.dominant.some((d) => d.startsWith('fam:'))));
  const FAM: Record<string, string> = { 'fam:coop': '2.5 or more', 'fam:brass': '1.5 to 2.5', 'fam:defect': 'under 1.5' };
  const fill = (d: string) => (d.startsWith('fam:') ? `url(#pat-s0-${d.slice(4)})` : STYLE[d as Column].fill);
  const famsPresent = $derived(Object.keys(FAM).filter((f) => points.some((pt) => pt.dominant.includes(f))));
  let hover: SweepPoint | null = $state(null);
</script>

<figure bind:clientWidth={cw}>
  <svg viewBox="0 0 {W} {H}" role="img" aria-label="Final mean payoff and dominant strategy at each noise level">
    {#each [1, 2, 3] as v}
      <line x1={L} x2={W - R} y1={y(v)} y2={y(v)} class="grid" />
      <text x={L - 5} y={y(v) + 3} class="ax" text-anchor="end">{v}</text>
    {/each}
    <text x={L} y={T - 1} class="ttl">Mean payoff, last 100 generations</text>
    <path d={medPath} class="med" />
    {#each points as pt, i}
      <g role="presentation" onpointerenter={() => (hover = pt)} onpointerleave={() => (hover = null)}>
        <rect x={x(pt.p) - Math.min(12, (W - L) / points.length / 2)} y={T} width={Math.min(24, (W - L) / points.length)} height={H1 + GAP + H2} class="hit" />
        {#each pt.payoffs as v, r}
          <circle cx={x(pt.p) + ((r % 5) - 2) * 2.2} cy={y(v)} r="2.3" class="dot" />
        {/each}
        {#each pt.dominant as d, r}
          <rect x={x(pt.p) - CELL / 2} y={T + H1 + GAP + r * (CELL + 2)} width={CELL} height={CELL} style="fill:{fill(d)}" class="cell" />
        {/each}
        <text x={x(pt.p)} y={H - 6} class="ax" text-anchor="middle">{i % 2 === 0 || (points.length < 8 && W > 500) ? pt.p : ''}</text>
      </g>
    {/each}
    <text x={L} y={T + H1 + GAP - 8} class="ttl">{m2 ? 'Final most frequent genome, by what it earns against itself' : 'Most frequent strategy, one square per run'}</text>
  </svg>
  <figcaption class="caption">
    {#if hover}
      <span class="mono">p = {hover.p}</span>: median payoff <span class="mono">{med(hover.payoffs).toFixed(3)}</span>;
      {#if m2}
        the final most frequent genome holds {hover.topShare?.map((x) => Math.round(x * 100) + '%').join(', ')} of the gallery.
      {:else}
        most frequent: {ORDER.filter((c) => hover!.dominant.includes(c)).map((c) => `${c} in ${hover!.dominant.filter((d) => d === c).length}`).join(', ')} of {hover.payoffs.length} runs.
      {/if}
    {:else}
      Dots: one per run; line: median. Point at a level for details. Runs use independent seeds, as in the report.
    {/if}
    <span class="legend">
      {#if m2}
        {#each famsPresent as f}<span class="li"><svg width="14" height="14" aria-hidden="true"><rect x="0.5" y="0.5" width="13" height="13" style="fill:{fill(f)};stroke:var(--ink)" /></svg> earns {FAM[f]} against itself</span>{/each}
      {:else}
        {#each present as c}<span class="li"><Swatch col={c} /> <span class="mono">{c}</span></span>{/each}
      {/if}
    </span>
  </figcaption>
</figure>

<style>
  figure { margin: 0; max-width: 820px; }
  svg { width: 100%; height: auto; display: block; }
  .grid { stroke: var(--rule); stroke-width: 0.6; }
  .ax { font-family: var(--font-mono); font-size: 10px; fill: var(--ink-3); }
  .ttl { font-size: 10.5px; font-variant-caps: all-small-caps; letter-spacing: 0.07em; fill: var(--ink-2); }
  .med { fill: none; stroke: var(--ink); stroke-width: 1.4; }
  .dot { fill: var(--paper); stroke: var(--ink); stroke-width: 1; }
  .cell { stroke: var(--ink); stroke-width: 0.6; }
  .hit { fill: transparent; }
  g:hover .hit { fill: var(--brass-tint); opacity: 0.5; }
  .legend { display: flex; flex-wrap: wrap; gap: 0.3rem 1rem; font-size: 0.85rem; margin-top: 0.4rem; color: var(--ink); }
  .legend .li { display: flex; align-items: center; gap: 0.35rem; }
</style>
