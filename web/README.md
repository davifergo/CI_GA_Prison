# The Dilemma Court

An interactive companion to the practical work *The iterated prisoner's dilemma: when does
cooperation emerge?* (`../report/main.tex`). Three views:

- **I. The Courtroom**: one match between two memory-one strategies, round by round, with
  the clerk's errors (noise), the reporter's tape, the cumulative score against the exact
  expectation ("precedent") and a verdict written from the match data.
- **II. The Gallery**: a population of 100 evolving under the genetic algorithm, with
  strategy frequencies, mean payoff, regimes and three presets that replay the runs shown
  in Figure 6 of the report.
- **III. Labs**: invasion of a resident by k mutants, a noise sweep, and the tournament
  matrix (6 named strategies or all 32).

A switch under the title (*memory one / two*, also `?m=2` in the URL) moves every view to the
memory-two strategies of `main_memory2.py`: 18-bit genomes shown as two opening moves plus a 4×4
table of replies, the most frequent genomes in the gallery (as in Figure 7 of the report), and in
Labs a check of all 262,144 mutants against a resident.

Built with Vite, TypeScript and Svelte 5. No server: it is a static site.

## Same model as the Python code

`src/lib/model/` is a port of `main.py`:

| Python (`main.py`)       | TypeScript                   |
| ------------------------ | ---------------------------- |
| `expected_match`         | `payoff.ts` `expectedMatch`  |
| `payoff_matrix`          | `payoff.ts` `payoffMatrix`   |
| `evaluate`               | `ga.ts` `evaluate`           |
| `run_ga` (DEAP 1.4)      | `ga.ts` `GA.step`            |
| Python's `random`        | `pyrandom.ts` (MT19937)      |

The port is exact, not approximate. The GA consumes Python's Mersenne Twister in the
same order as DEAP's `selTournament`, `varAnd`, `cxUniform` and `mutFlipBit`. The
floating-point operations follow the order used by NumPy/OpenBLAS, including the fused
multiply-adds of its `dgemv` kernel, emulated in `fma.ts`. As a result, the payoff
matrices and whole GA runs are identical to `main.py` bit for bit, and seed *s* here is
`run_ga(M, s)` there. Without this, exact fitness ties at `p_noise = 0` are broken
differently and a run diverges after a few hundred generations.

Memory two (`memory2.ts`) ports `main_memory2.py`. The pair payoffs match it to 1e-12 and the
noisy runs (seeds 100 and 200) match it generation by generation (mean payoff, number of
distinct genomes and most frequent genome). Without noise, exact fitness ties make memory-two
runs depend on the last bit of floating point, which the report already notes across machines,
so only the first generations are compared.

The single matches in the courtroom are sampled with a seeded `mulberry32`, so they are
reproducible but are not part of the Python model (Python never simulates single matches).

## Run

```bash
cd web
npm install
npm run dev        # http://localhost:5173
npm test           # Vitest: the model against main.py
npm run check      # type check (svelte-check)
npm run build      # static site in dist/
npm run preview    # serve dist/ on http://localhost:4173
```

### Tests

`src/lib/model/model.test.ts` checks:

- the payoffs given in the brief (e.g. TFT vs TFT = 2.521 with p = 0.01, ALLD vs GRIM = 1.18
  with p = 0.05);
- the three 32×32 payoff matrices, bit for bit;
- the fused multiply-add emulation against `math.fma` (3000 cases);
- Python's random stream;
- four complete GA runs: run 0 of each noise level (500 generations, every mean payoff and
  the final population) and one run with non-default parameters;
- memory two (`memory2.test.ts`): the values quoted in the report, 198 pair payoffs and the
  noisy runs 100 and 200 against `main_memory2.py` (fixture from `scripts/make_fixtures_m2.py`).

The reference values are in `src/lib/model/__fixtures__/python.json`. To regenerate them
after changing `main.py`, run from the repository root:

```bash
.venv/bin/python web/scripts/make_fixtures.py
```

### Screenshots

`scripts/screenshots.mjs` drives every view with Playwright and saves desktop (1440 px) and
phone (375 px) captures in light and dark mode. It also reports any horizontal overflow and
console errors.

```bash
npx playwright install chromium   # once
npm run build && npm run preview &
npm run shots                     # → screenshots/
```

## Deploy to GitHub Pages

The build uses relative asset paths (`base: './'`) and hash routing (`#court`, `#gallery`,
`#labs`), so `dist/` works under any path, including `https://<user>.github.io/<repo>/`.

**With the included workflow** (`../.github/workflows/pages.yml`): in the repository settings,
go to *Pages → Build and deployment → Source* and choose *GitHub Actions*. Every push to `main`
that changes `web/` runs the tests, builds and publishes the site.

**By hand:** `npm run build`, then publish the contents of `dist/` on any static host (or push
them to a `gh-pages` branch).

## Design notes

- The look is a 1930s newspaper court sketch. Ink on paper with pen linework (an SVG
  displacement filter adds a slight wobble), cross-hatched shading and paper grain.
  Everything is drawn in SVG in `components/Scene.svelte` and `components/Patterns.svelte`.
- The palette is defined as tokens in `src/app.css`. Dark mode is the same sheet printed in
  negative (warm black stock, cream ink), not a grey theme.
- Strategies are distinguished by hatching and a letter as well as by colour (verdigris for
  cooperative strategies, oxblood for defecting ones).
- Typefaces are IM Fell English (headings), Source Serif 4 (text) and JetBrains Mono
  (genomes and numbers), all self-hosted through Fontsource.
- Animations use decelerating or plain easing with no overshoot. With
  `prefers-reduced-motion`, every round shows its final state at once.
