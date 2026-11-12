<script lang="ts">
  import { onDestroy } from 'svelte';
  import { genomeOfName, label, type Genome } from '../lib/model/game';
  import { expectedCumulative, expectedMatch } from '../lib/model/payoff';
  import { simulateMatch } from '../lib/model/match';
  import { roundCaption, verdict } from '../lib/model/analysis';
  import StrategyPicker from '../components/StrategyPicker.svelte';
  import CaseFile from '../components/CaseFile.svelte';
  import Tape from '../components/Tape.svelte';
  import ScoreChart from '../components/ScoreChart.svelte';
  import Scene from '../components/Scene.svelte';
  import StrategyPicker2 from '../components/StrategyPicker2.svelte';
  import CaseFile2 from '../components/CaseFile2.svelte';
  import { expectedMatch2, NAMED2, simulateMatch2 } from '../lib/model/memory2';
  import { settings } from '../lib/settings.svelte';

  // ---------------------------------------------------------------- the case
  const m2 = settings.memory === 2; // the view is re-created when the memory changes
  const named2 = (n: string) => NAMED2.find((x) => x.name === n)!.g;
  let s1: Genome = $state(m2 ? named2('PAV2') : genomeOfName('TFT')!);
  let s2: Genome = $state(m2 ? named2('TFT') : genomeOfName('GRIM')!);
  let pNoise = $state(m2 ? 0.05 : 0.02);
  let nRounds = $state(150);
  let seed = $state(7);

  const nR = $derived(Math.max(1, Math.min(1000, Math.round(nRounds) || 1)));
  const match = $derived(m2 ? simulateMatch2(s1, s2, nR, pNoise, seed >>> 0) : simulateMatch(s1, s2, nR, pNoise, seed >>> 0));
  const n = $derived(match.rounds.length);
  const exp2 = $derived(m2 ? expectedMatch2(s1, s2, n, pNoise, true) : null);
  const exp = $derived(exp2 ?? expectedMatch(s1, s2, n, pNoise));
  const expCum = $derived(exp2 ? { c1: exp2.c1, c2: exp2.c2 } : expectedCumulative(s1, s2, n, pNoise));
  const plate = (g: Genome) => NAMED2.find((x) => x.g === g)?.name ?? 'Custom';
  const names = $derived((m2 ? [plate(s1), plate(s2)] : [label(s1), label(s2)]) as [string, string]);

  // ---------------------------------------------------------------- playback
  let t = $state(-1); // last round shown (-1: court not yet in session)
  let playing = $state(false);
  let speed = $state(1);
  const SPEEDS = [1, 2, 5, 10, 25, 50];
  const BEAT = 1700; // ms per round at 1x
  const beat = $derived(BEAT / speed);
  let timer: ReturnType<typeof setTimeout> | undefined;
  let stepped = $state(false); // true when the last change was one round forward

  // a new case resets the session
  $effect(() => {
    void match;
    stop();
    stepped = false;
    t = -1;
  });

  function tick() {
    if (t >= n - 1) { playing = false; return; }
    stepped = true;
    t += 1;
    if (t >= n - 1) { playing = false; return; }
    timer = setTimeout(tick, beat);
  }
  function play() {
    if (t >= n - 1) t = -1;
    playing = true;
    clearTimeout(timer);
    tick();
  }
  function stop() { playing = false; clearTimeout(timer); }
  function toggle() { playing ? stop() : play(); }
  function step() { stop(); if (t < n - 1) { stepped = true; t += 1; } }
  function back() { stop(); if (t > -1) { stepped = false; t -= 1; } }
  function toEnd() { stop(); stepped = false; t = n - 1; }
  function jump(r: number) { stop(); stepped = r === t + 1; t = r; }
  // speed changes apply from the next round
  $effect(() => { void speed; if (playing) { clearTimeout(timer); timer = setTimeout(tick, beat); } });
  onDestroy(() => clearTimeout(timer));

  const round = $derived(t >= 0 ? match.rounds[t] : null);
  const finished = $derived(t === n - 1);
  const v = $derived(finished ? verdict(match, exp) : null);
  const caption = $derived(t >= 0 ? roundCaption(match, t) : 'The court is not yet in session. Press “Play” or “Step”.');
  const fast = $derived(speed >= 10 || !stepped);
</script>

<section class="court" aria-labelledby="court-h">
  <div class="intro">
    <h2 id="court-h">The Courtroom</h2>
    <p class="dek">
      Two strategies play one match. Each round both defendants hand the judge a sealed slip; the slips are
      opened together and scored. With noise, the clerk sometimes copies a slip wrongly, and both parties then
      react to the move that was recorded, not the one that was intended.
      {#if m2}With memory two, each defendant remembers the last two rounds: a rule for every pair of outcomes,
        sixteen in all, plus the first two moves.{/if}
    </p>
  </div>

  <form class="docket" onsubmit={(e) => e.preventDefault()} aria-label="The case">
    {#if m2}
      <StrategyPicker2 bind:value={s1} legend="Defendant A" id="pick-a" />
      <StrategyPicker2 bind:value={s2} legend="Defendant B" id="pick-b" />
    {:else}
      <StrategyPicker bind:value={s1} legend="Defendant A" id="pick-a" />
      <StrategyPicker bind:value={s2} legend="Defendant B" id="pick-b" />
    {/if}
    <div class="params">
      <label class="field noise">
        <span>Clerk’s error rate <span class="mono val">p = {pNoise.toFixed(3)}</span></span>
        <input type="range" min="0" max="0.2" step="0.005" bind:value={pNoise} />
      </label>
      <label class="field"><span>Rounds</span><input type="number" min="1" max="1000" bind:value={nRounds} /></label>
      <label class="field"><span>Seed</span><input type="number" min="0" step="1" bind:value={seed} /></label>
    </div>
  </form>

  <div class="bench-row">
    <div class="file-a">
      {#if m2}<CaseFile2 genome={s1} side="left" letter="A" active={round ? round.rule[0] : -1} />
      {:else}<CaseFile genome={s1} side="left" letter="A" active={round ? round.rule[0] : -1} />{/if}
    </div>
    <div class="scene">
      <Scene {match} {t} {beat} {fast} {names} />
      <p class="round-caption" aria-live="polite">{caption}</p>
      <div class="transport" role="group" aria-label="Playback">
        <button class="btn" onclick={back} disabled={t < 0} aria-label="Previous round">‹ Back</button>
        <button class="btn primary" onclick={toggle} aria-pressed={playing}>{playing ? 'Pause' : t >= n - 1 ? 'Replay' : 'Play'}</button>
        <button class="btn" onclick={step} disabled={t >= n - 1}>Step ›</button>
        <button class="btn" onclick={toEnd} disabled={t >= n - 1}>To verdict »</button>
        <label class="speed">
          <span class="kicker">Speed</span>
          <select bind:value={speed} aria-label="Playback speed">
            {#each SPEEDS as s}<option value={s}>{s}×</option>{/each}
          </select>
        </label>
      </div>
    </div>
    <div class="file-b">
      {#if m2}<CaseFile2 genome={s2} side="right" letter="B" active={round ? round.rule[1] : -1} />
      {:else}<CaseFile genome={s2} side="right" letter="B" active={round ? round.rule[1] : -1} />{/if}
    </div>

    <aside class="side" aria-label="Score">
      <h3>The score</h3>
      <ScoreChart rounds={match.rounds} {t} expected={expCum} {names} />
      <dl class="precedent">
        <dt>Precedent <span class="caption">exact expected points per round</span></dt>
        <dd><span class="mono">{exp.pay1.toFixed(3)}</span> {names[0]} · <span class="mono">{exp.pay2.toFixed(3)}</span> {names[1]}</dd>
        <dt>This match so far</dt>
        <dd>
          {#if t >= 0}
            <span class="mono">{(round!.total[0] / (t + 1)).toFixed(3)}</span> · <span class="mono">{(round!.total[1] / (t + 1)).toFixed(3)}</span>
            <span class="caption">after {t + 1} round{t ? 's' : ''}</span>
          {:else}—{/if}
        </dd>
      </dl>
    </aside>
  </div>

  <Tape rounds={match.rounds} {t} {names} onjump={jump} />

  <section class="verdict" aria-live="polite" aria-labelledby="verdict-h">
    <h3 id="verdict-h">The verdict</h3>
    {#if v}
      <p class="v-head">{v.heading}</p>
      {#each v.paragraphs as para}<p>{para}</p>{/each}
    {:else}
      <p class="caption">The judge rules when the last round has been recorded ({n - Math.max(0, t + 1)} to go).</p>
    {/if}
  </section>
</section>

<style>
  .court { padding-top: 1.3rem; }
  .intro { display: grid; gap: 0.4rem; margin-bottom: 1rem; }

  .docket {
    display: grid;
    grid-template-columns: auto auto 1fr;
    gap: 0.8rem 2rem;
    align-items: start;
    padding: 0.7rem 0 0.8rem;
    border-top: 1px solid var(--rule-strong);
    border-bottom: 1px solid var(--rule);
  }
  .params { display: flex; gap: 1rem 1.2rem; align-items: end; justify-content: end; flex-wrap: wrap; }
  .noise { min-width: 12rem; flex: 1; max-width: 18rem; }
  .val { color: var(--ink); font-size: 0.8rem; font-variant-caps: normal; letter-spacing: 0; }

  .bench-row {
    display: grid;
    grid-template-columns: minmax(200px, 240px) minmax(0, 1fr) minmax(200px, 240px) minmax(260px, 300px);
    grid-template-areas: 'fa scene fb side';
    gap: 1.2rem;
    margin-top: 1rem;
    align-items: start;
  }
  .file-a { grid-area: fa; margin-top: 2.5rem; }
  .file-b { grid-area: fb; margin-top: 2.5rem; }
  .scene { grid-area: scene; min-width: 0; }
  .side { grid-area: side; border-left: 1px solid var(--rule); padding-left: 1.2rem; }
  .side h3 { font-size: 1.3rem; margin-bottom: 0.3rem; }

  .round-caption { min-height: 2.8em; margin: 0.4rem 0 0.2rem; text-align: center; font-style: italic; color: var(--ink-2); font-size: 0.95rem; }
  .transport { display: flex; flex-wrap: wrap; gap: 0.4rem; justify-content: center; align-items: end; }
  .speed { display: inline-flex; align-items: end; gap: 0.35rem; margin-left: 0.4rem; }
  .speed select { min-width: 4.2rem; font-family: var(--font-mono); font-size: 0.9rem; }

  .precedent { margin: 0.8rem 0 0; display: grid; gap: 0.15rem; align-content: start; }
  .precedent dt { font-variant-caps: all-small-caps; letter-spacing: 0.07em; color: var(--ink-2); margin-top: 0.4rem; }
  .precedent dt .caption { font-variant-caps: normal; letter-spacing: 0; font-style: italic; }
  .precedent dd { margin: 0; }

  .verdict {
    margin-top: 1.4rem;
    padding-top: 0.8rem;
    border-top: 3px double var(--rule-strong);
    column-width: 30ch;
    column-gap: 2rem;
    column-rule: 1px solid var(--rule);
  }
  .verdict h3 { column-span: all; font-size: 1.6rem; margin-bottom: 0.3rem; }
  .v-head { column-span: all; font-family: var(--font-display); font-size: 1.35rem; font-style: italic; margin-bottom: 0.6rem; }
  .verdict p { break-inside: avoid; }

  @media (max-width: 1500px) {
    .bench-row {
      grid-template-columns: minmax(200px, 250px) minmax(0, 1fr) minmax(200px, 250px);
      grid-template-areas: 'fa scene fb' 'side side side';
    }
    .side { border-left: 0; padding-left: 0; border-top: 1px solid var(--rule); padding-top: 0.8rem; display: grid; grid-template-columns: minmax(0, 460px) minmax(0, 1fr); gap: 0 2.5rem; align-items: start; }
    .side h3 { grid-column: 1 / -1; }
  }
  @media (max-width: 960px) {
    .docket { grid-template-columns: 1fr 1fr; }
    .params { grid-column: 1 / -1; justify-content: start; }
    .bench-row { grid-template-columns: 1fr 1fr; grid-template-areas: 'scene scene' 'fa fb' 'side side'; }
    .file-a, .file-b { margin-top: 0; }
  }
  @media (max-width: 640px) {
    .docket { grid-template-columns: 1fr; }
    .bench-row { grid-template-columns: minmax(0, 1fr); grid-template-areas: 'scene' 'fa' 'fb' 'side'; }
    .side { grid-template-columns: minmax(0, 1fr); }
    .noise { max-width: none; }
  }
</style>
