"""Figures and a short summary for the memory-2 experiment.
Run after main_memory2.py (and main.py, for the comparison with memory 1).

Writes:
  results/memory2/summary.txt                      final payoff, memory 1 vs memory 2 tests, top
                                                   genomes and their invasion check
  results/memory2/figures/fig1_mean_payoff         mean payoff over generations (median and IQR)
  results/memory2/figures/fig2_final_payoff        boxplot of the final payoff per noise level
  results/memory2/figures/fig3_memory1_vs_memory2  boxplots of memory 1 and memory 2 side by side
  results/memory2/figures/fig4_diversity           distinct genomes and share of the top genome
  results/memory2/figures/fig5_report              figure 7 of the report: 3 panels at final size
"""
import csv
import os
from collections import Counter

import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import mannwhitneyu

# same style, helpers and settings as the memory-1 analysis (LAST = generations averaged);
# load_history reads the memory-1 results
from analysis import (a12, boot_median_ci, load_history, NOISE_COLORS,
                      INK, MUTED, LAST, BOOT_SEED)
from main_memory2 import (NOISE_LEVELS, N_GEN, ROUNDS, RESULTS_DIR, N_BITS, SHIFTS,
                          expected_matches)

FIG_DIR = os.path.join(RESULTS_DIR, "figures")
MEMORY_COLORS = {1: "#898781", 2: "#2a78d6"}  # grey = memory 1, blue = memory 2


def save(fig, name):
    os.makedirs(FIG_DIR, exist_ok=True)
    for ext in ("pdf", "png"):
        fig.savefig(os.path.join(FIG_DIR, f"{name}.{ext}"), bbox_inches="tight")
    plt.close(fig)


def load_history_m2(p):
    """Returns {column: array of shape (n_runs, N_GEN + 1)} for the memory-2 CSV."""
    with open(os.path.join(RESULTS_DIR, f"history_noise_{p}.csv")) as f:
        rows = list(csv.DictReader(f))
    n_runs = max(int(r["run"]) for r in rows) + 1
    data = {col: np.array([float(r[col]) for r in rows]).reshape(n_runs, N_GEN + 1)
            for col in ("mean_payoff", "n_distinct", "top_freq")}
    # the most frequent genome is text ("g0101..."), so it is kept as strings
    data["top_genome"] = np.array([r["top_genome"] for r in rows]).reshape(n_runs, N_GEN + 1)
    return data


def format_genome(g):
    """'g' + 18 bits -> '00 | 0101 0101 0101 0101': first two moves | one group of 4 per
    previous outcome (CC, CD, DC, DD), each group = reply after current CC, CD, DC, DD."""
    bits = g[1:]
    return bits[:2] + " | " + " ".join(bits[2 + 4 * k: 6 + 4 * k] for k in range(4))


def invasion_check(g, p_noise, chunk=32768):
    """Plays every one of the 2^18 genomes Y against genome g. Returns pi(g, g), the best
    pi(Y, g) and how many genomes Y (g itself included) obtain pi(Y, g) >= pi(g, g).
    If that number is 1, no mutant can invade a population of g."""
    G = np.array([[int(c) for c in g[1:]]])
    self_payoff = expected_matches(G, G, ROUNDS, p_noise)[0][0]
    best, n_ge = -1.0, 0
    for start in range(0, 2 ** N_BITS, chunk):
        ids = np.arange(start, min(start + chunk, 2 ** N_BITS))
        Y = (ids[:, None] >> SHIFTS) & 1  # bits of each genome (see evaluate() in main_memory2)
        f, _ = expected_matches(Y, np.repeat(G, len(Y), axis=0), ROUNDS, p_noise)
        best = max(best, f.max())
        n_ge += int((f >= self_payoff - 1e-9).sum())
    return self_payoff, best, n_ge


def boxplot(ax, data, positions, colors, width=0.5, size=10):
    """Boxplot with the individual runs drawn as points on top."""
    bp = ax.boxplot(data, positions=positions, widths=width, patch_artist=True,
                    showfliers=False, medianprops=dict(color=INK, lw=1.4))
    jitter = np.random.default_rng(0)
    for patch, x, y, c in zip(bp["boxes"], positions, data, colors):
        patch.set(facecolor=c, alpha=0.25, edgecolor=c)
        ax.scatter(x + jitter.uniform(-width / 4, width / 4, len(y)), y, s=size, color=c,
                   edgecolor="white", linewidth=0.5, zorder=3)


def plot_mean_payoff(ax, hist2, gens, labels):
    for p in NOISE_LEVELS:
        y = hist2[p]["mean_payoff"]
        med, q1, q3 = np.median(y, 0), *np.percentile(y, [25, 75], axis=0)
        ax.fill_between(gens, q1, q3, color=NOISE_COLORS[p], alpha=0.18, lw=0)
        ax.plot(gens, med, color=NOISE_COLORS[p], label=labels[p])
    for level in (3, 1):
        ax.axhline(level, color=MUTED, lw=0.8, ls="--")
    ax.set(xlabel="generation", ylabel="mean payoff per round", xlim=(0, N_GEN), ylim=(0.8, 3.2))


def plot_memory1_vs_memory2(ax, final1, final2, width=0.35, size=10):
    for final, mem in ((final1, 1), (final2, 2)):
        pos = np.arange(len(NOISE_LEVELS)) + (-0.2 if mem == 1 else 0.2)
        boxplot(ax, [final[p] for p in NOISE_LEVELS], pos, [MEMORY_COLORS[mem]] * len(pos),
                width=width, size=size)
        ax.plot([], [], "s", color=MEMORY_COLORS[mem], alpha=0.5, label=f"memory {mem}")
    ax.set_xticks(range(len(NOISE_LEVELS)), [str(p) for p in NOISE_LEVELS])
    ax.set(xlabel="$p_{noise}$", ylabel=f"mean payoff, last {LAST} generations")


def main():
    rng = np.random.default_rng(BOOT_SEED)
    hist2 = {p: load_history_m2(p) for p in NOISE_LEVELS}
    hist1 = {p: load_history(p) for p in NOISE_LEVELS}
    gens = np.arange(N_GEN + 1)
    # final payoff of each run = mean payoff of the last LAST generations (as in analysis.py)
    final2 = {p: hist2[p]["mean_payoff"][:, -LAST:].mean(axis=1) for p in NOISE_LEVELS}
    final1 = {p: hist1[p]["mean_payoff"][:, -LAST:].mean(axis=1) for p in NOISE_LEVELS}
    n_runs = len(final2[NOISE_LEVELS[0]])
    labels = {p: f"$p_{{noise}}$ = {p}" for p in NOISE_LEVELS}

    # ================= SUMMARY =================
    out = [f"MEMORY 2: FINAL MEAN PAYOFF (mean of the last {LAST} generations, {n_runs} runs)"]
    for p in NOISE_LEVELS:
        x = final2[p]
        lo, hi = boot_median_ci(x, rng)
        q1, q3 = np.percentile(x, [25, 75])
        out.append(f"  p_noise={p:<5} median {np.median(x):.3f}  95% CI [{lo:.3f}, {hi:.3f}]  "
                   f"IQR [{q1:.3f}, {q3:.3f}]  min {x.min():.3f}  max {x.max():.3f}")
    out.append("")

    out.append("MEMORY 2 vs MEMORY 1 (final mean payoff; A12 = P(memory 2 > memory 1), Mann-Whitney)")
    for p in NOISE_LEVELS:
        x2, x1 = final2[p], final1[p]
        pval = mannwhitneyu(x2, x1, alternative="two-sided").pvalue
        out.append(f"  p_noise={p:<5} median m2 {np.median(x2):.3f}  m1 {np.median(x1):.3f}  "
                   f"diff {np.median(x2) - np.median(x1):+.3f}  A12 {a12(x2, x1):.2f}  p {pval:.2e}")
    out.append("")

    out.append(f"DIVERSITY over the last {LAST} generations (median across runs)")
    for p in NOISE_LEVELS:
        nd = np.median(hist2[p]["n_distinct"][:, -LAST:].mean(axis=1))
        tf = np.median(hist2[p]["top_freq"][:, -LAST:].mean(axis=1))
        out.append(f"  p_noise={p:<5} distinct genomes {nd:.1f}  share of the most frequent genome {tf:.2f}")
    out.append("")

    out.append("MOST FREQUENT GENOME AT THE LAST GENERATION (how many runs end with each one)")
    out.append("  format: first two moves | 4 groups (previous outcome CC, CD, DC, DD), each with the "
               "reply after current CC, CD, DC, DD; 0 = C, 1 = D")
    out.append("  invasion check: pi(G,G) and the best pi(Y,G) over all 2^18 genomes Y; "
               "'#>=' = genomes with pi(Y,G) >= pi(G,G) (1 = only G itself: no mutant can invade)")
    for p in NOISE_LEVELS:
        tops = Counter(hist2[p]["top_genome"][:, -1])
        share = np.median(hist2[p]["top_freq"][:, -1])
        out.append(f"  p_noise={p} ({len(tops)} different genomes over {n_runs} runs; "
                   f"median share of the top genome in its population {share:.0%}):")
        for g, count in tops.most_common(3):
            self_payoff, best, n_ge = invasion_check(g, p)  # about 8 s each
            out.append(f"    {format_genome(g)}   in {count} runs   pi(G,G) {self_payoff:.3f}  "
                       f"best pi(Y,G) {best:.3f}  #>= {n_ge}")
    text = "\n".join(out)
    os.makedirs(RESULTS_DIR, exist_ok=True)
    with open(os.path.join(RESULTS_DIR, "summary.txt"), "w") as f:
        f.write(text + "\n")
    print(text)

    # ================= FIGURES =================
    # 1. mean payoff over generations: median and IQR across runs
    fig, ax = plt.subplots(figsize=(6.2, 3.2))
    plot_mean_payoff(ax, hist2, gens, labels)
    ax.text(5, 3.03, "full cooperation (R = 3)", fontsize=7, color=MUTED, va="bottom")
    ax.text(5, 1.03, "full defection (P = 1)", fontsize=7, color=MUTED, va="bottom")
    ax.legend(loc="lower right")
    ax.set_title(f"Memory 2: mean payoff of the population (median and IQR of {n_runs} runs)",
                 loc="left")
    save(fig, "fig1_mean_payoff")

    # 2. final payoff per noise level
    fig, ax = plt.subplots(figsize=(4.2, 3.0))
    boxplot(ax, [final2[p] for p in NOISE_LEVELS], range(1, len(NOISE_LEVELS) + 1),
            [NOISE_COLORS[p] for p in NOISE_LEVELS])
    ax.set_xticks(range(1, len(NOISE_LEVELS) + 1), [str(p) for p in NOISE_LEVELS])
    ax.set(xlabel="$p_{noise}$", ylabel=f"mean payoff, last {LAST} generations")
    ax.set_title(f"Memory 2: final mean payoff ({n_runs} runs each)", loc="left")
    save(fig, "fig2_final_payoff")

    # 3. memory 1 vs memory 2: two boxes per noise level
    fig, ax = plt.subplots(figsize=(5.0, 3.0))
    plot_memory1_vs_memory2(ax, final1, final2)
    ax.legend(loc="upper right")
    ax.set_title("Final mean payoff: memory 1 vs memory 2", loc="left")
    save(fig, "fig3_memory1_vs_memory2")

    # 4. diversity: how many distinct genomes, and how dominant the most frequent one is
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 2.8))
    for p in NOISE_LEVELS:
        axes[0].plot(gens, np.median(hist2[p]["n_distinct"], 0), color=NOISE_COLORS[p],
                     label=labels[p])
        axes[1].plot(gens, np.median(hist2[p]["top_freq"], 0), color=NOISE_COLORS[p])
    axes[0].set(xlabel="generation", ylabel="distinct genomes (median of runs)",
                xlim=(0, N_GEN), ylim=(0, None))
    axes[1].set(xlabel="generation", ylabel="share of the most frequent genome",
                xlim=(0, N_GEN), ylim=(0, 1))
    axes[0].legend(loc="upper right")
    axes[0].set_title("Memory 2: diversity of the population", loc="left")
    save(fig, "fig4_diversity")

    # 5. figure of the report: the three panels above, drawn at their final size (text width)
    fig, axes = plt.subplots(1, 3, figsize=(6.5, 2.2), gridspec_kw=dict(wspace=0.45))
    plot_mean_payoff(axes[0], hist2, gens, labels)
    axes[0].legend(loc="center right", fontsize=6, handlelength=1.2)
    plot_memory1_vs_memory2(axes[1], final1, final2, width=0.3, size=5)
    axes[1].set_ylabel(f"mean payoff, last {LAST} gen.")
    axes[1].legend(loc="lower left", fontsize=6, handlelength=1.0)
    for p in NOISE_LEVELS:
        axes[2].plot(gens, np.median(hist2[p]["top_freq"], 0), color=NOISE_COLORS[p])
    axes[2].set(xlabel="generation", ylabel="share of the top genome", xlim=(0, N_GEN), ylim=(0, 1))
    for ax, letter in zip(axes, "abc"):
        ax.set_title(f"({letter})", loc="left", fontsize=9)
    save(fig, "fig5_report")


if __name__ == "__main__":
    main()
