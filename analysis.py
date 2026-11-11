"""Statistics and figures for the report. Run after main.py.

Writes:
  memory1/results/summary.txt        all tables (pilot, final payoff, tests, strategies, regimes,
                                     one-bit mutants, invasion)
  memory1/results/final_per_run.csv  the response variable of every run
  memory1/results/stats_pairwise.csv median difference + bootstrap CI, A12, Mann-Whitney (Holm)
  report/figures/*.pdf               memory-1 figures of the report (vector PDF, one file per plot)
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

FIG_DIR = os.path.join("report", "figures")
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
    "font.family": "serif", "font.serif": ["STIXGeneral", "DejaVu Serif"], "mathtext.fontset": "stix",
    "axes.formatter.use_mathtext": True, "axes.unicode_minus": False,
    "font.size": 8, "axes.titlesize": 8, "axes.labelsize": 8, "legend.fontsize": 8,
    "xtick.labelsize": 7, "ytick.labelsize": 7, "pdf.fonttype": 42,
    "axes.edgecolor": "#c3c2b7", "axes.labelcolor": INK2, "xtick.color": MUTED, "ytick.color": MUTED,
    "text.color": INK, "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6,
    "axes.spines.top": False, "axes.spines.right": False, "lines.linewidth": 1.6,
    "legend.frameon": False, "savefig.dpi": 300,
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
    fig.savefig(os.path.join(FIG_DIR, f"{name}.pdf"))
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

    # ---------- regime transitions (dominant strategy > 50% for >= 10 generations) ----------
    out.append("REGIMES: a regime = one strategy above 50% for at least 10 consecutive generations")
    for p in NOISE_LEVELS:
        trans, n_switch = {}, 0
        for r in range(n_runs):
            regimes, cur, length = [], None, 0
            for g in range(N_GEN + 1):
                best = max(COLUMNS, key=lambda c: hist[p][c][r, g])
                d = best if hist[p][best][r, g] > 0.5 else None
                cur, length = (d, length + 1) if d == cur else (d, 1)
                if length == 10 and d and (not regimes or regimes[-1] != d):
                    regimes.append(d)
            n_switch += len(regimes) > 1
            for a, b in zip(regimes, regimes[1:]):
                trans[(a, b)] = trans.get((a, b), 0) + 1
        time_frac = {c: float((hist[p][c][:, 100:] > 0.5).mean()) for c in COLUMNS}
        out.append(f"  p_noise={p}: runs with >= 1 change of regime: {n_switch}/{n_runs}; transitions: "
                   + ", ".join(f"{a}->{b} {n}" for (a, b), n in sorted(trans.items(), key=lambda kv: -kv[1])))
        out.append("    fraction of generations 101-500 with a strategy > 50%: "
                   + ", ".join(f"{c} {v:.2f}" for c, v in time_frac.items() if v > 0.005))
        mask = hist[p]["OTHER"] > 0.5
        if mask.any():
            top = sorted(((lab[1:], float(hist[p][lab][mask].mean())) for lab in GENOME_LABELS),
                         key=lambda kv: -kv[1])[:4]
            out.append("    genomes when OTHER > 50%: " + ", ".join(f"{g} {v:.2f}" for g, v in top))
    out.append("")

    # ---------- one-bit mutants of the residents (near-neutral drift paths) ----------
    out.append("ONE-BIT MUTANTS: pi(mutant, resident) - pi(resident, resident)  (> 0 invades, ~0 neutral drift)")
    for p in NOISE_LEVELS:
        for res in ("TFT", "GRIM", "ALLD"):
            g = next(k for k, v in NAMED.items() if v == res)
            r = genome_index(g)
            muts = [tuple(b ^ (i == k) for i, b in enumerate(g)) for k in range(len(g))]
            out.append(f"  p_noise={p} resident {res:>4}: " + ", ".join(
                f"{''.join(map(str, x))} {mats[p][genome_index(x), r] - mats[p][r, r]:+.3f}" for x in muts))
    out.append("")

    text = "\n".join(out)
    with open(os.path.join(RESULTS_DIR, "summary.txt"), "w") as f:
        f.write(text + "\n")
    print(text)

    # ================= FIGURES =================
    # One file per plot, drawn at its final size in the report (A4, text width 16.6 cm = 6.5 in;
    # a third of the width = 2.1 in), so the fonts appear at their real size.
    os.makedirs(FIG_DIR, exist_ok=True)
    FULL, THIRD = 6.4, 2.1
    tag = {p: f"p{str(p).replace('.', '')}" for p in NOISE_LEVELS}   # 0.01 -> p001
    lab_noise = {p: rf"$p_{{\mathrm{{noise}}}}={p}$" for p in NOISE_LEVELS}

    # legend shared by all the strategy figures
    fig = plt.figure(figsize=(FULL, 0.28))
    handles = [plt.Line2D([], [], color=STRAT_COLORS[c], lw=2, ls=":" if c == "OTHER" else "-")
               for c in COLUMNS]
    fig.legend(handles, list(COLUMNS), loc="center",
               ncol=len(COLUMNS), handlelength=1.8, columnspacing=1.6)
    save(fig, "strategy_legend")

    # 1. mean payoff over generations: median and IQR across runs
    fig, ax = plt.subplots(figsize=(FULL, 2.5), layout="constrained")
    for p in NOISE_LEVELS:
        y = hist[p]["mean_payoff"]
        med, q1, q3 = np.median(y, 0), *np.percentile(y, [25, 75], axis=0)
        ax.fill_between(gens, q1, q3, color=NOISE_COLORS[p], alpha=0.18, lw=0)
        ax.plot(gens, med, color=NOISE_COLORS[p], lw=1.3)
        ax.annotate(lab_noise[p], (gens[-1], med[-1]), xytext=(4, 0), textcoords="offset points",
                    va="center", color=INK2)
    for yv, txt in ((3, "full cooperation ($R=3$)"), (1, "full defection ($P=1$)")):
        ax.axhline(yv, color=MUTED, lw=0.7, ls="--")
        ax.text(6, yv + 0.03, txt, fontsize=7, color=MUTED, va="bottom")
    ax.set(xlabel="generation", ylabel="mean payoff per round", xlim=(0, N_GEN), ylim=(0.8, 3.2))
    save(fig, "fig_mean_payoff")

    # 2. final mean payoff per run: boxplot + points
    fig, ax = plt.subplots(figsize=(3.1, 2.4), layout="constrained")
    bp = ax.boxplot([final[p] for p in NOISE_LEVELS], widths=0.5, patch_artist=True, showfliers=False,
                    medianprops=dict(color=INK, lw=1.2))
    for patch, p in zip(bp["boxes"], NOISE_LEVELS):
        patch.set(facecolor=NOISE_COLORS[p], alpha=0.25, edgecolor=NOISE_COLORS[p])
    jit = np.random.default_rng(0)
    for i, p in enumerate(NOISE_LEVELS, start=1):
        ax.scatter(i + jit.uniform(-0.13, 0.13, n_runs), final[p], s=9, color=NOISE_COLORS[p],
                   edgecolor="white", linewidth=0.4, zorder=3)
    ax.set_xticks(range(1, len(NOISE_LEVELS) + 1), [str(p) for p in NOISE_LEVELS])
    ax.set(xlabel=r"$p_{\mathrm{noise}}$", ylabel=f"mean payoff (last {LAST} gen.)")
    save(fig, "fig_final_payoff")

    for p in NOISE_LEVELS:
        # 3. strategy frequencies over generations (mean across runs)
        fig, ax = plt.subplots(figsize=(THIRD, 1.75), layout="constrained")
        for c in COLUMNS:
            ax.plot(gens, hist[p][c].mean(0), color=STRAT_COLORS[c], lw=1.0,
                    ls=":" if c == "OTHER" else "-")
        ax.set(xlabel="generation", ylabel="mean frequency", xlim=(0, N_GEN), ylim=(0, 1))
        save(fig, f"fig_frequencies_{tag[p]}")

        # 4. final composition of each run, sorted by final payoff
        fig, ax = plt.subplots(figsize=(THIRD, 1.75), layout="constrained")
        order = np.argsort(final[p])
        bottom = np.zeros(n_runs)
        for c in COLUMNS:
            v = final_freq[p][c][order]
            ax.bar(range(n_runs), v, bottom=bottom, width=0.85, color=STRAT_COLORS[c], linewidth=0)
            bottom += v
        ax.set(xlabel="run (sorted by payoff)", ylabel="frequency", ylim=(0, 1), xlim=(-0.7, n_runs - 0.3),
               xticks=[])
        ax.grid(False)
        save(fig, f"fig_composition_{tag[p]}")

        # 5. one example run (shows the cycles that the averages hide)
        fig, ax = plt.subplots(figsize=(THIRD, 1.75), layout="constrained")
        for c in COLUMNS:
            ax.plot(gens, hist[p][c][0], color=STRAT_COLORS[c], lw=0.8,
                    ls=":" if c == "OTHER" else "-")
        ax.set(xlabel="generation", ylabel="frequency", xlim=(0, N_GEN), ylim=(0, 1))
        save(fig, f"fig_run_{tag[p]}")

        # 6. payoff matrix of the named strategies
        fig, ax = plt.subplots(figsize=(THIRD, 2.05), layout="constrained")
        sub = mats[p][np.ix_(idx, idx)]
        ax.imshow(sub, cmap="Blues", vmin=0, vmax=5)
        for i in range(len(names)):
            for j in range(len(names)):
                ax.text(j, i, f"{sub[i, j]:.2f}", ha="center", va="center", fontsize=5.6,
                        color="white" if sub[i, j] > 3.2 else INK)
        short = [n if n != "PAVLOV" else "PAVL." for n in names]
        ax.set_xticks(range(len(names)), short, rotation=90)
        ax.set_yticks(range(len(names)), short)
        ax.tick_params(labelsize=6.5, length=0)
        ax.set_xlabel("column (opponent)", fontsize=7)
        ax.grid(False)
        save(fig, f"fig_matrix_{tag[p]}")


if __name__ == "__main__":
    main()
