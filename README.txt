Iterated prisoner's dilemma: when does cooperation emerge?
Computational Intelligence (CI-MAI) - Evolutionary Computation practical work, exercise 8

1. SETUP (Python >= 3.10)
-------------------------
    python3 -m venv .venv
    source .venv/bin/activate          (Windows: .venv\Scripts\activate)
    pip install -r requirements.txt

   Tested with Python 3.13, deap 1.4, numpy 2.5, scipy 1.18, matplotlib 3.11.

2. REPRODUCE THE RESULTS
------------------------
    python main.py        # runs the GA: 3 noise levels x 30 runs (about 1 minute)
    python analysis.py    # statistics + figures (a few seconds)

   Everything is seeded, so the results are identical on every execution.

3. FILES
--------
   main.py       GA (DEAP) and exact payoff computation.
   analysis.py   Pilot, effect sizes, tests, payoff matrices, invasion analysis, figures.

   results/history_noise_<p>.csv       one row per (run, generation): mean payoff of the
                                       population, frequency of the named strategies
                                       (ALLC, ALLD, TFT, PAVLOV, GRIM, STFT, OTHER) and of
                                       all 32 genomes (columns g<bits>).
   results/payoff_matrix_noise_<p>.csv expected payoff per round of every genome (row)
                                       against every genome (column), 32 x 32.
   results/final_per_run.csv           response variable of every run.
   results/stats_pairwise.csv          pairwise comparisons between noise levels.
   results/summary.txt                 all the tables used in the report.
   report/main.tex                     the report (LaTeX; upload the report/ folder to Overleaf).
   report/figures/*.pdf                figures of the report, one vector PDF per plot.
   report/robustness.py                extra check (longer matches, higher noise) cited in the report.

4. MODEL
--------
   Actions: 0 = C, 1 = D. Payoffs T = 5, R = 3, P = 1, S = 0.
   Genome (memory 1, 5 bits): first action, then the action after the previous outcome
   CC, CD, DC, DD (own action first).
     ALLC 00000, ALLD 11111, TFT 00101, PAVLOV 00110, GRIM 00111, STFT 10101.
   Noise: each intended action is flipped with probability p_noise; strategies react to
   the actions actually played.
   Fitness: average payoff per round against all the other individuals of the
   population (round robin, no game against oneself), so 3 = full cooperation and
   1 = full defection.
   The payoff of a match is its EXACT EXPECTATION over the noise: the outcome of a
   round is a 4-state Markov chain, propagated for 150 rounds. It is computed once per
   noise level for the 32 x 32 pairs. This removes the sampling noise of simulating one
   noisy match per pair, which would otherwise make every copy of a pair of strategies
   share the same lucky or unlucky realisation.

5. PARAMETERS (suggested defaults of the exercise)
--------------------------------------------------
   population 100, 500 generations, 150 rounds per match,
   uniform crossover (pc = 0.7, swap probability 0.5 per bit),
   bit-flip mutation (pm = 0.01 per bit, applied to every child),
   tournament selection of size 3, elitism of 2.
   Factor: p_noise in {0, 0.01, 0.05}. p_noise = 0 is the control.
   30 independent runs per level; level k (0, 1, 2) uses seeds 100k ... 100k + 29.
   Response variable: mean payoff of the population averaged over the last 100
   generations of each run.
   Statistics: difference of medians with a 95% bootstrap interval (10000 resamples),
   Vargha-Delaney A12, two-sided Mann-Whitney test with Holm correction.
