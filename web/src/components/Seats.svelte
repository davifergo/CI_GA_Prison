<script lang="ts" module>
  export interface SeatData {
    /** index in the population */
    i: number;
    fill: string;
    mark: string;
    label: string;
    elite: boolean;
    mutant: boolean;
    fresh: boolean;
  }
</script>

<script lang="ts">
  // The public gallery: one seat per individual. The view decides the order and the style.
  let {
    seats, gen, selected = $bindable(), animate,
  }: { seats: SeatData[]; gen: number; selected: number | null; animate: boolean } = $props();

  const cols = $derived(Math.ceil(Math.sqrt(seats.length)));
  const rows = $derived(Math.ceil(seats.length / cols));
  const S = 30, GAP = 5, AISLE = 14;
  // an aisle down the middle, as in a public gallery
  const half = $derived(Math.ceil(cols / 2));
  const sx = (c: number) => c * (S + GAP) + (c >= half ? AISLE : 0);
  const W = $derived(sx(cols - 1) + S + 4);
  const H = $derived(rows * (S + GAP) + 4);

  function key(e: KeyboardEvent, k: number) {
    const go = (j: number) => {
      if (j < 0 || j >= seats.length) return;
      selected = seats[j].i;
      (document.querySelector(`[data-seat="${j}"]`) as SVGElement | null)?.focus();
      e.preventDefault();
    };
    if (e.key === 'ArrowRight') go(k + 1);
    else if (e.key === 'ArrowLeft') go(k - 1);
    else if (e.key === 'ArrowDown') go(k + cols);
    else if (e.key === 'ArrowUp') go(k - cols);
    else if (e.key === 'Enter' || e.key === ' ') { selected = seats[k].i; e.preventDefault(); }
  }
</script>

<svg viewBox="-2 -2 {W} {H}" class="seats" class:animate role="grid" aria-label="Population, one seat per individual">
  {#each seats as s, k (k + ':' + gen)}
    {@const c = k % cols}
    {@const r = Math.floor(k / cols)}
    <g
      transform="translate({sx(c)} {r * (S + GAP)})"
      class="seat"
      class:elite={s.elite}
      class:mutant={s.mutant}
      class:fresh={s.fresh}
      class:sel={selected === s.i}
      style="--d:{(k % cols) * 12 + r * 6}ms"
      data-seat={k}
      role="gridcell"
      tabindex={selected === s.i || (selected === null && k === 0) ? 0 : -1}
      aria-selected={selected === s.i}
      aria-label={s.label}
      onclick={() => (selected = s.i)}
      onkeydown={(e) => key(e, k)}
    >
      <g class="body">
        <!-- chair back seen from the front -->
        <path d="M2 {S} L2 7 Q2 1.5 8 1.5 L{S - 8} 1.5 Q{S - 2} 1.5 {S - 2} 7 L{S - 2} {S} Z" style="fill:{s.fill}" class="back" />
        <path d="M0.5 {S - 6.5} L{S - 0.5} {S - 6.5}" class="rail" />
        <circle cx={S / 2} cy={S / 2 - 2.5} r="6.2" class="halo" />
        <text x={S / 2} y={S / 2 + 1} class="mark">{s.mark}</text>
      </g>
      {#if s.mutant}<text x={S - 3} y="8" class="star" aria-hidden="true">*</text>{/if}
      <rect x="-2" y="-2" width={S + 4} height={S + 4} class="ring" />
    </g>
  {/each}
</svg>

<style>
  .seats { width: 100%; height: auto; display: block; }
  .seat { cursor: pointer; outline: none; }
  .back { stroke: var(--ink); stroke-width: 1; }
  .rail { stroke: var(--ink); stroke-width: 1.4; }
  .halo { fill: var(--paper); opacity: 0.88; }
  .mark { font-family: var(--font-mono); font-size: 9px; font-weight: 700; text-anchor: middle; fill: var(--ink); }
  .star { font-family: var(--font-mono); font-size: 13px; font-weight: 700; fill: var(--red-ink); text-anchor: middle; }
  .ring { fill: none; stroke: transparent; stroke-width: 2; }
  .seat:hover .ring { stroke: var(--ink-3); }
  .seat:focus-visible .ring { stroke: var(--brass); stroke-dasharray: 3 2; }
  .seat.sel .ring { stroke: var(--ink); stroke-width: 2.2; }
  .elite .back { stroke: var(--brass); stroke-width: 2.6; }
  .elite .rail { stroke: var(--brass); }

  /* one short animation per generation; nothing overshoots */
  .animate .fresh .body { animation: take-seat 520ms var(--ease-slide) var(--d) both; }
  .animate .mutant .body { animation: flash 640ms var(--ease-ink) both; }
  .animate .elite .ring { animation: glow 900ms var(--ease-ink) both; }
  @keyframes take-seat {
    from { opacity: 0; transform: translateY(5px); }
    to { opacity: 1; transform: none; }
  }
  @keyframes flash {
    0%, 40%, 80% { filter: none; }
    20%, 60% { filter: invert(1); }
  }
  @keyframes glow {
    0% { stroke: var(--brass); stroke-width: 6; opacity: 0; }
    35% { opacity: 1; }
    100% { stroke: var(--brass); stroke-width: 2; opacity: 0.9; }
  }
</style>
