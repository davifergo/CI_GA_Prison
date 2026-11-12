<script lang="ts">
  import { onDestroy, onMount } from 'svelte';
  import { bitString, classify, label } from '../lib/model/game';
  import { currentRegime, DEFAULT_PARAMS, majority, Origin, regimes, type GAParams, type Generation } from '../lib/model/ga';
  import { GAClient } from '../lib/gaClient';
  import { ORDER, STYLE, type Column } from '../lib/strategies';
  import Seats, { type SeatData } from '../components/Seats.svelte';
  import FreqChart from '../components/FreqChart.svelte';
  import M2Chart from '../components/M2Chart.svelte';
  import Swatch from '../components/Swatch.svelte';
  import Genome2Grid from '../components/Genome2Grid.svelte';
  import { classify2, expectedMatch2, format2, label2, type Generation2 } from '../lib/model/memory2';
  import { settings } from '../lib/settings.svelte';

  const m2 = settings.memory === 2; // the view is re-created when the memory changes
  const PRESETS = m2
    ? [
        { id: 'p0', title: 'No noise → drift', p: 0, seed: 0, note: 'Run 0 of the report at p = 0: the gallery cooperates (payoff near 2.97) but never settles; about 50 genomes coexist and none holds more than a tenth. Without noise, exact fitness ties make this run depend on floating-point details, so it can part from the report’s after a while (see Limitations).' },
        { id: 'p1', title: '1 % noise → one genome', p: 0.01, seed: 100, note: 'Run 0 at p = 0.01: by generation 20 one genome holds over half the gallery; at the end 10 | 0111 0111 0111 0110 holds 92% and the payoff stays near 2.84. Same seed and parameters as main_memory2.py, reproduced generation by generation.' },
        { id: 'p5', title: '5 % noise → cooperation survives', p: 0.05, seed: 200, note: 'Run 0 at p = 0.05: the same genome takes over by generation 23 and cooperation survives the noise (payoff near 2.57, against 1.17 with memory one). Same seed and parameters as main_memory2.py, reproduced generation by generation.' },
      ]
    : [
        { id: 'p0', title: 'No noise → TFT', p: 0, seed: 0, note: 'Run 0 of the report at p = 0: GRIM leads for a few generations, then TFT takes over from generation 19. Same seed and parameters as main.py, so this is the run shown in Figure 6 of the report.' },
        { id: 'p1', title: '1 % noise → GRIM cycles', p: 0.01, seed: 100, note: 'Run 0 at p = 0.01: GRIM holds the majority while forgiving variants keep re-entering and the payoff swings. Same seed and parameters as main.py, so this is the run shown in Figure 6 of the report.' },
        { id: 'p5', title: '5 % noise → ALLD', p: 0.05, seed: 200, note: 'Run 0 at p = 0.05: a long ALLD regime from generation 3, which switches to GRIM near generation 389. Same seed and parameters as main.py, so this is the run shown in Figure 6 of the report.' },
      ];

  // ---------------------------------------------------------------- parameters
  let pNoise = $state(0);
  let mutIndpb = $state(DEFAULT_PARAMS.mutIndpb);
  let tournSize = $state(DEFAULT_PARAMS.tournSize);
  let elitism = $state(DEFAULT_PARAMS.elitism);
  let nPop = $state(DEFAULT_PARAMS.nPop);
  let seed = $state(0);
  let preset = $state<string | null>('p0');
  let presetNote = $state<string>(PRESETS[0].note);

  const params = (): GAParams => ({ ...DEFAULT_PARAMS, pNoise, mutIndpb, tournSize, elitism, nPop, seed });
  // what the running population was started with
  let running: GAParams = $state({ ...DEFAULT_PARAMS });
  const needsReset = $derived(nPop !== running.nPop || seed !== running.seed);
  const reportDefaults = $derived(mutIndpb === 0.01 && tournSize === 3 && elitism === 2 && nPop === 100);

  // ---------------------------------------------------------------- run state
  let client: GAClient;
  let cur = $state<Generation | Generation2 | null>(null);
  let prevSet = $state<Set<number> | null>(null);
  interface Point { gen: number; freq: Record<string, number>; meanPayoff: number; top: number; distinct: number }
  let history: Point[] = $state([]);
  const point = (g: Generation | Generation2): Point => ({
    gen: g.gen, freq: g.freq, meanPayoff: g.meanPayoff,
    top: 'top' in g ? g.top[0].n / g.pop.length : 0, distinct: 'nDistinct' in g ? g.nDistinct : 0,
  });

  // memory two: the most frequent genomes keep a seat style (slot) while they stay frequent
  type Fam = 'coop' | 'brass' | 'defect';
  let slots = $state<{ g: number; fam: Fam; self: number }[]>([]);
  function updateSlots(g: Generation2) {
    const keep = new Set(g.top.filter((x) => x.n >= 2).slice(0, 8).map((x) => x.g));
    const next: ({ g: number; fam: Fam; self: number } | null)[] = Array.from({ length: 6 }, (_, k) => (slots[k] && keep.has(slots[k].g) ? slots[k] : null));
    for (const { g: gg, n } of g.top) {
      if (n < 2 || next.some((x) => x?.g === gg)) continue;
      const free = next.findIndex((x) => x === null);
      if (free < 0) break;
      const self = expectedMatch2(gg, gg, running.rounds, running.pNoise).pay1;
      next[free] = { g: gg, fam: self >= 2.5 ? 'coop' : self < 1.5 ? 'defect' : 'brass', self };
    }
    slots = next.map((x) => x ?? { g: -1, fam: 'brass', self: 0 });
  }
  const slotOf = (g: number) => slots.findIndex((x) => x.g === g);
  let playing = $state(false);
  let speed = $state(5);
  const SPEEDS = [1, 2, 5, 10, 25, 60];
  let selected = $state<number | null>(null);
  let busy = false;
  let timer: ReturnType<typeof setTimeout> | undefined;
  let epoch = 0; // invalidates replies from before a reset

  const reduced = matchMedia('(prefers-reduced-motion: reduce)');
  const animate = $derived(speed <= 5 && !reduced.matches);

  async function reset() {
    stop();
    epoch++;
    const e = epoch;
    running = params();
    const res = await client.request<'gens'>({ type: 'init', params: $state.snapshot(running) as GAParams, memory: settings.memory });
    if (e !== epoch) return;
    cur = res.gens[0];
    prevSet = null;
    slots = [];
    if (m2) updateSlots(cur as Generation2);
    history = [point(cur)];
    selected = null;
  }

  async function advance(k = 1) {
    if (busy || !cur) return;
    busy = true;
    const e = epoch;
    const res = await client.request<'gens'>({ type: 'step', n: k });
    busy = false;
    if (e !== epoch) return;
    const last = res.gens[res.gens.length - 1];
    prevSet = new Set((res.gens.length > 1 ? res.gens[res.gens.length - 2] : cur).pop);
    history = [...history, ...res.gens.map(point)];
    cur = last;
    if (m2) updateSlots(last as Generation2);
  }

  function loop() {
    if (!playing) return;
    const per = speed > 30 ? 2 : 1;
    advance(per).then(() => {
      if (playing) timer = setTimeout(loop, (1000 * per) / speed);
    });
  }
  function play() { if (!cur) return; playing = true; loop(); }
  function stop() { playing = false; clearTimeout(timer); }
  const toggle = () => (playing ? stop() : play());
  async function stepOne() { stop(); await advance(1); }

  async function applyPreset(p: (typeof PRESETS)[number]) {
    preset = p.id;
    presetNote = p.note;
    pNoise = p.p; seed = p.seed;
    mutIndpb = DEFAULT_PARAMS.mutIndpb; tournSize = DEFAULT_PARAMS.tournSize; elitism = DEFAULT_PARAMS.elitism; nPop = DEFAULT_PARAMS.nPop;
    await reset();
    play();
  }

  // live parameters apply from the next generation
  $effect(() => {
    const live = { pNoise, mutIndpb, tournSize, elitism };
    if (!client || !cur) return;
    if (live.pNoise !== running.pNoise || live.mutIndpb !== running.mutIndpb || live.tournSize !== running.tournSize || live.elitism !== running.elitism) {
      client.send({ type: 'set', params: live });
      running = { ...running, ...live };
      if (preset && PRESETS.find((p) => p.id === preset)?.p !== pNoise) preset = null;
    }
  });

  onMount(() => {
    client = new GAClient();
    reset();
  });
  onDestroy(() => { stop(); client?.terminate(); });

  // ---------------------------------------------------------------- derived read-outs
  const regime = $derived(currentRegime(history));
  const regimeLog = $derived(regimes(history));
  const copiesOf = (g: number) => { let n = 0; if (cur) for (const x of cur.pop) if (x === g) n++; return n; };
  const leader = $derived.by(() => {
    if (!cur) return null;
    if ('top' in cur) return { g: cur.top[0].g, share: cur.top[0].n / cur.pop.length };
    let best = 0;
    for (let g = 1; g < 32; g++) if (cur.counts[g] > cur.counts[best]) best = g;
    return { g: best, share: cur.counts[best] / cur.pop.length };
  });

  // seats: grouped so that blocks grow and shrink
  const seats: SeatData[] = $derived.by(() => {
    if (!cur) return [];
    const c = cur;
    const fresh = (g: number) => !!prevSet && !prevSet.has(g);
    if (m2) {
      const list = Array.from(c.pop, (g, i) => ({ i, g, slot: slotOf(g), fit: c.fitness[i], o: c.origin[i] }));
      list.sort((a, b) => (a.slot < 0 ? 99 : a.slot) - (b.slot < 0 ? 99 : b.slot) || a.g - b.g || b.fit - a.fit || a.i - b.i);
      return list.map(({ i, g, slot, fit, o }) => ({
        i, fill: slot >= 0 ? `url(#pat-s${slot}-${slots[slot].fam})` : 'url(#pat-other)', mark: slot >= 0 ? String(slot + 1) : '·',
        label: `genome ${format2(g)}, fitness ${fit.toFixed(3)}${o === Origin.Elite ? ', elite' : o === Origin.Mutant ? ', mutant' : ''}`,
        elite: o === Origin.Elite, mutant: o === Origin.Mutant, fresh: fresh(g),
      }));
    }
    const rank = (col: Column) => ORDER.indexOf(col);
    const list = Array.from(c.pop, (g, i) => ({ i, g, col: classify(g) as Column, fit: c.fitness[i], o: c.origin[i] }));
    list.sort((a, b) => rank(a.col) - rank(b.col) || a.g - b.g || b.fit - a.fit || a.i - b.i);
    return list.map(({ i, g, col, fit, o }) => ({
      i, fill: STYLE[col].fill, mark: STYLE[col].mark,
      label: `${col === 'OTHER' ? 'unnamed genome' : col} ${bitString(g)}, fitness ${fit.toFixed(3)}${o === Origin.Elite ? ', elite' : o === Origin.Mutant ? ', mutant' : ''}`,
      elite: o === Origin.Elite, mutant: o === Origin.Mutant, fresh: fresh(g),
    }));
  });
  const sel = $derived(cur && selected !== null && selected < cur.pop.length ? { i: selected, g: cur.pop[selected], fit: cur.fitness[selected], origin: cur.origin[selected] } : null);
  const ORIGIN_TEXT: Record<number, string> = {
    [Origin.Initial]: 'drawn at random in generation 0',
    [Origin.Elite]: 'elite: one of the best of the previous generation, carried over unchanged',
    [Origin.Copy]: 'tournament winner, copied without change',
    [Origin.Crossed]: 'offspring of a uniform crossover',
    [Origin.Mutant]: 'mutant: at least one bit flipped this generation',
  };
  const tally = $derived.by(() => {
    if (!cur) return { elite: 0, mutant: 0, fresh: 0 };
    let elite = 0, mutant = 0, fresh = 0;
    cur.origin.forEach((o, i) => {
      if (o === Origin.Elite) elite++;
      if (o === Origin.Mutant) mutant++;
      if (prevSet && !prevSet.has(cur!.pop[i])) fresh++;
    });
    return { elite, mutant, fresh };
  });
</script>

<section class="gallery" aria-labelledby="gal-h">
  <div class="intro">
    <h2 id="gal-h">The Gallery</h2>
    <p class="dek">
      The public benches hold the population: one seat per strategy, re-chosen every generation by tournament,
      crossover and mutation. Each individual’s fitness is its mean payoff per round against everyone else in the
      gallery.
      {#if m2}With memory two there are 262,144 genomes and the named strategies almost never appear, so the seats
        show the most frequent genomes instead, numbered 1 to 6.{/if}
    </p>
  </div>

  <div class="presets" role="group" aria-label="Presets from the report">
    <span class="kicker">From the report</span>
    {#each PRESETS as p}
      <button class="btn" aria-pressed={preset === p.id} onclick={() => applyPreset(p)}>{p.title}</button>
    {/each}
  </div>
  {#if preset}<p class="caption preset-note">{presetNote}</p>{/if}

  <div class="layout">
    <div class="hall">
      <div class="counter" aria-live="off">
        <span class="kicker">Generation</span>
        <span class="num gen">{cur?.gen ?? 0}</span>
      </div>
      <div class="bar" aria-hidden="true"></div>
      {#if cur}
        <Seats {seats} gen={cur.gen} bind:selected {animate} />
      {/if}
      <p class="caption tally">
        This generation: <span class="mono">{tally.elite}</span> elite (brass frame),
        <span class="mono">{tally.mutant}</span> mutant{tally.mutant === 1 ? '' : 's'} (<span class="star">*</span>),
        <span class="mono">{tally.fresh}</span> seat{tally.fresh === 1 ? '' : 's'} of a genome absent last generation.
      </p>
      <div class="transport" role="group" aria-label="Evolution">
        <button class="btn primary" onclick={toggle} aria-pressed={playing}>{playing ? 'Pause' : 'Play'}</button>
        <button class="btn" onclick={stepOne}>Step one generation</button>
        <label class="speed"><span class="kicker">Speed</span>
          <select bind:value={speed} aria-label="Generations per second">
            {#each SPEEDS as s}<option value={s}>{s}/s</option>{/each}
          </select>
        </label>
      </div>

      <div class="seat-info" aria-live="polite">
        {#if sel && m2}
          {@const slot = slotOf(sel.g)}
          <div class="si-head">
            {#if slot >= 0}<span class="slotmark mono">{slot + 1}</span>{/if}
            <h4>{label2(sel.g).includes('|') ? 'Unnamed genome' : label2(sel.g)}</h4>
          </div>
          <p class="mono bits">{format2(sel.g)}</p>
          <p>Fitness <span class="mono">{sel.fit.toFixed(4)}</span> per round · {ORIGIN_TEXT[sel.origin]}.</p>
          <div class="si-grid"><Genome2Grid genome={sel.g} compact label="Genome of the selected seat" /></div>
          <p class="caption">{copiesOf(sel.g)} of {cur!.pop.length} seats hold this genome. Against itself it earns
            <span class="mono">{expectedMatch2(sel.g, sel.g, running.rounds, running.pNoise).pay1.toFixed(3)}</span> per round.</p>
        {:else if sel}
          {@const col = classify(sel.g) as Column}
          <div class="si-head">
            <Swatch col={col} />
            <h4>{col === 'OTHER' ? 'Unnamed genome' : col}</h4>
            <span class="mono bits">{bitString(sel.g)}</span>
          </div>
          <p>Fitness <span class="mono">{sel.fit.toFixed(4)}</span> per round · {ORIGIN_TEXT[sel.origin]}.</p>
          <p class="caption">{STYLE[col].blurb}. {copiesOf(sel.g)} of {cur!.pop.length} seats hold this genome.</p>
        {:else}
          <p class="caption">Select a seat to read its genome, name and fitness.</p>
        {/if}
      </div>
    </div>

    <div class="charts">
      {#if m2 && cur && leader}
      <div class="regime" class:on={leader.share > 0.5}>
        <span class="kicker">Most frequent genome</span>
        <p><span class="mono">{format2(leader.g)}</span> holds <strong>{Math.round(leader.share * 100)}%</strong> of the gallery;
          <span class="mono">{(cur as Generation2).nDistinct}</span> distinct genomes in all.</p>
        <p class="caption">
          {label2(leader.g).includes('|') ? `Classified as ${classify2(leader.g)} by the report’s rule.` : `Named here: ${label2(leader.g)}.`}
          With noise, the report’s runs converge in about 40 generations to one genome holding about 83%; without noise
          about 43 genomes coexist and the most frequent holds about 15%.
        </p>
      </div>
      <M2Chart {history} nPop={cur.pop.length} />
      <ul class="legend" aria-label="Numbered genomes">
        {#each slots as sl, k}
          {#if sl.g >= 0}
            <li><svg width="14" height="14" aria-hidden="true"><rect x="0.5" y="0.5" width="13" height="13" style="fill:url(#pat-s{k}-{sl.fam});stroke:var(--ink)" /></svg>
              <span class="mono name">{k + 1}</span> <span class="mono g2">{format2(sl.g)}</span>
              <span class="caption">{copiesOf(sl.g)} seats · {sl.self.toFixed(2)} against itself</span></li>
          {/if}
        {/each}
        <li class="note caption">Colour: green if a genome earns 2.5 or more against itself, red if under 1.5, brass in between.
          Unnumbered seats (stippled) hold rarer genomes.</li>
      </ul>
      {:else}
      <div class="regime" class:on={!!regime}>
        <span class="kicker">Regime</span>
        {#if regime}
          <p><strong>{regime.name}</strong> has held over half the gallery for <span class="mono">{regime.length}</span> generations (since {regime.since}).</p>
        {:else if cur && majority(cur.freq)}
          <p>{majority(cur.freq)} has the majority, but not yet for 10 generations.</p>
        {:else}
          <p>No strategy holds over half the gallery.</p>
        {/if}
        <p class="caption">
          A regime is a strategy above 50% for at least 10 generations, the report’s definition.
          {#if regimeLog.length}Record so far: {regimeLog.map((r) => `${r.name} (gen ${r.start})`).join(' → ')}.{/if}
          {#if leader}Most common genome now: <span class="mono">{bitString(leader.g)}</span> ({label(leader.g)}, {Math.round(leader.share * 100)}%).{/if}
        </p>
      </div>
      <FreqChart {history} />
      <ul class="legend" aria-label="Strategies">
        {#each ORDER as c}
          <li><Swatch col={c} /> <span class="mono name">{c}</span> <span class="caption">{STYLE[c].blurb}</span></li>
        {/each}
      </ul>
      {/if}
    </div>

    <form class="knobs" onsubmit={(e) => { e.preventDefault(); reset(); }} aria-label="Parameters">
      <h3>Parameters</h3>
      <label class="field"><span>Noise <span class="mono v">p = {pNoise.toFixed(3)}</span></span>
        <input type="range" min="0" max="0.1" step="0.005" bind:value={pNoise} /></label>
      <label class="field"><span>Mutation per bit <span class="mono v">{mutIndpb.toFixed(3)}</span></span>
        <input type="range" min="0" max="0.1" step="0.001" bind:value={mutIndpb} /></label>
      <label class="field"><span>Tournament size <span class="mono v">{tournSize}</span></span>
        <input type="range" min="1" max="10" step="1" bind:value={tournSize} /></label>
      <label class="field"><span>Elitism <span class="mono v">{elitism}</span></span>
        <input type="range" min="0" max="10" step="1" bind:value={elitism} /></label>
      <p class="caption">These four apply from the next generation.</p>
      <label class="field"><span>Population size <span class="mono v">{nPop}</span></span>
        <input type="range" min="10" max="400" step="2" bind:value={nPop} /></label>
      <label class="field"><span>Seed</span><input type="number" min="0" step="1" bind:value={seed} /></label>
      <button class="btn" class:primary={needsReset} type="submit">Reset with these settings</button>
      <p class="caption">
        {#if needsReset}Population size and seed take effect on reset.{:else if m2 && running.pNoise === 0}Memory two without noise is slower: many distinct genomes, so many new pairs to compute.{:else if reportDefaults}Crossover 0.7 and 150 rounds per match, as in the report.{:else}Crossover 0.7 and 150 rounds per match; other settings differ from the report.{/if}
      </p>
    </form>
  </div>
</section>

<style>
  .gallery { padding-top: 1.3rem; }
  .intro { display: grid; gap: 0.4rem; margin-bottom: 0.9rem; }
  .presets { display: flex; flex-wrap: wrap; align-items: center; gap: 0.4rem 0.6rem; padding: 0.6rem 0; border-top: 1px solid var(--rule-strong); }
  .presets .kicker { margin-right: 0.3rem; }
  .preset-note { margin: 0 0 0.4rem; max-width: 90ch; }

  .layout {
    display: grid;
    grid-template-columns: minmax(280px, 400px) minmax(0, 1fr) 230px;
    gap: 1.6rem;
    border-top: 1px solid var(--rule);
    padding-top: 1rem;
    align-items: start;
  }
  .hall { min-width: 0; }
  .counter { display: flex; align-items: baseline; justify-content: space-between; }
  .gen { font-family: var(--font-display); font-size: clamp(3rem, 2rem + 3vw, 4.6rem); line-height: 0.9; font-variant-numeric: lining-nums tabular-nums; }
  .bar { height: 9px; margin: 0.4rem 0 0.6rem; border-top: 2px solid var(--ink); border-bottom: 1px solid var(--ink);
    background: repeating-linear-gradient(90deg, var(--ink) 0 1.5px, transparent 1.5px 12px); }
  .tally { margin: 0.5rem 0 0.6rem; }
  .star { color: var(--red-ink); font-weight: 700; font-family: var(--font-mono); }
  .transport { display: flex; flex-wrap: wrap; gap: 0.4rem; align-items: end; }
  .speed { display: inline-flex; align-items: end; gap: 0.35rem; margin-left: 0.3rem; }
  .speed select { min-width: 4.6rem; font-family: var(--font-mono); font-size: 0.9rem; }
  .seat-info { margin-top: 0.9rem; padding-top: 0.6rem; border-top: 1px dotted var(--rule-strong); min-height: 5.5rem; }
  .si-head { display: flex; align-items: center; gap: 0.5rem; }
  .si-head h4 { font-size: 1.3rem; }
  .bits { font-size: 0.9rem; letter-spacing: 0.08em; color: var(--ink-2); }
  .seat-info p { margin: 0.3rem 0 0; }

  .charts { min-width: 0; }
  .regime { border-left: 3px solid var(--rule); padding: 0.1rem 0 0.2rem 0.7rem; margin-bottom: 0.8rem; }
  .regime.on { border-left-color: var(--brass); }
  .regime p { margin: 0.1rem 0 0; }
  .legend { list-style: none; margin: 0.4rem 0 0; padding: 0; display: grid; grid-template-columns: repeat(auto-fill, minmax(15rem, 1fr)); gap: 0.15rem 1rem; }
  .legend li { display: flex; align-items: center; gap: 0.4rem; }
  .legend .name { font-size: 0.8rem; min-width: 3.8rem; }
  .legend .caption { font-size: 0.8rem; }
  .legend .g2 { font-size: 0.78rem; white-space: nowrap; }
  .legend .note { grid-column: 1 / -1; margin-top: 0.2rem; }
  .slotmark { display: inline-grid; place-items: center; width: 1.4rem; height: 1.4rem; border: 1px solid var(--ink); font-size: 0.8rem; font-weight: 700; }
  .si-grid { margin: 0.4rem 0; }

  .knobs { display: grid; gap: 0.55rem; align-content: start; border-left: 1px solid var(--rule); padding-left: 1.2rem; }
  .knobs h3 { font-size: 1.3rem; }
  .knobs .v { color: var(--ink); font-size: 0.78rem; font-variant-caps: normal; letter-spacing: 0; float: right; }
  .knobs .caption { margin: 0; }

  @media (max-width: 1180px) {
    .layout { grid-template-columns: minmax(260px, 360px) minmax(0, 1fr); }
    .knobs { grid-column: 1 / -1; border-left: 0; padding-left: 0; border-top: 1px solid var(--rule); padding-top: 0.8rem; grid-template-columns: repeat(auto-fill, minmax(13rem, 1fr)); gap: 0.6rem 1.4rem; }
    .knobs h3, .knobs .caption { grid-column: 1 / -1; }
  }
  @media (max-width: 760px) {
    .layout { grid-template-columns: minmax(0, 1fr); }
  }
</style>
