<script lang="ts">
  import Patterns from './components/Patterns.svelte';
  import Courtroom from './views/Courtroom.svelte';
  import Gallery from './views/Gallery.svelte';
  import Labs from './views/Labs.svelte';
  import { settings, setMemory } from './lib/settings.svelte';

  const VIEWS = [
    { id: 'court', numeral: 'I', title: 'The Courtroom', sub: 'one match, round by round' },
    { id: 'gallery', numeral: 'II', title: 'The Gallery', sub: 'a population evolving' },
    { id: 'labs', numeral: 'III', title: 'Labs', sub: 'invasion, noise, tournament' },
  ] as const;
  type ViewId = (typeof VIEWS)[number]['id'];

  const fromHash = (): ViewId => {
    const h = location.hash.replace(/^#\/?/, '').split('?')[0];
    return (VIEWS.find((v) => v.id === h)?.id ?? 'court') as ViewId;
  };
  let view: ViewId = $state(fromHash());
  $effect(() => {
    const on = () => (view = fromHash());
    addEventListener('hashchange', on);
    return () => removeEventListener('hashchange', on);
  });

  // theme: follows the system unless the reader chooses one
  let theme: 'light' | 'dark' | null = $state(
    (document.documentElement.dataset.theme as 'light' | 'dark' | undefined) ?? null,
  );
  const systemDark = matchMedia('(prefers-color-scheme: dark)');
  const effectiveDark = () => (theme ? theme === 'dark' : systemDark.matches);
  let isDark = $state(effectiveDark());
  function toggleTheme() {
    theme = effectiveDark() ? 'light' : 'dark';
    document.documentElement.dataset.theme = theme;
    try { localStorage.setItem('theme', theme); } catch { /* storage unavailable */ }
    isDark = effectiveDark();
  }
  $effect(() => {
    const on = () => (isDark = effectiveDark());
    systemDark.addEventListener('change', on);
    return () => systemDark.removeEventListener('change', on);
  });
</script>

<Patterns />

<header class="masthead">
  <div class="page">
    <div class="topline">
      <span>Supplement to <em>The iterated prisoner’s dilemma: when does cooperation emerge?</em></span>
      <button class="theme" onclick={toggleTheme} aria-label={isDark ? 'Print on white stock' : 'Print in negative'}>
        <svg viewBox="0 0 20 20" width="18" height="18" aria-hidden="true">
          <circle cx="10" cy="10" r="7.2" fill="none" stroke="currentColor" stroke-width="1.3" />
          <path d="M10 2.8 A7.2 7.2 0 0 1 10 17.2 Z" fill="currentColor" />
        </svg>
        <span>{isDark ? 'Positive' : 'Negative'}</span>
      </button>
    </div>
    <hr class="rule-double" />
    <div class="nameplate">
      <h1>The Dilemma Court</h1>
      <p class="motto">
        <span class="nw">Strategies with memory
          <span class="mem" role="group" aria-label="Memory of the strategies">
            <button aria-pressed={settings.memory === 1} onclick={() => setMemory(1)}>one</button><button aria-pressed={settings.memory === 2} onclick={() => setMemory(2)}>two</button>
          </span>,</span>
        <span class="nw">tried under T&nbsp;5 · R&nbsp;3 · P&nbsp;1 · S&nbsp;0</span>
      </p>
    </div>
    <hr class="rule" />
    <nav aria-label="Sections">
      {#each VIEWS as v}
        <a href={'#' + v.id + (settings.memory === 2 ? '?m=2' : '')} aria-current={view === v.id ? 'page' : undefined}>
          <span class="numeral">{v.numeral}.</span>
          <span class="t">{v.title}</span>
          <span class="s">{v.sub}</span>
        </a>
      {/each}
    </nav>
    <hr class="rule-double" />
  </div>
</header>

<main class="page">
  {#key settings.memory}
    {#if view === 'court'}
      <Courtroom />
    {:else if view === 'gallery'}
      <Gallery />
    {:else}
      <Labs />
    {/if}
  {/key}
</main>

<footer class="page colophon">
  <hr class="rule" />
  <p>
    {#if settings.memory === 1}
      Every number on these pages comes from the same model as the report: payoffs per round are exact
      expectations over the noise (a four-state Markov chain), and the genetic algorithm reproduces
      <code>main.py</code> draw for draw, so seed 0 here is run 0 there.
    {:else}
      Memory two follows <code>main_memory2.py</code>: payoffs are exact expectations over a sixteen-state
      Markov chain (the last two outcomes), computed for each pair the first time it appears. With noise
      the genetic algorithm reproduces the report’s runs generation by generation; without noise, exact
      fitness ties make runs depend on the last bit of floating point, as the report notes.
    {/if}
  </p>
</footer>

<style>
  .masthead { padding-top: 0.6rem; }
  .masthead .page, .colophon { padding-bottom: 0; }
  .topline {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 1rem;
    font-size: 0.82rem;
    color: var(--ink-2);
    padding-bottom: 0.35rem;
  }
  .theme {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    background: none;
    border: 0;
    cursor: pointer;
    padding: 0.2rem 0;
    font-variant-caps: all-small-caps;
    letter-spacing: 0.07em;
    font-size: 0.95rem;
    flex: none;
    min-height: 32px;
  }
  .nameplate {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 0.2rem 1.5rem;
    padding: 0.45rem 0 0.35rem;
  }
  h1 {
    font-size: clamp(2.3rem, 1.4rem + 4vw, 4.4rem);
    line-height: 0.95;
    letter-spacing: -0.005em;
  }
  .nw { white-space: nowrap; }
  .mem { display: inline-flex; vertical-align: 1px; margin: 0 0.1rem 0 0.25rem; border: 1px solid var(--ink); }
  .mem button {
    font-family: var(--font-display); font-style: italic; font-size: 1.02rem; line-height: 1.15;
    background: none; border: 0; padding: 0.05rem 0.55rem 0.1rem; cursor: pointer; color: var(--ink); min-height: 30px;
  }
  .mem button + button { border-left: 1px solid var(--ink); }
  .mem button[aria-pressed='true'] { background: var(--ink); color: var(--paper); }
  .mem button:hover:not([aria-pressed='true']) { background: var(--paper-3); }
  .motto {
    margin: 0;
    font-style: italic;
    color: var(--ink-2);
    font-size: 0.98rem;
  }
  nav {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
  }
  nav a {
    display: grid;
    grid-template-columns: auto 1fr;
    column-gap: 0.45rem;
    padding: 0.5rem 0.75rem 0.55rem;
    text-decoration: none;
    border-left: 1px solid var(--rule);
  }
  nav a:first-child { border-left: 0; padding-left: 0; }
  nav .numeral { font-family: var(--font-display); font-size: 1.15rem; color: var(--ink-3); grid-row: span 2; }
  nav .t { font-family: var(--font-display); font-size: 1.25rem; line-height: 1.2; }
  nav .s { font-size: 0.8rem; color: var(--ink-3); font-style: italic; }
  nav a[aria-current='page'] .t { text-decoration: underline; text-decoration-thickness: 2px; text-underline-offset: 4px; text-decoration-color: var(--brass); }
  nav a[aria-current='page'] .numeral { color: var(--brass); }
  nav a:hover .t { text-decoration: underline; text-decoration-thickness: 1px; text-underline-offset: 4px; }

  .colophon { color: var(--ink-2); font-size: 0.85rem; padding-bottom: 2rem; }
  .colophon p { max-width: 80ch; margin-top: 0.8rem; }

  @media (max-width: 640px) {
    .topline > span { font-size: 0.75rem; }
    nav a { padding: 0.45rem 0.4rem; grid-template-columns: 1fr; }
    nav .numeral { grid-row: auto; font-size: 0.95rem; }
    nav .t { font-size: 1.02rem; }
    nav .s { display: none; }
  }
</style>
