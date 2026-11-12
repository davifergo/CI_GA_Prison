<script lang="ts">
  // Memory two, as in Figure 7 of the report: the share of the most frequent genome and the
  // number of distinct genomes per generation, and the mean payoff below.
  import { R, P } from '../lib/model/game';

  interface Point { gen: number; top: number; distinct: number; meanPayoff: number }
  let { history, nPop, minGens = 100 }: { history: Point[]; nPop: number; minGens?: number } = $props();

  let cw = $state(640);
  const W = $derived(Math.max(300, Math.min(900, cw)));
  const L = 34, T = 14;
  const Rm = $derived(cw < 500 ? 84 : 112);
  const H1 = $derived(cw < 500 ? 150 : 190), GAP = 30, H2 = 120, B = 24;
  const H = $derived(T + H1 + GAP + H2 + B);
  const last = $derived(history.length ? history[history.length - 1].gen : 0);
  const xMax = $derived(Math.max(minGens, last));
  const x = (g: number) => L + (g / xMax) * (W - L - Rm);
  const y1 = (f: number) => T + (1 - f) * H1;
  const top2 = $derived(T + H1 + GAP);
  const y2 = (v: number) => top2 + (1 - v / 5) * H2;

  const pts = $derived.by(() => {
    const k = Math.max(1, Math.ceil(history.length / 600));
    return history.filter((_, i) => i % k === 0 || i === history.length - 1);
  });
  const topArea = $derived(pts.length ? `M${x(pts[0].gen)} ${y1(0)}` + pts.map((p) => `L${x(p.gen).toFixed(1)} ${y1(p.top).toFixed(1)}`).join('') + `L${x(pts[pts.length - 1].gen)} ${y1(0)}Z` : '');
  const distinctPath = $derived(pts.length ? 'M' + pts.map((p) => `${x(p.gen).toFixed(1)} ${y1(p.distinct / nPop).toFixed(1)}`).join('L') : '');
  const payPath = $derived(pts.length ? 'M' + pts.map((p) => `${x(p.gen).toFixed(1)} ${y2(p.meanPayoff).toFixed(1)}`).join('L') : '');
  const xTicks = $derived.by(() => {
    const step = xMax <= 120 ? 20 : xMax <= 300 ? 50 : xMax <= 1200 ? 100 : 500;
    return Array.from({ length: Math.floor(xMax / step) + 1 }, (_, i) => i * step);
  });
  const end = $derived(history[history.length - 1]);

  let hover: Point | null = $state(null);
  let svgEl: SVGSVGElement | undefined = $state();
  function move(e: PointerEvent) {
    if (!svgEl || !history.length) return;
    const r = svgEl.getBoundingClientRect();
    const g = Math.round(((((e.clientX - r.left) / r.width) * W - L) / (W - L - Rm)) * xMax);
    hover = g >= 0 && g <= last ? history[Math.min(history.length - 1, g - history[0].gen)] ?? null : null;
  }
</script>

<figure class="fc" bind:clientWidth={cw}>
  <svg bind:this={svgEl} viewBox="0 0 {W} {H}" role="img" onpointermove={move} onpointerleave={() => (hover = null)}
    aria-label="Share of the most frequent genome and number of distinct genomes per generation, and the mean payoff">
    <text x={L} y={T - 4} class="ttl">Most frequent genome (share) · distinct genomes (count)</text>
    {#each [0, 0.5, 1] as f}
      <line x1={L} x2={W - Rm} y1={y1(f)} y2={y1(f)} class="grid" />
      <text x={L - 5} y={y1(f) + 3} class="ax" text-anchor="end">{f * 100}%</text>
    {/each}
    <path d={topArea} class="top" />
    <path d={distinctPath} class="distinct" />
    <rect x={L} y={T} width={x(last) - L} height={H1} class="frame" />
    {#if end}
      <text x={x(last) + 5} y={y1(end.top) + 4} class="lab">top {Math.round(end.top * 100)}%</text>
      <text x={x(last) + 5} y={Math.min(y1(end.distinct / nPop) + 4, T + H1 - 2) + (Math.abs(y1(end.distinct / nPop) - y1(end.top)) < 12 ? 12 : 0)} class="lab dl">{end.distinct} distinct</text>
    {/if}

    <text x={L} y={top2 - 8} class="ttl">Mean payoff per round</text>
    {#each [[R, cw < 500 ? 'R = 3' : 'R = 3 · all cooperate'], [P, cw < 500 ? 'P = 1' : 'P = 1 · all defect']] as [v, t]}
      <line x1={L} x2={W - Rm} y1={y2(+v)} y2={y2(+v)} class="ref" />
      <text x={W - Rm + 5} y={y2(+v) + 3} class="reflab">{t}</text>
    {/each}
    {#each [0, 1, 2, 3, 4, 5] as v}<text x={L - 5} y={y2(v) + 3} class="ax" text-anchor="end">{v}</text>{/each}
    <line x1={L} x2={L} y1={top2} y2={top2 + H2} class="axis" />
    <path d={payPath} class="pay" />
    {#each xTicks as g}
      <line x1={x(g)} x2={x(g)} y1={top2 + H2} y2={top2 + H2 + 4} class="axis" />
      <text x={x(g)} y={top2 + H2 + 15} class="ax" text-anchor="middle">{g}</text>
    {/each}
    <text x={W - Rm} y={H - 1} class="ax" text-anchor="end">generation</text>
    {#if hover}
      <line x1={x(hover.gen)} x2={x(hover.gen)} y1={T} y2={top2 + H2} class="cursor" />
      <circle cx={x(hover.gen)} cy={y2(hover.meanPayoff)} r="3" class="cdot" />
    {/if}
  </svg>
  <figcaption class="caption readout">
    {#if hover}
      <span class="mono">gen {hover.gen}</span> · payoff <span class="mono">{hover.meanPayoff.toFixed(3)}</span> ·
      most frequent genome <span class="mono">{Math.round(hover.top * 100)}%</span> · <span class="mono">{hover.distinct}</span> distinct genomes
    {:else}
      Hatched area: share of the most frequent genome. Dashed line: number of distinct genomes (out of {nPop}). Point at the chart to read a generation.
    {/if}
  </figcaption>
</figure>

<style>
  .fc { margin: 0; }
  svg { width: 100%; height: auto; display: block; touch-action: pan-y; }
  .grid { stroke: var(--rule); stroke-width: 0.6; }
  .top { fill: url(#hatch); stroke: var(--brass); stroke-width: 1.6; stroke-linejoin: round; }
  .distinct { fill: none; stroke: var(--ink); stroke-width: 1.3; stroke-dasharray: 4 3; }
  .frame { fill: none; stroke: var(--ink); stroke-width: 0.8; }
  .ax { font-family: var(--font-mono); font-size: 10px; fill: var(--ink-3); }
  .lab { font-family: var(--font-mono); font-size: 10.5px; fill: var(--brass-text); font-weight: 600; }
  .lab.dl { fill: var(--ink); font-weight: 400; }
  .ttl { font-family: var(--font-body); font-size: 11px; font-variant-caps: all-small-caps; letter-spacing: 0.07em; fill: var(--ink-2); }
  .ref { stroke: var(--ink-3); stroke-width: 0.7; stroke-dasharray: 4 3; }
  .reflab { font-family: var(--font-body); font-size: 10.5px; font-style: italic; fill: var(--ink-2); }
  .axis { stroke: var(--ink); stroke-width: 0.8; }
  .pay { fill: none; stroke: var(--ink); stroke-width: 1.5; stroke-linejoin: round; }
  .cursor { stroke: var(--brass); stroke-width: 1; }
  .cdot { fill: var(--brass); }
  .readout { min-height: 2.6em; margin-top: 0.2rem; }
</style>
