<script lang="ts">
  // The courtroom, drawn as a pen-and-ink sketch. Two compositions: wide (bench in the middle,
  // defendants either side) and narrow (bench above, defendants below) for phones.
  //
  // Each round is one "beat": the slips travel from the defendants' tables to the bench, are
  // unsealed together, any clerk's error is struck through in red ink, the gavel comes down and
  // the ledger gets a new line. All timings are fractions of --beat; at high speed or with
  // reduced motion the end state is shown directly.
  import { actionChar } from '../lib/model/game';
  import type { Match } from '../lib/model/match';

  let { match, t, beat, fast, names }: { match: Match; t: number; beat: number; fast: boolean; names: [string, string] } =
    $props();

  let width = $state(600);
  const narrow = $derived(width < 440);

  const WIDE = {
    vb: [600, 372], floor: 330, bench: { x: 300, y: 186, w: 132, h: 144 }, clock: { x: 300, y: 42 },
    def: [{ x: 92, y: 268 }, { x: 508, y: 268 }], slip: [{ x: 228, y: 150 }, { x: 372, y: 150 }],
  };
  const NARROW = {
    vb: [360, 470], floor: 462, bench: { x: 180, y: 210, w: 128, h: 104 }, clock: { x: 180, y: 38 },
    def: [{ x: 86, y: 402 }, { x: 274, y: 402 }], slip: [{ x: 110, y: 176 }, { x: 250, y: 176 }],
  };
  const L = $derived(narrow ? NARROW : WIDE);
  const r = $derived(t >= 0 ? match.rounds[t] : null);
  const n = $derived(match.rounds.length);
  const ledger = $derived(match.rounds.slice(Math.max(0, t - 2), t + 1));
  const clockAngle = $derived(((t + 1) / n) * 360);
  // where a slip leaves from: the defendant's hand on the table
  const hand = (k: 0 | 1) => ({ x: L.def[k].x + (k === 0 ? 4 : -4), y: L.def[k].y - 6 });
  const tilt = [-3.5, 2.8];

  // a few deterministic wobbles so repeated shapes don't look stamped
  const panels = $derived.by(() => {
    const [W] = L.vb;
    const out: { x: number; w: number }[] = [];
    const pw = narrow ? 52 : 62;
    for (let x = 6; x + pw < W; x += pw + 10) out.push({ x, w: pw });
    return out;
  });
</script>

<div class="scene-wrap" bind:clientWidth={width}>
  <svg
    viewBox="0 0 {L.vb[0]} {L.vb[1]}"
    class="scene"
    class:fast
    style="--beat:{beat}ms"
    role="img"
    aria-label="The courtroom. {r ? `Round ${t + 1}: ${names[0]} ${actionChar(r.played[0])}, ${names[1]} ${actionChar(r.played[1])}.` : 'Court not yet in session.'}"
  >
    <!-- ============================================================ room (static linework) -->
    <g class="room" filter="url(#pen)">
      <!-- cornice and wall -->
      <path d="M0 14 L{L.vb[0]} 14 M0 19 L{L.vb[0]} 19" class="ln thin" />
      <rect x="0" y="19" width={L.vb[0]} height={L.floor - 19} fill="url(#vgrain)" opacity="0.35" />
      <!-- wainscot panels -->
      {#each panels as p, i}
        {@const top = narrow ? 300 : 150}
        <path d="M{p.x} {top} L{p.x + p.w} {top + (i % 2 ? 0.6 : -0.4)} L{p.x + p.w} {L.floor - 8} L{p.x} {L.floor - 8} Z" class="ln" fill="none" />
        <path d="M{p.x + p.w - 7} {top + 4} L{p.x + p.w - 3} {top + 4} L{p.x + p.w - 3} {L.floor - 12} L{p.x + p.w - 7} {L.floor - 12} Z" fill="url(#hatch)" />
      {/each}
      <path d="M0 {narrow ? 296 : 146} L{L.vb[0]} {narrow ? 296 : 146}" class="ln" />
      <!-- floor -->
      <path d="M0 {L.floor} L{L.vb[0]} {L.floor}" class="ln heavy" />
      <rect x="0" y={L.floor} width={L.vb[0]} height={L.vb[1] - L.floor} fill="url(#hatch-wide)" opacity="0.7" />

      <!-- the bench -->
      {#each [L.bench] as b}
        <!-- drape behind the judge -->
        <path d="M{b.x - 74} 72 C{b.x - 70} 120 {b.x - 78} 150 {b.x - 80} {b.y} L{b.x + 80} {b.y} C{b.x + 78} 150 {b.x + 70} 120 {b.x + 74} 72 Z" fill="url(#hatch)" class="ln thin" opacity="0.8" />
        <path d="M{b.x - 74} 72 Q{b.x} 62 {b.x + 74} 72" class="ln" fill="none" />
        {#each [-52, -26, 0, 26, 52] as dx}
          <path d="M{b.x + dx} 70 C{b.x + dx + 3} 110 {b.x + dx - 3} 150 {b.x + dx + 1} {b.y}" class="ln hair" fill="none" />
        {/each}
        <!-- front of the bench -->
        <path d="M{b.x - b.w} {b.y} L{b.x + b.w} {b.y} L{b.x + b.w - 4} {b.y + b.h} L{b.x - b.w + 4} {b.y + b.h} Z" class="paper ln heavy" />
        <path d="M{b.x - b.w - 6} {b.y - 6} L{b.x + b.w + 6} {b.y - 6} L{b.x + b.w + 6} {b.y + 3} L{b.x - b.w - 6} {b.y + 3} Z" class="paper ln" />
        <path d="M{b.x - b.w - 4} {b.y + 3} L{b.x + b.w + 4} {b.y + 3} L{b.x + b.w + 2} {b.y + 9} L{b.x - b.w - 2} {b.y + 9} Z" fill="url(#xhatch)" class="ln thin" />
        <!-- three framed panels, shaded on the right -->
        {#each [-1, 0, 1] as k}
          {@const pw = (b.w * 2 - 40) / 3}
          {@const px = b.x - b.w + 14 + (k + 1) * (pw + 6)}
          <rect x={px} y={b.y + 20} width={pw} height={b.h - 34} class="ln" fill="none" />
          <rect x={px + 5} y={b.y + 25} width={pw - 10} height={b.h - 44} class="ln thin" fill="none" />
          <path d="M{px + pw - 5} {b.y + 25} L{px + pw} {b.y + 20} L{px + pw} {b.y + b.h - 14} L{px + pw - 5} {b.y + b.h - 19} Z" fill="url(#hatch)" />
        {/each}
        <path d="M{b.x + b.w - 4} {b.y + 9} L{b.x + b.w + 10} {b.y + 14} L{b.x + b.w + 6} {b.y + b.h} L{b.x + b.w - 4} {b.y + b.h} Z" fill="url(#xhatch)" class="ln thin" />
      {/each}
    </g>

    <!-- ============================================================ clock: one turn per match -->
    <g transform="translate({L.clock.x} {L.clock.y})" class="clock">
      <circle r="21" class="paper ln heavy" />
      <circle r="17" class="ln thin" fill="none" />
      {#each Array.from({ length: 12 }) as _, i}
        <line x1="0" y1="-17" x2="0" y2={i % 3 ? -14.5 : -12.5} transform="rotate({i * 30})" class="ln" />
      {/each}
      <g style="transform: rotate({clockAngle}deg)" class="hand">
        <path d="M0 3 L-1.6 0 L0 -15 L1.6 0 Z" class="ink" />
      </g>
      <circle r="1.8" class="brass-f" />
      <text x="28" y="4" class="tiny">round {t + 1} of {n}</text>
    </g>

    <!-- ============================================================ the judge -->
    <g transform="translate({L.bench.x} {L.bench.y - 6})" class="judge">
      <g filter="url(#pen)">
        <!-- robe -->
        <path d="M-64 0 C-62 -26 -54 -48 -30 -58 L-10 -63 L10 -63 L30 -58 C54 -48 62 -26 64 0 Z" fill="url(#xhatch-dense)" class="ln heavy" />
        <path d="M-30 -58 C-36 -40 -38 -20 -36 0 M30 -58 C36 -40 38 -20 36 0" class="ln" fill="none" />
        <!-- bands -->
        <path d="M-7 -63 L-1 -63 L-2 -44 L-8 -45 Z M1 -63 L7 -63 L8 -45 L2 -44 Z" class="paper ln" />
        <!-- neck and head -->
        <path d="M-8 -64 L-8 -70 M8 -64 L8 -70" class="ln" />
        <ellipse cx="0" cy="-88" rx="16.5" ry="20.5" class="paper ln heavy" />
        <path d="M5 -106 C14 -102 17 -92 15 -76 C12 -72 8 -70 3 -69 C10 -76 12 -92 5 -106 Z" fill="url(#hatch)" />
        <!-- grey hair at the sides -->
        <path d="M-16 -94 C-19 -100 -16 -108 -10 -110 M-17 -88 C-20 -92 -20 -98 -18 -102 M16 -94 C19 -100 16 -108 10 -110 M17 -88 C20 -92 20 -98 18 -102" class="ln thin" fill="none" />
        <!-- ears -->
        <path d="M-16.5 -90 C-21 -91 -21 -82 -16 -82 M16.5 -90 C21 -91 21 -82 16 -82" class="ln" fill="none" />
        <!-- brows, spectacles, nose, mouth -->
        <path d="M-12 -96 L-3 -95 M3 -95 L12 -96" class="ln heavy" />
        <circle cx="-6.5" cy="-89" r="4.4" class="ln" fill="none" />
        <circle cx="6.5" cy="-89" r="4.4" class="ln" fill="none" />
        <path d="M-2.1 -89.5 Q0 -91 2.1 -89.5 M-10.9 -89.5 L-16 -91 M10.9 -89.5 L16 -91" class="ln thin" fill="none" />
        <circle cx="-6.5" cy="-88.6" r="0.9" class="ink" />
        <circle cx="6.5" cy="-88.6" r="0.9" class="ink" />
        <path d="M0 -86 L-1.6 -79 L1.4 -78.5" class="ln" fill="none" />
        <path d="M-5 -73.5 C-2 -72.6 2 -72.6 5 -73.5" class="ln" fill="none" />
        <!-- resting forearm -->
        <path d="M-40 -40 C-52 -24 -54 -10 -52 0 L-26 0 C-28 -14 -30 -26 -34 -36" fill="url(#xhatch-dense)" class="ln" />
        <path d="M-26 0 C-22 -4 -16 -4 -14 0" class="paper ln" />
      </g>
      <!-- arm and gavel: the arm pivots at the shoulder; nothing overshoots -->
      <g transform="translate(16 0)">
      <g class="gavel-arm">
        {#key t}
          <g class="swing" class:strike={r !== null}>
            <path d="M40 -40 C52 -32 62 -26 74 -24 L80 -15 C66 -16 54 -20 36 -28 Z" fill="url(#xhatch-dense)" class="ln" filter="url(#pen)" />
            <circle cx="79" cy="-20" r="5.2" class="paper ln" />
            <!-- handle and head -->
            <path d="M79 -20 L106 -26" class="ln handle" />
            <rect x="99" y="-40" width="12" height="25" rx="2" transform="rotate(-12 105 -27)" class="paper ln heavy" />
            <path d="M101 -37 L101 -19 M104 -38 L104 -18" transform="rotate(-12 105 -27)" class="ln thin" />
          </g>
        {/key}
      </g>
      <!-- sound block -->
      <path d="M96 -2 L122 -2 L120 6 L98 6 Z" class="paper ln" />
      <path d="M98 2 L120 2" class="ln thin" />
      {#if r}
        {#key t}
          <g class="impact" aria-hidden="true">
            <path d="M126 -6 L134 -12 M128 2 L138 1 M92 -6 L86 -12" class="ln" />
          </g>
        {/key}
      {/if}
      </g>
    </g>

    <!-- ============================================================ defendants -->
    {#each [0, 1] as k}
      {@const d = L.def[k]}
      {@const flip = k === 1}
      <g transform="translate({d.x} {d.y})">
        <g transform={flip ? 'scale(-1 1)' : ''} filter="url(#pen)">
          <!-- chair -->
          <path d="M-70 -64 L-66 62 M-70 -64 L-58 -64 L-56 4 M-66 8 L-30 8 L-30 62" class="ln heavy" fill="none" />
          <!-- body, seated, leaning forward -->
          <path d="M-62 4 C-66 -22 -62 -46 -46 -58 L-34 -60 C-24 -50 -20 -30 -22 -6 Z" fill={k === 0 ? 'url(#hatch)' : 'url(#xhatch)'} class="ln heavy" />
          <path d="M-40 -59 L-34 -44 L-31 -59" class="paper ln thin" />
          <!-- arm to the table -->
          <path d="M-40 -48 C-30 -34 -18 -16 -2 -10 L0 -2 C-20 -6 -36 -20 -46 -36 Z" fill={k === 0 ? 'url(#hatch)' : 'url(#xhatch)'} class="ln" />
          <path d="M-2 -10 C3 -11 8 -8 8 -4 L0 -2 Z" class="paper ln" />
          <!-- head -->
          <ellipse cx="-36" cy="-76" rx="12" ry="14.5" class="paper ln heavy" />
          <path d="M-31 -88 C-26 -84 -24 -76 -25 -66 C-28 -63 -33 -62 -36 -62 C-30 -68 -28 -78 -31 -88 Z" fill="url(#hatch)" />
          <path d="M-24.5 -78 L-21 -73 L-24.5 -71.5" class="ln" fill="none" />
          <circle cx="-28" cy="-79" r="1" class="ink" />
          <path d="M-31 -84 L-25 -83" class="ln" />
          {#if k === 0}
            <!-- slicked hair with a parting -->
            <path d="M-48 -78 C-50 -92 -38 -96 -26 -88 C-30 -90 -38 -92 -46 -84 Z" class="ink" />
            <!-- fedora on the table -->
            <path d="M14 -2 C14 -8 18 -14 26 -14 C34 -14 38 -8 38 -2 Z" fill="url(#xhatch)" class="ln" />
            <path d="M8 -1 C18 -4 34 -4 44 -1" class="ln heavy" fill="none" />
          {:else}
            <!-- bowler hat and moustache -->
            <path d="M-50 -82 C-50 -98 -24 -100 -24 -84 Z" fill="url(#xhatch-dense)" class="ln heavy" />
            <path d="M-54 -82 C-42 -84 -30 -84 -20 -81" class="ln heavy" fill="none" />
            <path d="M-29 -70 C-26 -68 -23 -69 -22 -71" class="ln heavy" fill="none" />
          {/if}
          <!-- table -->
          <path d="M-24 0 L44 0 L44 5 L-24 5 Z" class="paper ln heavy" />
          <path d="M-20 5 L-20 62 M40 5 L40 62" class="ln heavy" />
          <path d="M-20 12 L40 12" class="ln thin" />
          <path d="M34 12 L40 12 L40 62 L34 62 Z" fill="url(#hatch)" />
        </g>
        <!-- name plate (not mirrored) -->
        <g transform="translate({flip ? -10 : 10} 30)">
          <rect x="-34" y="-11" width="68" height="22" class="plate" />
          <text y="4.5" class="plate-t" text-anchor="middle">{names[k]}</text>
        </g>
      </g>
    {/each}

    <!-- ============================================================ the ledger on the bench -->
    <g transform="translate({L.bench.x} {L.bench.y - 4})" class="ledger">
      <path d="M-44 -2 L-42 -34 L0 -31 L0 1 Z" class="paper ln" />
      <path d="M44 -2 L42 -34 L0 -31 L0 1 Z" class="paper ln" />
      <path d="M0 -31 L0 1" class="ln" />
      <path d="M-44 -2 L0 1 L44 -2 L44 1 L0 4 L-44 1 Z" fill="url(#xhatch)" class="ln thin" />
      {#each ledger as row, i (row.t)}
        <g class="row" class:new={row.t === t} style="transform: translateY({(i - ledger.length + 1) * 8.5}px)">
          <text x="-40" y="-6" class="lg">{row.t + 1}</text>
          <text x="-6" y="-6" class="lg" text-anchor="end">{row.pay[0]}·{row.pay[1]}</text>
        </g>
      {/each}
      {#if r}
        {#key t}
          <g class="row new">
            <text x="22" y="-21" class="lg" text-anchor="middle">{r.total[0]}</text>
            <text x="22" y="-7" class="lg" text-anchor="middle">{r.total[1]}</text>
            <path d="M8 -15.5 L36 -15.5" class="ln hair" />
          </g>
        {/key}
      {/if}
    </g>

    <!-- ============================================================ the slips of this round -->
    {#if r}
      {#key t}
        {#each [0, 1] as k}
          {@const s = L.slip[k]}
          {@const h = hand(k as 0 | 1)}
          {@const err = r.error[k]}
          {@const intended = actionChar(r.intended[k])}
          {@const played = actionChar(r.played[k])}
          <g transform="translate({s.x} {s.y}) rotate({tilt[k]})">
            <!-- sealed slip, carried from the table -->
            <g class="sealed" style="--dx:{h.x - s.x}px; --dy:{h.y - s.y}px">
              <rect x="-14" y="-9" width="28" height="18" class="paper ln" />
              <path d="M-14 -9 L0 1 L14 -9" class="ln thin" fill="none" />
              <circle cx="0" cy="1" r="3.2" class="brass-f" />
            </g>
            <!-- opened slip -->
            <g class="open">
              <rect x={err ? -36 : -24} y="-30" width={err ? 72 : 48} height="58" class="slip-paper" />
              <path d="M{err ? -36 : -24} -2 L{err ? 36 : 24} -2" class="fold" />
              {#if !err}
                <text y="17" class="letter" class:d={played === 'D'} text-anchor="middle">{played}</text>
              {:else}
                <text x="-17" y="17" class="letter muted" text-anchor="middle">{intended}</text>
                <line x1="-31" y1="13" x2="-3" y2="-9" class="strike" pathLength="1" />
                <text x="17" y="17" class="letter recorded" class:d={played === 'D'} text-anchor="middle">{played}</text>
                <g class="err-note"><rect x="-34" y="-47" width="68" height="14" class="note-bg" /><text y="-36.5" text-anchor="middle">clerk’s error</text></g>
              {/if}
            </g>
          </g>
        {/each}
      {/key}
    {/if}
  </svg>
</div>

<style>
  .scene-wrap { width: 100%; }
  .scene { width: 100%; height: auto; display: block; overflow: visible; }

  .ln { stroke: var(--ink); stroke-width: 1.15; stroke-linecap: round; stroke-linejoin: round; }
  .ln.thin { stroke-width: 0.7; }
  .ln.hair { stroke-width: 0.45; }
  .ln.heavy { stroke-width: 1.7; }
  .ink { fill: var(--ink); }
  .paper { fill: var(--paper); }
  .brass-f { fill: var(--brass); stroke: var(--ink); stroke-width: 0.6; }
  .handle { stroke-width: 3.2; }
  .tiny { font-family: var(--font-mono); font-size: 8.5px; fill: var(--ink-2); }
  .plate { fill: var(--paper-2); stroke: var(--brass); stroke-width: 1.6; }
  .plate-t { font-family: var(--font-mono); font-size: 11.5px; font-weight: 600; fill: var(--ink); }
  .lg { font-family: var(--font-mono); font-size: 7.5px; fill: var(--ink); }
  .hand { transition: transform 400ms var(--ease-ink); }

  .slip-paper { fill: var(--paper); stroke: var(--ink); stroke-width: 1.2; }
  .fold { stroke: var(--rule-strong); stroke-width: 0.6; stroke-dasharray: 2 2; }
  .letter { font-family: var(--font-display); font-size: 36px; fill: var(--coop); }
  .letter.d { fill: var(--defect); }
  .letter.muted { fill: var(--ink-3); font-size: 30px; }
  .strike { stroke: var(--red-ink); stroke-width: 3; stroke-linecap: round; stroke-dasharray: 1; }
  .err-note text { font-family: var(--font-body); font-style: italic; font-size: 11px; fill: var(--red-ink); }
  .note-bg { fill: var(--paper); stroke: var(--red-ink); stroke-width: 0.6; }

  /* ------------------------------------------------ the beat */
  .sealed {
    animation: travel calc(var(--beat) * 0.3) var(--ease-slide) both, unseal calc(var(--beat) * 0.08) var(--ease-ink) calc(var(--beat) * 0.3) both;
  }
  @keyframes travel { from { transform: translate(var(--dx), var(--dy)) scale(0.8); } to { transform: none; } }
  @keyframes unseal { from { opacity: 1; } to { opacity: 0; } }

  .open { transform-box: fill-box; transform-origin: 50% 0; animation: unfold calc(var(--beat) * 0.1) var(--ease-ink) calc(var(--beat) * 0.32) both; }
  @keyframes unfold { from { transform: scaleY(0.05); opacity: 0; } to { transform: none; opacity: 1; } }
  .letter { animation: ink-in calc(var(--beat) * 0.12) var(--ease-ink) calc(var(--beat) * 0.4) both; }
  .strike { animation: draw calc(var(--beat) * 0.1) var(--ease-strike) calc(var(--beat) * 0.5) both; }
  .recorded, .err-note { animation: ink-in calc(var(--beat) * 0.1) var(--ease-ink) calc(var(--beat) * 0.58) both; }
  @keyframes ink-in { from { opacity: 0; } to { opacity: 1; } }
  @keyframes draw { from { stroke-dashoffset: 1; } to { stroke-dashoffset: 0; } }

  /* gavel: raised at rest, comes down on the block, lifts again */
  .swing { transform-origin: 40px -40px; transform: rotate(-30deg); }
  .swing.strike { animation: gavel calc(var(--beat) * 0.2) linear calc(var(--beat) * 0.6) both; }
  @keyframes gavel {
    0% { transform: rotate(-30deg); animation-timing-function: cubic-bezier(0.55, 0, 0.9, 0.4); }
    40% { transform: rotate(10deg); animation-timing-function: cubic-bezier(0.2, 0.6, 0.35, 1); }
    100% { transform: rotate(-30deg); }
  }
  .impact { opacity: 0; animation: impact calc(var(--beat) * 0.12) var(--ease-ink) calc(var(--beat) * 0.67) both; }
  @keyframes impact { 0% { opacity: 0; } 30% { opacity: 1; } 100% { opacity: 0; } }

  .ledger .row { transition: transform 300ms var(--ease-slide); }
  .ledger .row.new { animation: write calc(var(--beat) * 0.18) var(--ease-ink) calc(var(--beat) * 0.72) both; }
  @keyframes write { from { clip-path: inset(0 100% 0 0); } to { clip-path: inset(0 0 0 0); } }

  /* fast: no choreography, just the result */
  .fast .sealed { display: none; }
  .fast .open, .fast .letter, .fast .strike, .fast .recorded, .fast .err-note, .fast .ledger .row.new { animation: none; }
  .fast .swing.strike { animation: none; }
  .fast .impact { display: none; }
  @media (prefers-reduced-motion: reduce) {
    .sealed, .impact { display: none; }
    .swing.strike { animation: none; }
  }
</style>
