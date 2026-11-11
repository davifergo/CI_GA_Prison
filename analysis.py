"""Statistics and figures for the report. Run after main.py.

Writes:
  results/summary.txt               all tables (pilot, final payoff, tests, strategies, invasion)
  results/final_per_run.csv         the response variable of every run
  results/stats_pairwise.csv        median difference + bootstrap CI, A12, Mann-Whitney (Holm)
  figures/*.pdf and *.png           figures for the report
"""
import csv
import itertools
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import mannwhitneyu

from main import NOISE_LEVELS, N_GEN, RESULTS_DIR, COLUMNS, NAMED, GENOME_LABELS, genome_index

FIG_DIR = "figures"
LAST = 100            # response variable: average over the last LAST generations
N_PILOT = 10
N_BOOT = 10_000
BOOT_SEED = 12345

# Colors: one fixed color per entity (validated categorical palette, fixed order)
NOISE_COLORS = {0.0: "#2a78d6", 0.01: "#eb6834", 0.05: "#1baf7a"}
STRAT_COLORS = {"ALLC": "#2a78d6", "ALLD": "#eb6834", "TFT": "#1baf7a",
                "PAVLOV": "#eda100", "GRIM": "#e87ba4", "STFT": "#6250d6", "OTHER": "#b5b3ab"}
INK, INK2, MUTED, GRID = "#0b0b0b", "#52514e", "#898781", "#e1e0d9"

plt.rcParams.update({
    "font.size": 9, "axes.titlesize": 10, "axes.labelsize": 9, "legend.fontsize": 8,
    "axes.edgecolor": "#c3c2b7", "axes.labelcolor": INK2, "xtick.color": MUTED, "ytick.color": MUTED,
    "text.color": INK, "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6,
    "axes.spines.top": False, "axes.spines.right": False, "lines.linewidth": 1.6,
    "legend.frameon": False, "savefig.bbox": "tight", "savefig.dpi": 200,
})


def load_history(p):
    """Returns {column: array of shape (n_runs, n_gen + 1)}."""
    with open(os.path.join(RESULTS_DIR, f"history_noise_{p}.csv")) as f:
        rows = list(csv.DictReader(f))
    n_runs = max(int(r["run"]) for r in rows) + 1
    data = {}
    for col in rows[0]:
        data[col] = np.array([float(r[col]) for r in rows]).reshape(n_runs, N_GEN + 1)
    return data


def load_matrix(p):
    with open(os.path.join(RESULTS_DIR, f"payoff_matrix_noise_{p}.csv")) as f:
        rows = list(csv.reader(f))[1:]
    return np.array([[float(v) for v in r[1:]] for r in rows])


def a12(x, y):
    """Vargha-Delaney A12: probability that a value of x is larger than one of y."""
    x, y = np.asarray(x), np.asarray(y)
    greater = (x[:, None] > y[None, :]).sum()
    equal = (x[:, None] == y[None, :]).sum()
    return (greater + 0.5 * equal) / (len(x) * len(y))


def boot_median_diff(x, y, rng, n_boot=N_BOOT):
    """Difference of medians (x - y) with a 95% percentile bootstrap interval."""
    diffs = [np.median(rng.choice(x, len(x))) - np.median(rng.choice(y, len(y)))
             for _ in range(n_boot)]
    return np.median(x) - np.median(y), *np.percentile(diffs, [2.5, 97.5])


def boot_median_ci(x, rng, n_boot=N_BOOT):
    meds = [np.median(rng.choice(x, len(x))) for _ in range(n_boot)]
    return np.percentile(meds, [2.5, 97.5])


def holm(pvals):
    order = np.argsort(pvals)
    adj = np.empty(len(pvals))
    running = 0.0
    for rank, i in enumerate(order):
        running = max(running, (len(pvals) - rank) * pvals[i])
        adj[i] = min(1.0, running)
    return adj


def save(fig, name):
    os.makedirs(FIG_DIR, exist_ok=True)
    for ext in ("pdf", "png"):
        fig.savefig(os.path.join(FIG_DIR, f"{name}.{ext}"))
    plt.close(fig)


def main():
    rng = np.random.default_rng(BOOT_SEED)
    hist = {p: load_history(p) for p in NOISE_LEVELS}
    mats = {p: load_matrix(p) for p in NOISE_LEVELS}
    gens = np.arange(N_GEN + 1)
    final = {p: hist[p]["mean_payoff"][:, -LAST:].mean(axis=1) for p in NOISE_LEVELS}
    final_freq = {p: {c: hist[p][c][:, -LAST:].mean(axis=1) for c in COLUMNS} for p in NOISE_LEVELS}
    out = []

    # ---------- pilot: spread of the first N_PILOT runs -> is N_RUNS enough? ----------
    out.append(f"PILOT (first {N_PILOT} runs; response = mean payoff of the last {LAST} generations)")
    out.append(f"{'p_noise':>8} {'median':>8} {'sd':>7} {'IQR':>7} {'95% CI half-width, n=10':>24} {'n=30':>7}")
    for p in NOISE_LEVELS:
        x, xall = final[p][:N_PILOT], final[p]
        lo, hi = boot_median_ci(x, rng)
        lo30, hi30 = boot_median_ci(xall, rng)
        q1, q3 = np.percentile(x, [25, 75])
        out.append(f"{p:>8} {np.median(x):8.3f} {np.std(x, ddof=1):7.3f} {q3 - q1:7.3f} "
                   f"{(hi - lo) / 2:24.3f} {(hi30 - lo30) / 2:7.3f}")
    pilot_pairs = [(a, b, a12(final[a][:N_PILOT], final[b][:N_PILOT]))
                   for a, b in itertools.combinations(NOISE_LEVELS, 2)]
    out.append("Pilot A12: " + ", ".join(f"{a} vs {b}: {v:.2f}" for a, b, v in pilot_pairs))
    out.append("")

    # ---------- final payoff per noise level ----------
    n_runs = len(final[NOISE_LEVELS[0]])
    out.append(f"FINAL MEAN PAYOFF ({n_runs} runs per noise level)")
    for p in NOISE_LEVELS:
        lo, hi = boot_median_ci(final[p], rng)
        q1, q3 = np.percentile(final[p], [25, 75])
        out.append(f"  p_noise={p:<5} median {np.median(final[p]):.3f}  95% CI [{lo:.3f}, {hi:.3f}]  "
                   f"IQR [{q1:.3f}, {q3:.3f}]  min {final[p].min():.3f}  max {final[p].max():.3f}")
    out.append("")

    with open(os.path.join(RESULTS_DIR, "final_per_run.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["p_noise", "run", "final_mean_payoff"] + [f"freq_{c}" for c in COLUMNS])
        for p in NOISE_LEVELS:
            for r in range(n_runs):
                w.writerow([p, r, f"{final[p][r]:.6f}"] + [f"{final_freq[p][c][r]:.4f}" for c in COLUMNS])

    # ---------- pairwise tests ----------
    pairs = list(itertools.combinations(NOISE_LEVELS, 2))
    tests = []
    for a, b in pairs:
        d, lo, hi = boot_median_diff(final[a], final[b], rng)
        pval = mannwhitneyu(final[a], final[b], alternative="two-sided").pvalue
        tests.append({"A": a, "B": b, "median_diff_A_minus_B": d, "ci_low": lo, "ci_high": hi,
                      "A12": a12(final[a], final[b]), "mannwhitney_p": pval})
    for t, padj in zip(tests, holm(np.array([t["mannwhitney_p"] for t in tests]))):
        t["p_holm"] = padj
    with open(os.path.join(RESULTS_DIR, "stats_pairwise.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=tests[0].keys())
        w.writeheader()
        w.writerows(tests)
    out.append("PAIRWISE COMPARISONS of the final mean payoff (A vs B; Mann-Whitney, Holm-corrected)")
    for t in tests:
        out.append(f"  {t['A']} vs {t['B']}: median diff {t['median_diff_A_minus_B']:+.3f} "
                   f"[{t['ci_low']:+.3f}, {t['ci_high']:+.3f}]  A12 {t['A12']:.2f}  "
                   f"p {t['mannwhitney_p']:.2e}  p_holm {t['p_holm']:.2e}")
    out.append("")

    # ---------- strategy frequencies ----------
    out.append(f"STRATEGY FREQUENCY over the last {LAST} generations: median [IQR] across runs; "
               f"'dominant' = runs where it is > 50%")
    for p in NOISE_LEVELS:
        parts = []
        for c in COLUMNS:
            x = final_freq[p][c]
            q1, q3 = np.percentile(x, [25, 75])
            parts.append(f"{c} {np.median(x):.2f} [{q1:.2f},{q3:.2f}] dom {int((x > 0.5).sum())}")
        out.append(f"  p_noise={p}: " + " | ".join(parts))
    out.append("")
    # most frequent genomes overall (including unnamed ones)
    for p in NOISE_LEVELS:
        g = {lab: hist[p][lab][:, -LAST:].mean() for lab in GENOME_LABELS}
        top = sorted(g.items(), key=lambda kv: -kv[1])[:5]
        out.append(f"  top genomes p_noise={p}: " + ", ".join(
            f"{lab[1:]}{'(' + NAMED[tuple(int(c) for c in lab[1:])] + ')' if tuple(int(c) for c in lab[1:]) in NAMED else ''} {v:.2f}"
            for lab, v in top))
    out.append("  genome bits = first move, then reply after CC, CD, DC, DD (0 = C, 1 = D)")
    out.append("")

    # ---------- payoff matrices and invasion analysis of the named strategies ----------
    names = list(NAMED.values())
    idx = [genome_index(g) for g in NAMED]
    for p in NOISE_LEVELS:
        sub = mats[p][np.ix_(idx, idx)]
        out.append(f"PAYOFF MATRIX p_noise={p} (expected payoff per round of row vs column)")
        out.append("          " + "".join(f"{n:>8}" for n in names))
        for n, row in zip(names, sub):
            out.append(f"  {n:>8}" + "".join(f"{v:8.3f}" for v in row))
        out.append("  Invasion (mutant Y can invade resident X if pi(Y,X) > pi(X,X), "
                   "or = and pi(Y,Y) > pi(X,Y)):")
        for i, x in enumerate(names):
            inv = [names[j] for j in range(len(names)) if j != i and (
                sub[j, i] > sub[i, i] + 1e-9 or (abs(sub[j, i] - sub[i, i]) < 1e-9 and sub[j, j] > sub[i, j] + 1e-9))]
            # best invader against the full 32-genome space
            col = mats[p][:, genome_index(list(NAMED)[i])]
            best = int(np.argmax(col))
            out.append(f"    resident {x:>7}: invaded by {', '.join(inv) if inv else '-'}"
                       f"   (best reply among all 32: {GENOME_LABELS[best][1:]} with {col[best]:.3f} "
                       f"vs {sub[i, i]:.3f})")
        out.append("")

    text = "\n".join(out)
    with open(os.path.join(RESULTS_DIR, "summary.txt"), "w") as f:
        f.write(text + "\n")
    print(text)

    # ================= FIGURES =================
    labels = {p: f"$p_{{noise}}$ = {p}" for p in NOISE_LEVELS}

    # 1. mean payoff over generations: median and IQR across runs
    fig, ax = plt.subplots(figsize=(6.2, 3.2))
    for p in NOISE_LEVELS:
        y = hist[p]["mean_payoff"]
        med, q1, q3 = np.median(y, 0), *np.percentile(y, [25, 75], axis=0)
        ax.fill_between(gens, q1, q3, color=NOISE_COLORS[p], alpha=0.18, lw=0)
        ax.plot(gens, med, color=NOISE_COLORS[p], label=labels[p])
        ax.annotate(labels[p], (gens[-1], med[-1]), xytext=(4, 0), textcoords="offset points",
                    va="center", fontsize=8, color=INK2)
    ax.axhline(3, color=MUTED, lw=0.8, ls="--")
    ax.axhline(1, color=MUTED, lw=0.8, ls="--")
    ax.text(5, 3.03, "full cooperation (R = 3)", fontsize=7, color=MUTED, va="bottom")
    ax.text(5, 1.03, "full defection (P = 1)", fontsize=7, color=MUTED, va="bottom")
    ax.set(xlabel="generation", ylabel="mean payoff per round", xlim=(0, N_GEN), ylim=(0.8, 3.2))
    ax.set_title(f"Mean payoff of the population (median and IQR of {n_runs} runs)", loc="left")
    save(fig, "fig1_mean_payoff")

    # 2. strategy frequencies over generations (mean across runs), one panel per noise level
    fig, axes = plt.subplots(1, 3, figsize=(7.2, 2.6), sharey=True)
    for ax, p in zip(axes, NOISE_LEVELS):
        for c in COLUMNS:
            ax.plot(gens, hist[p][c].mean(0), color=STRAT_COLORS[c], lw=1.4,
                    ls=":" if c == "OTHER" else "-", label=c)
        ax.set_title(labels[p], loc="left")
        ax.set(xlabel="generation", xlim=(0, N_GEN), ylim=(0, 1))
    axes[0].set_ylabel("frequency (mean of runs)")
    axes[-1].legend(loc="upper left", bbox_to_anchor=(1.0, 1.0))
    save(fig, "fig2_strategy_frequencies")

    # 3. final mean payoff per run: boxplot + points
    fig, ax = plt.subplots(figsize=(4.2, 3.0))
    data = [final[p] for p in NOISE_LEVELS]
    bp = ax.boxplot(data, widths=0.5, patch_artist=True, showfliers=False,
                    medianprops=dict(color=INK, lw=1.4))
    for patch, p in zip(bp["boxes"], NOISE_LEVELS):
        patch.set(facecolor=NOISE_COLORS[p], alpha=0.25, edgecolor=NOISE_COLORS[p])
    jit = np.random.default_rng(0)
    for i, p in enumerate(NOISE_LEVELS, start=1):
        ax.scatter(i + jit.uniform(-0.12, 0.12, len(final[p])), final[p], s=12,
                   color=NOISE_COLORS[p], edgecolor="white", linewidth=0.5, zorder=3)
    ax.set_xticks(range(1, len(NOISE_LEVELS) + 1), [str(p) for p in NOISE_LEVELS])
    ax.set(xlabel="$p_{noise}$", ylabel=f"mean payoff, last {LAST} generations")
    ax.set_title(f"Final mean payoff ({n_runs} runs each)", loc="left")
    save(fig, "fig3_final_payoff")

    # 4. payoff matrices of the named strategies
    fig, axes = plt.subplots(1, 3, figsize=(7.4, 2.7))
    for ax, p in zip(axes, NOISE_LEVELS):
        sub = mats[p][np.ix_(idx, idx)]
        im = ax.imshow(sub, cmap="Blues", vmin=0, vmax=5)
        for i in range(len(names)):
            for j in range(len(names)):
                ax.text(j, i, f"{sub[i, j]:.2f}", ha="center", va="center", fontsize=6,
                        color="white" if sub[i, j] > 3.2 else INK)
        ax.set_xticks(range(len(names)), names, rotation=90, fontsize=7)
        ax.set_yticks(range(len(names)), names if ax is axes[0] else [], fontsize=7)
        ax.grid(False)
        ax.set_title(labels[p], loc="left")
    fig.colorbar(im, ax=axes, shrink=0.8, label="payoff of row vs column")
    save(fig, "fig4_payoff_matrices")

    # 5. one example run per noise level (shows the dynamics and cycles that averages hide)
    fig, axes = plt.subplots(1, 3, figsize=(7.2, 2.6), sharey=True)
    for ax, p in zip(axes, NOISE_LEVELS):
        for c in COLUMNS:
            ax.plot(gens, hist[p][c][0], color=STRAT_COLORS[c], lw=1.0,
                    ls=":" if c == "OTHER" else "-", label=c)
        ax.set_title(f"{labels[p]}, run 0", loc="left")
        ax.set(xlabel="generation", xlim=(0, N_GEN), ylim=(0, 1))
    axes[0].set_ylabel("frequency")
    axes[-1].legend(loc="upper left", bbox_to_anchor=(1.0, 1.0))
    save(fig, "fig5_example_runs")

    # 6. final composition of each run (stacked bars), sorted by payoff
    fig, axes = plt.subplots(1, 3, figsize=(7.2, 2.6), sharey=True)
    for ax, p in zip(axes, NOISE_LEVELS):
        order = np.argsort(final[p])
        bottom = np.zeros(n_runs)
        for c in COLUMNS:
            v = final_freq[p][c][order]
            ax.bar(range(n_runs), v, bottom=bottom, width=0.9, color=STRAT_COLORS[c],
                   edgecolor="white", linewidth=0.3, label=c)
            bottom += v
        ax.set_title(labels[p], loc="left")
        ax.set(xlabel="run (sorted by final payoff)", ylim=(0, 1), xticks=[])
        ax.grid(False)
    axes[0].set_ylabel(f"frequency, last {LAST} gen.")
    axes[-1].legend(loc="upper left", bbox_to_anchor=(1.0, 1.0))
    save(fig, "fig6_final_composition")


if __name__ == "__main__":
    main()
