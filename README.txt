Iterated prisoner's dilemma: when does cooperation emerge?
Computational Intelligence (CI-MAI) - Evolutionary Computation practical work, exercise 8
David Fernández Gómez, Pol Marsol Torras

0. CONTENTS
-----------
   README.txt           this file
   requirements.txt     Python packages
   report.pdf           the report
   src/                 all the code (run every script from this folder's root, see 2)
   results/             all the outputs used in the report, as produced by the code:
     memory1/           main experiment (memory-1 strategies)
       figures/         memory-1 figures of the report (Figures 1-6)
     memory2/           extension (memory-2 strategies)
       figures/         memory-2 figures (fig5_report = Figure 7 of the report)
     check_exact.txt    check of the exact payoff computation (memory 1 and memory 2)

   Every script finds its input and output folders by itself (relative to the folder that
   contains src/ and results/), so nothing has to be moved or edited. Running a script
   overwrites its files in results/ with the same content (see 2 for the one exception).

1. SETUP (Python >= 3.10)
-------------------------
    python3 -m venv .venv
    source .venv/bin/activate          (Windows: .venv\Scripts\activate)
    pip install -r requirements.txt

   Tested with Python 3.13, deap 1.4, numpy 2.5, scipy 1.18, matplotlib 3.11.

2. REPRODUCE THE RESULTS (from the folder that contains README.txt)
-------------------------------------------------------------------
   Memory 1 (main experiment):
    python src/main.py              # GA: 3 noise levels x 30 runs (about 1 minute)
    python src/analysis.py          # statistics + figures (a few seconds)

   Memory 2 (extension; needs the memory-1 results for the comparison):
    python src/main_memory2.py      # GA: 3 noise levels x 30 runs (about 8 minutes)
    python src/analysis_memory2.py  # statistics, invasion checks, figures (about 2 minutes)

   Extra checks cited in the report (optional, independent of each other):
    python src/robustness.py        # memory 1 with 1000 rounds and p_noise 0.1, 0.25
                                    # (a few minutes) -> results/memory1/robustness.txt
    python src/check_exact.py       # exact payoffs vs a Monte Carlo simulator
                                    # (about 1 minute) -> results/check_exact.txt
    python src/check_collapses.py   # why some memory-2 runs without noise have a low payoff
                                    # (about 30 s; needs main_memory2.py results)
                                    # -> results/memory2/check_collapses.txt

   Everything is seeded, so the results are identical on every execution on the same machine.
   Exception: memory 2 without noise has many exact fitness ties, and floating-point
   differences of 1e-15 between machines or NumPy versions can change who wins a tournament,
   so on another computer those runs diverge (the conclusions do not change; see Limitations
   in the report). Memory 1 and memory 2 with noise reproduce exactly. The PDF figures embed
   their creation date, so the files differ in that field only.

3. FILES
--------
   src/main.py               memory 1: GA (DEAP) and exact payoff computation.
   src/analysis.py           memory 1: pilot, effect sizes, tests, payoff matrices, invasion
                             analysis, regimes, one-bit mutants, figures.
   src/main_memory2.py       memory 2: GA and exact payoff computation (computed on demand,
                             with a cache).
   src/analysis_memory2.py   memory 2: final payoff, comparison with memory 1, diversity,
                             three most frequent final genomes and their invasion check, figures.
   src/robustness.py         memory 1 with longer matches and more noise (10 runs each).
   src/check_exact.py        exact payoff computation vs an independent simulator.
   src/check_collapses.py    reruns four memory-2 runs without noise and inspects the whole
                             population around each collapse of the payoff (the meaning of
                             every column is explained at the top of the script).

   results/memory1/history_noise_<p>.csv        one row per (run, generation): mean payoff of
                                                the population, frequency of the named
                                                strategies (ALLC, ALLD, TFT, PAVLOV, GRIM,
                                                STFT, OTHER) and of all 32 genomes (g<bits>).
   results/memory1/payoff_matrix_noise_<p>.csv  expected payoff per round of every genome
                                                (row) against every genome (column), 32 x 32.
   results/memory1/final_per_run.csv            response variable of every run.
   results/memory1/stats_pairwise.csv           pairwise comparisons between noise levels.
   results/memory1/summary.txt                  all the memory-1 tables used in the report.
   results/memory1/figures/fig_*.pdf            memory-1 figures of the report (one PDF per
                                                plot; <p> in the name: p00 = 0, p001 = 0.01,
                                                p005 = 0.05).
   results/memory1/robustness.txt               output of src/robustness.py.

   results/memory2/history_noise_<p>.csv        one row per (run, generation): mean payoff,
                                                frequency of the memory-1 strategies embedded
                                                in memory 2 and of TF2T (in practice always
                                                OTHER), number of distinct genomes, most
                                                frequent genome and its share.
   results/memory2/summary.txt                  all the memory-2 tables used in the report.
   results/memory2/figures/fig*.pdf / .png      memory-2 figures (fig5_report is Figure 7 of
                                                the report).
   results/memory2/check_collapses.txt          output of src/check_collapses.py.
   results/check_exact.txt                      output of src/check_exact.py.

4. MODEL
--------
   Actions: 0 = C, 1 = D. Payoffs T = 5, R = 3, P = 1, S = 0.
   An outcome is written from the player's own point of view: CC, CD, DC, DD (own action
   first).
   Genome, memory 1 (5 bits): first action, then the action after the previous outcome
   CC, CD, DC, DD.
     ALLC 00000, ALLD 11111, TFT 00101, PAVLOV 00110, GRIM 00111, STFT 10101.
   Genome, memory 2 (18 bits): actions in rounds 1 and 2 (unconditional), then the action
   after each pair (previous outcome, current outcome): bit 2 + 4*previous + current,
   with outcomes numbered CC = 0, CD = 1, DC = 2, DD = 3. In the summaries a genome is
   written as "ab | CC CD DC DD": the two first moves, then one group of 4 bits per
   previous outcome with the reply after each current outcome.
   Noise: each intended action is flipped with probability p_noise; strategies react to
   the actions actually played.
   Fitness: average payoff per round against all the other individuals of the
   population (round robin, no game against oneself), so 3 = full cooperation and
   1 = full defection.
   The payoff of a match is its EXACT EXPECTATION over the noise, i.e. the average over
   infinitely many matches of 150 rounds: the state of the match is a Markov chain
   (memory 1: last outcome, 4 states; memory 2: last two outcomes, 16 states) whose
   distribution is propagated for 150 rounds. This removes the sampling noise of
   simulating one noisy match per pair, which would otherwise make every copy of a pair
   of strategies share the same lucky or unlucky realisation.
   Memory 1 computes the 32 x 32 payoff matrix once per noise level. Memory 2 has
   2^18 = 262144 genomes (a full matrix would need about 550 GB), so the payoff of a pair
   is computed only when the pair appears in the population and is cached during the run.

5. PARAMETERS (suggested defaults of the exercise, the same for memory 1 and memory 2)
--------------------------------------------------------------------------------------
   population 100, 500 generations, 150 rounds per match,
   uniform crossover (pc = 0.7, swap probability 0.5 per bit),
   bit-flip mutation (pm = 0.01 per bit, applied to every child),
   tournament selection of size 3, elitism of 2.
   Factor: p_noise in {0, 0.01, 0.05}. p_noise = 0 is the control.
   30 independent runs per level; level k (0, 1, 2) uses seeds 100k ... 100k + 29.
   Response variable: mean payoff of the population averaged over the last 100
   generations of each run.
   Statistics: difference of medians with a 95% bootstrap interval (10000 resamples),
   Vargha-Delaney A12, two-sided Mann-Whitney test (Holm correction between noise
   levels in memory 1).
