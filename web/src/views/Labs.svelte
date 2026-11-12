<script lang="ts">
  import { onDestroy, onMount } from 'svelte';
  import { genomeOfName, label, type Genome } from '../lib/model/game';
  import { payoffMatrix } from '../lib/model/payoff';
  import { challengers, invasionCheck } from '../lib/model/analysis';
  import { DEFAULT_PARAMS } from '../lib/model/ga';
  import { GAClient } from '../lib/gaClient';
  import type { SweepPoint } from '../lib/ga.worker';
  import StrategyPicker from '../components/StrategyPicker.svelte';
  import StrategyPicker2 from '../components/StrategyPicker2.svelte';
  import { bitString, isNamed, NAMED } from '../lib/model/game';
  import { invasionFromPayoffs } from '../lib/model/analysis';
  import { expectedMatch2, format2, N_GENOMES2, NAMED2 } from '../lib/model/memory2';
  import { settings } from '../lib/settings.svelte';

  const m2 = settings.memory === 2; // the view is re-created when the memory changes
  const named2 = (n: string) => NAMED2.find((x) => x.name === n)!.g;
  /** short name: the strategy's name, else its bits */
  const nm = (g: number) => (m2 ? (NAMED2.find((x) => x.g === g)?.name ?? format2(g)) : label(g));
  import Heatmap from '../components/Heatmap.svelte';
  import SweepChart from '../components/SweepChart.svelte';
  import InvasionChart from '../components/InvasionChart.svelte';

  let client: GAClient;
  onMount(() => {
    client = new GAClient();
    client.onProgress = (d, t) => (sweepProgress = d / t);
    runInvasion();
  });
  onDestroy(() => client?.terminate());

  // ================================================================ invasion
  let X: Genome = $state(m2 ? named2('PAV2') : genomeOfName('PAVLOV')!);
  let Y: Genome = $state(m2 ? named2('ALLD') : genomeOfName('ALLD')!);
  let k = $state(5);
  let invNoise = $state(0.01);
  let invMut = $state(0);
  let invGens = $state(60);
  const invRuns = 20;
  const invM = $derived(m2 ? null : payoffMatrix(invNoise));
  const chk = $derived.by(() => {
    if (invM) return invasionCheck(invM, X, Y);
    const yx = expectedMatch2(Y, X, 150, invNoise), xx = expectedMatch2(X, X, 150, invNoise), yy = expectedMatch2(Y, Y, 150, invNoise);
    return invasionFromPayoffs(yx.pay1, xx.pay1, yy.pay1, yx.pay2);
  });
  const chal = $derived(invM ? challengers(invM, X) : []);

  // memory two: test all 262,144 genomes against the resident (in the worker)
  let chal2 = $state<{ count: number; better: number; best: { g: number; pay: number } | null; self: number; X: number; p: number } | null>(null);
  let chal2Running = $state(false);
  let chal2Progress = $state(0);
  async function testAll() {
    if (!client || chal2Running) return;
    chal2Running = true;
    chal2Progress = 0;
    const x = X, p = invNoise;
    client.onProgress = (d, t) => (chal2Progress = d / t);
    const res = await client.request<'challengers2'>({ type: 'challengers2', resident: x, p, rounds: 150 });
    client.onProgress = (d, t) => (sweepProgress = d / t);
    chal2 = { ...res, X: x, p };
    chal2Running = false;
  }
  const chal2Current = $derived(chal2 && chal2.X === X && chal2.p === invNoise ? chal2 : null);
  const nPop = 100;
  const fY = $derived(((k - 1) * chk.piYY + (nPop - k) * chk.piYX) / (nPop - 1));
  const fX = $derived(((nPop - k - 1) * chk.piXX + k * chk.piXY) / (nPop - 1));
  let traces: number[][] = $state([]);
  let invaded = $state(0);
  let grew = $state(0);
  let invTimer: ReturnType<typeof setTimeout> | undefined;
  let invToken = 0;

  async function runInvasion() {
    if (!client) return;
    const tok = ++invToken;
    const res = await client.request<'invasion'>({
      type: 'invasion', resident: X, mutant: Y, k, runs: invRuns, gens: invGens, memory: settings.memory,
      params: { ...DEFAULT_PARAMS, pNoise: invNoise, mutIndpb: invMut, seed: 1 },
    });
    if (tok !== invToken) return;
    traces = res.traces;
    invaded = res.invaded;
    grew = res.grew;
  }
  $effect(() => {
    void [X, Y, k, invNoise, invMut, invGens];
    clearTimeout(invTimer);
    invTimer = setTimeout(runInvasion, 150);
  });

  const fmt = (v: number) => v.toFixed(3);
  const verdictText = $derived.by(() => {
    if (X === Y) return 'The mutant is the resident itself: choose a different strategy.';
    const a = `${nm(Y)} earns ${fmt(chk.piYX)} against ${nm(X)}, which earns ${fmt(chk.piXX)} against itself.`;
    if (chk.invades && !chk.neutral) return `${a} The mutant does better than the residents do among themselves, so it can invade.`;
    if (chk.invades) return `${a} A tie; the second condition decides: ${nm(Y)} earns ${fmt(chk.piYY)} against itself, more than ${fmt(chk.piXY)} for ${nm(X)} against it, so it can invade.`;
    if (chk.neutral) return `${a} A tie, and ${nm(Y)} does not do better against itself (${fmt(chk.piYY)} vs ${fmt(chk.piXY)}), so it cannot invade, but it can spread by neutral drift.`;
    return `${a} The mutant does worse, so it cannot invade.`;
  });

  // ================================================================ noise sweep
  let sweepRuns = $state(m2 ? 2 : 6);
  let sweepGens = $state(m2 ? 150 : 300);
  const nLevels = m2 ? 6 : 11;
  let sweepMax = $state(0.1);
  let sweepPoints: SweepPoint[] = $state([]);
  let sweepProgress = $state(0);
  let sweeping = $state(false);
  async function runSweep() {
    if (!client || sweeping) return;
    sweeping = true;
    sweepProgress = 0;
    const ps = Array.from({ length: nLevels }, (_, i) => +((i * sweepMax) / (nLevels - 1)).toFixed(4));
    const res = await client.request<'sweep'>({ type: 'sweep', ps, runs: sweepRuns, gens: sweepGens, params: { ...DEFAULT_PARAMS, seed: 0 }, memory: settings.memory });
    sweepPoints = res.points;
    sweeping = false;
  }

  // ================================================================ tournament
  let allGenomes = $state(false);
  let tNoise = $state(0.01);
  let tRounds = $state(150);
  const tR = $derived(Math.max(1, Math.min(1000, Math.round(tRounds) || 1)));
  const tM = $derived(m2 ? null : payoffMatrix(tNoise, tR));
  const tIds = $derived(m2 ? NAMED2.map((x) => x.g) : allGenomes ? Array.from({ length: 32 }, (_, i) => i) : NAMED.map(([, g]) => g));
  const tM2 = $derived.by(() => {
    if (!m2) return null;
    const ids = NAMED2.map((x) => x.g);
    const M = ids.map(() => new Array(ids.length).fill(0));
    for (let i = 0; i < ids.length; i++)
      for (let j = i; j < ids.length; j++) {
        const r = expectedMatch2(ids[i], ids[j], tR, tNoise);
        M[i][j] = r.pay1; M[j][i] = r.pay2;
      }
    return M;
  });
  const tPay = (i: number, j: number) => (tM2 ? tM2[i][j] : tM![tIds[i]][tIds[j]]);
  const tName = (g: number) => (m2 ? nm(g) : allGenomes ? bitString(g) : label(g));
  const tFull = (g: number) => (m2 ? `${nm(g)} (${format2(g)})` : isNamed(g) ? `${label(g)} ${bitString(g)}` : bitString(g));
</script>

<section class="labs" aria-labelledby="labs-h">
  <div class="intro">
    <h2 id="labs-h">Labs</h2>
    <p class="dek">Three experiments behind the report’s arguments, run on the same model.</p>
  </div>

  <!-- ============================================================ invasion -->
  <article class="lab" aria-labelledby="inv-h">
    <header>
      <span class="num-head">1</span>
      <div>
        <h3 id="inv-h">Invasion</h3>
        <p class="dek">
          A gallery of 100 residents of one strategy, with <em>k</em> mutants of another. The report’s criterion:
          the mutant <em>Y</em> invades the resident <em>X</em> if π(<em>Y</em>,<em>X</em>) &gt; π(<em>X</em>,<em>X</em>), or if
          they are equal and π(<em>Y</em>,<em>Y</em>) &gt; π(<em>X</em>,<em>Y</em>).
        </p>
      </div>
    </header>
    <div class="inv-grid">
      <div class="inv-controls">
        {#if m2}
          <StrategyPicker2 bind:value={X} legend="Resident X" id="inv-x" />
          <StrategyPicker2 bind:value={Y} legend="Mutant Y" id="inv-y" />
        {:else}
          <StrategyPicker bind:value={X} legend="Resident X" id="inv-x" />
          <StrategyPicker bind:value={Y} legend="Mutant Y" id="inv-y" />
        {/if}
        <label class="field"><span>Mutants <span class="mono v">k = {k}</span></span><input type="range" min="1" max="50" bind:value={k} /></label>
        <label class="field"><span>Noise <span class="mono v">p = {invNoise.toFixed(3)}</span></span><input type="range" min="0" max="0.1" step="0.005" bind:value={invNoise} /></label>
        <label class="field"><span>Mutation per bit <span class="mono v">{invMut.toFixed(3)}</span></span><input type="range" min="0" max="0.05" step="0.001" bind:value={invMut} /></label>
        <label class="field"><span>Generations <span class="mono v">{invGens}</span></span><input type="range" min="10" max="300" step="10" bind:value={invGens} /></label>
      </div>
      <div class="inv-result">
        <table class="pi">
          <caption class="caption">Expected payoff per round, row against column</caption>
          <thead><tr><th></th><th scope="col">vs X</th><th scope="col">vs Y</th></tr></thead>
          <tbody>
            <tr><th scope="row"><span class="caption">X</span> {nm(X)}</th><td class="mono" class:hl={true}>{fmt(chk.piXX)}</td><td class="mono" class:hl2={chk.neutral}>{fmt(chk.piXY)}</td></tr>
            <tr><th scope="row"><span class="caption">Y</span> {nm(Y)}</th><td class="mono hl" class:win={chk.piYX > chk.piXX + 1e-9} class:lose={chk.piYX < chk.piXX - 1e-9}>{fmt(chk.piYX)}</td><td class="mono" class:hl2={chk.neutral}>{fmt(chk.piYY)}</td></tr>
          </tbody>
        </table>
        <p class="ruling" class:yes={chk.invades && X !== Y}>{verdictText}</p>
        <p class="caption">
          With {k} mutant{k === 1 ? '' : 's'} among {nPop}, the fitness of a mutant is <span class="mono">{fmt(fY)}</span> and that of a
          resident <span class="mono">{fmt(fX)}</span>.
          {#if m2}
            {#if chal2Current}
              {#if chal2Current.count === 0}
                <strong>None of the other 262,143 memory-two genomes</strong> earns as much against {nm(X)} as it earns against
                itself ({fmt(chal2Current.self)}): no mutant can invade it.
              {:else}
                <strong>{chal2Current.count.toLocaleString('en')} other genomes</strong> earn at least π(X,X) = {fmt(chal2Current.self)} against {nm(X)}
                ({chal2Current.better.toLocaleString('en')} strictly more), up to {fmt(chal2Current.best!.pay)} for <span class="mono">{format2(chal2Current.best!.g)}</span>.
                The report counts the resident itself too, so it says {(chal2Current.count + 1).toLocaleString('en')}.
              {/if}
            {:else}
              Whether any of the {N_GENOMES2.toLocaleString('en')} genomes can invade {nm(X)}:
              <button class="btn inline" onclick={testAll} disabled={chal2Running}>
                {chal2Running ? `Testing… ${Math.round(chal2Progress * 100)}%` : 'Test every mutant'}
              </button>
              <span class="caption">(about ten seconds)</span>
            {/if}
          {:else if chal.length === 0}No memory-one strategy earns as much against {label(X)} as it earns against itself: {label(X)} is not invadable.
          {:else}{chal.length} of the 32 genomes earn at least π(X,X) against {label(X)}: {chal.slice(0, 8).map(label).join(', ')}{chal.length > 8 ? ', …' : ''}.{/if}
        </p>
        <InvasionChart {traces} {invaded} {grew} mutant={nm(Y)} k0={k / nPop} />
      </div>
    </div>
  </article>

  <!-- ============================================================ noise sweep -->
  <article class="lab" aria-labelledby="sw-h">
    <header>
      <span class="num-head">2</span>
      <div>
        <h3 id="sw-h">Noise sweep</h3>
        <p class="dek">
          Short evolutionary runs at {m2 ? 'six' : 'eleven'} noise levels from 0 to {sweepMax}{m2 ? ', with memory-two strategies' : ''}. For each run: the mean payoff over the
          last 100 generations (the report’s response variable) and the strategy most frequent over that period.
          The report did not explore the levels between 0 and 0.01, where TFT gives way to GRIM.
        </p>
      </div>
    </header>
    <div class="sw-controls">
      <label class="field"><span>Runs per level <span class="mono v">{sweepRuns}</span></span><input type="range" min="1" max="20" bind:value={sweepRuns} /></label>
      <label class="field"><span>Generations <span class="mono v">{sweepGens}</span></span><input type="range" min="100" max="500" step="50" bind:value={sweepGens} /></label>
      <label class="field"><span>Highest noise</span>
        <select bind:value={sweepMax}><option value={0.01}>0.01</option><option value={0.02}>0.02</option><option value={0.05}>0.05</option><option value={0.1}>0.1</option></select>
      </label>
      <button class="btn primary" onclick={runSweep} disabled={sweeping}>{sweeping ? `Running… ${Math.round(sweepProgress * 100)}%` : 'Run the sweep'}</button>
    </div>
    {#if sweepPoints.length}
      <SweepChart points={sweepPoints} />
    {:else}
      <p class="caption empty">{sweeping ? 'Running in the background…' : `Not run yet: ${nLevels * sweepRuns} runs of ${sweepGens} generations, ${m2 ? `roughly ${Math.max(5, Math.round((nLevels * sweepRuns * sweepGens * 12) / 1000))} seconds` : 'a few seconds'}.`}</p>
    {/if}
  </article>

  <!-- ============================================================ tournament -->
  <article class="lab" aria-labelledby="tour-h">
    <header>
      <span class="num-head">3</span>
      <div>
        <h3 id="tour-h">Tournament</h3>
        <p class="dek">Every strategy against every other: the exact expected payoff per round of the row player. Darker ink, higher payoff.</p>
      </div>
    </header>
    <div class="tour-controls">
      {#if !m2}
        <div class="seg" role="group" aria-label="Which strategies">
          <button class="btn" aria-pressed={!allGenomes} onclick={() => (allGenomes = false)}>Named six</button>
          <button class="btn" aria-pressed={allGenomes} onclick={() => (allGenomes = true)}>All 32</button>
        </div>
      {:else}
        <p class="caption m2note">The memory-one strategies written as memory-two genomes, TF2T, and the report’s most frequent final genomes (PAV2, PAV2D, GRIM1; names ours).</p>
      {/if}
      <label class="field"><span>Noise <span class="mono v">p = {tNoise.toFixed(3)}</span></span><input type="range" min="0" max="0.1" step="0.005" bind:value={tNoise} /></label>
      <label class="field"><span>Rounds</span><input type="number" min="1" max="1000" bind:value={tRounds} /></label>
    </div>
    <Heatmap ids={tIds} pay={tPay} name={tName} full={tFull} named={m2 ? undefined : isNamed} compact={!m2 && allGenomes} />
  </article>
</section>

<style>
  .labs { padding-top: 1.3rem; }
  .intro { display: grid; gap: 0.4rem; margin-bottom: 0.4rem; }
  .lab { border-top: 3px double var(--rule-strong); padding: 1rem 0 1.6rem; }
  .lab header { display: grid; grid-template-columns: auto 1fr; gap: 0 1rem; align-items: start; margin-bottom: 0.9rem; }
  .num-head { font-family: var(--font-display); font-size: 3.2rem; line-height: 0.8; color: var(--brass); }
  .lab h3 { font-size: 1.7rem; margin-bottom: 0.25rem; }
  .v { color: var(--ink); font-size: 0.78rem; font-variant-caps: normal; letter-spacing: 0; float: right; }

  .inv-grid { display: grid; grid-template-columns: minmax(280px, 380px) minmax(0, 1fr); gap: 2rem; }
  .inv-controls { display: grid; gap: 0.7rem; align-content: start; }
  .pi { border-collapse: collapse; margin-bottom: 0.6rem; }
  .pi caption { text-align: left; caption-side: top; padding-bottom: 0.2rem; }
  .pi th, .pi td { padding: 0.25rem 0.8rem 0.25rem 0; text-align: left; border-bottom: 1px solid var(--rule); font-weight: 400; }
  .pi thead th { font-variant-caps: all-small-caps; letter-spacing: 0.06em; border-bottom: 1px solid var(--rule-strong); }
  .pi td { font-size: 1.05rem; }
  .pi td.hl { text-decoration: underline; text-decoration-color: var(--brass); text-decoration-thickness: 2px; text-underline-offset: 4px; }
  .pi td.win { color: var(--defect); font-weight: 700; }
  .pi td.lose { color: var(--coop); }
  .pi td.hl2 { background: var(--brass-tint); }
  .ruling { font-family: var(--font-display); font-size: 1.15rem; line-height: 1.35; border-left: 3px solid var(--coop); padding-left: 0.7rem; max-width: 70ch; }
  .ruling.yes { border-left-color: var(--defect); }

  .sw-controls, .tour-controls { display: flex; flex-wrap: wrap; gap: 0.8rem 1.6rem; align-items: end; margin-bottom: 0.9rem; }
  .sw-controls .field, .tour-controls .field { min-width: 12rem; }
  .empty { padding: 2rem 0; }
  .seg { display: flex; }
  .seg .btn + .btn { border-left: 0; }
  .btn.inline { min-height: 30px; padding: 0.15rem 0.6rem; margin: 0.2rem 0.3rem 0.2rem 0; }
  .m2note { max-width: 48ch; margin: 0; }

  @media (max-width: 860px) {
    .inv-grid { grid-template-columns: minmax(0, 1fr); }
  }
</style>
