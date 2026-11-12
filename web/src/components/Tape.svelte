<script lang="ts">
  import { actionChar } from '../lib/model/game';
  import type { Round } from '../lib/model/match';

  let { rounds, t, names, onjump }: { rounds: Round[]; t: number; names: [string, string]; onjump: (t: number) => void } =
    $props();

  let strip: HTMLDivElement | undefined = $state();
  // keep the current round in view
  $effect(() => {
    const el = strip?.querySelector<HTMLElement>(`[data-t="${t}"]`);
    if (!strip || !el) return;
    const { offsetLeft: x, offsetWidth: w } = el;
    if (x < strip.scrollLeft + 40 || x + w > strip.scrollLeft + strip.clientWidth - 40)
      strip.scrollTo({ left: x - strip.clientWidth / 2, behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth' });
  });

  function key(e: KeyboardEvent) {
    if (e.key === 'ArrowRight') { onjump(Math.min(rounds.length - 1, t + 1)); e.preventDefault(); }
    if (e.key === 'ArrowLeft') { onjump(Math.max(0, t - 1)); e.preventDefault(); }
    if (e.key === 'Home') { onjump(0); e.preventDefault(); }
    if (e.key === 'End') { onjump(rounds.length - 1); e.preventDefault(); }
  }
  const nErr = $derived(rounds.slice(0, t + 1).reduce((s, r) => s + +r.error[0] + +r.error[1], 0));
</script>

<section class="tape" aria-label="Court reporter's tape">
  <div class="head">
    <h3>The reporter’s tape</h3>
    <p class="caption">
      Every round as recorded. <span class="key c">C</span> cooperate, <span class="key d">D</span> defect,
      <span class="dagger">†</span> clerk’s error (the struck letter was intended). Click a round to go to it.
      <span class="mono count">{nErr} error{nErr === 1 ? '' : 's'} so far</span>
    </p>
  </div>
  <div class="frame">
    <div class="labels" aria-hidden="true">
      <span></span><span class="mono">{names[0]}</span><span class="mono">{names[1]}</span><span></span>
    </div>
    <div class="strip" bind:this={strip} onkeydown={key} tabindex="0" role="toolbar" aria-label="Rounds; arrow keys move between rounds">
      {#each rounds as r (r.t)}
        {@const shown = r.t <= t}
        <button
          type="button"
          class="col"
          class:cur={r.t === t}
          class:future={!shown}
          data-t={r.t}
          tabindex="-1"
          onclick={() => onjump(r.t)}
          aria-label="Round {r.t + 1}{shown ? `: ${names[0]} ${actionChar(r.played[0])}, ${names[1]} ${actionChar(r.played[1])}${r.error[0] || r.error[1] ? ', clerk’s error' : ''}` : ''}"
        >
          <span class="err">{shown && (r.error[0] || r.error[1]) ? '†' : ''}</span>
          {#each [0, 1] as k}
            <span class="cell" class:d={shown && r.played[k] === 1} class:c={shown && r.played[k] === 0} class:flip={shown && r.error[k]}>
              {shown ? actionChar(r.played[k]) : ''}
            </span>
          {/each}
          <span class="tick mono">{(r.t + 1) % 10 === 0 || r.t === 0 ? r.t + 1 : ''}</span>
        </button>
      {/each}
    </div>
  </div>
</section>

<style>
  .tape { margin-top: 1.2rem; }
  .head { display: flex; flex-wrap: wrap; align-items: baseline; gap: 0.2rem 1rem; margin-bottom: 0.4rem; }
  .head h3 { font-size: 1.3rem; }
  .head .caption { margin: 0; }
  .count { margin-left: 0.4rem; color: var(--ink); font-size: 0.78rem; }
  .key { display: inline-block; font-family: var(--font-mono); font-size: 0.75rem; width: 1.1em; text-align: center; border: 1px solid; line-height: 1.25; }
  .key.c { background: var(--coop-tint); color: var(--coop); }
  .key.d { background: var(--defect); color: var(--paper); border-color: var(--defect); }
  .dagger { color: var(--red-ink); font-weight: 700; }

  .frame {
    display: grid;
    grid-template-columns: auto 1fr;
    border-top: 1px solid var(--rule-strong);
    border-bottom: 1px solid var(--rule-strong);
    background:
      repeating-linear-gradient(90deg, transparent 0 13px, var(--rule) 13px 14px) 0 0 / auto 4px no-repeat,
      var(--paper-2);
  }
  .labels {
    display: grid;
    grid-template-rows: 14px 20px 20px 16px;
    row-gap: 2px;
    padding: 4px 6px 4px 4px;
    border-right: 1px solid var(--rule);
    font-size: 0.7rem;
    color: var(--ink-2);
    align-items: center;
    max-width: 7.5rem;
  }
  .labels span { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .strip {
    display: flex;
    overflow-x: auto;
    padding: 4px 4px 4px 2px;
    scrollbar-width: thin;
    scrollbar-color: var(--ink-3) transparent;
  }
  .col {
    display: grid;
    grid-template-rows: 14px 20px 20px 16px;
    row-gap: 2px;
    flex: none;
    width: 15px;
    padding: 0;
    margin: 0 1px 0 0;
    background: none;
    border: 0;
    cursor: pointer;
  }
  .col:hover .cell { outline: 1px solid var(--ink-3); }
  .cell {
    position: relative;
    display: grid;
    place-items: center;
    font-family: var(--font-mono);
    font-size: 0.66rem;
    font-weight: 600;
    border: 1px dotted var(--rule);
    line-height: 1;
  }
  .cell.c { background: var(--coop-tint); color: var(--coop); border: 1px solid color-mix(in srgb, var(--coop) 45%, transparent); }
  .cell.d { background: var(--defect); color: var(--paper); border: 1px solid var(--defect); }
  /* red ink slash over a falsified slip */
  .cell.flip::after {
    content: '';
    position: absolute;
    inset: -2px;
    background: linear-gradient(115deg, transparent 44%, var(--red-ink) 44% 56%, transparent 56%);
  }
  .err { color: var(--red-ink); font-weight: 700; font-size: 0.8rem; line-height: 14px; text-align: center; }
  .tick { font-size: 0.55rem; color: var(--ink-3); text-align: left; white-space: nowrap; line-height: 16px; }
  .col.cur .cell { outline: 2px solid var(--brass); outline-offset: 0; }
  .col.cur .tick { color: var(--ink); }
  .col.future .cell { opacity: 0.6; }
</style>
