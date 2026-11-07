#!/usr/bin/env python3
"""VECTOR Comparative Analysis - Publication-quality plots (dark theme, PNG only).

Reads processed aggregated CSVs and exports PNG (300 DPI) figures only.
Plots with no available data are skipped.
"""

import csv
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

ANALYSIS_DIR = os.path.join(PROJECT_ROOT, "analysis")
PROCESSED_DIR = os.path.join(ANALYSIS_DIR, "experiments", "processed_data")
PLOT_DIR = os.path.join(ANALYSIS_DIR, "plots")

# Dark, research-paper style
plt.rcParams.update({
    "font.size": 11,
    "font.family": "DejaVu Sans",
    "axes.titlesize": 13,
    "axes.labelsize": 11,
    "xtick.labelsize": 10,
    "ytick.labelsize": 10,
    "legend.fontsize": 10,
    "figure.dpi": 100,
    "savefig.dpi": 300,
    "axes.grid": True,
    "grid.alpha": 0.25,
    "grid.linestyle": "--",
    "axes.spines.top": False,
    "axes.spines.right": False,
    "figure.facecolor": "#1e1e1e",
    "axes.facecolor": "#2a2a2a",
    "savefig.facecolor": "#1e1e1e",
    "text.color": "#e0e0e0",
    "axes.labelcolor": "#e0e0e0",
    "xtick.color": "#e0e0e0",
    "ytick.color": "#e0e0e0",
})

ALGORITHM_COLORS = {
    "VECTOR_HEED": "#00cc96",
    "VECTOR_BatteryAware": "#00cc96",
    "VECTOR_Full": "#00cc96",
    "LEACH": "#ffa15a",
    "RANDOM_DIRECT": "#ef553b",
    "debruijn": "#00cc96",
    "ring": "#ffa15a",
    "chordal_ring": "#636efa",
    "random": "#ef553b",
    "TurboBlom": "#ab63fa",
    "PairwisePreSharedKeys": "#ffa15a",
    "MaxConsensus_Unaware": "#ffa15a",
    "Random": "#ef553b",
    "No_Energy_Awareness": "#ffa15a",
    "No_Clustering": "#ef553b",
    "No_Structured_Topology": "#636efa",
    "No_TurboBlom": "#ab63fa",
}

MARKERS = ["o", "s", "^", "D", "v", "P", "*", "X"]


def load_agg(experiment: str):
    path = os.path.join(PROCESSED_DIR, experiment, "aggregated.csv")
    if not os.path.exists(path):
        return []
    return list(csv.DictReader(open(path)))


def col(rows, algorithm, metric, size=None):
    """Return (xs, ys, yerr) for a given algorithm/metric."""
    xs, ys, ye = [], [], []
    for r in rows:
        if r["algorithm"] != algorithm:
            continue
        if size is not None and int(r["num_nodes"]) != size:
            continue
        mkey = f"{metric}_mean"
        skey = f"{metric}_std"
        if mkey not in r or r[mkey] == "":
            continue
        try:
            yval = float(r[mkey])
        except (ValueError, TypeError):
            continue
        if yval == float("inf") or yval == float("-inf") or yval != yval:  # inf or nan
            continue
        xs.append(int(r["num_nodes"]))
        ys.append(yval)
        ye.append(float(r[skey]) if r.get(skey) not in (None, "") else 0.0)
    by_x = {}
    for x, y, e in zip(xs, ys, ye):
        by_x.setdefault(x, []).append((y, e))
    xs2 = sorted(by_x)
    ys2 = [np.mean([v[0] for v in by_x[x]]) for x in xs2]
    ye2 = [np.mean([v[1] for v in by_x[x]]) for x in xs2]
    return xs2, ys2, ye2


def save(fig, name):
    os.makedirs(PLOT_DIR, exist_ok=True)
    base = os.path.join(PLOT_DIR, name)
    fig.savefig(base + ".png", dpi=300, bbox_inches="tight", facecolor="#1e1e1e")
    fig.savefig(base + ".pdf", bbox_inches="tight", facecolor="#1e1e1e")
    plt.close(fig)


def line_plot(rows, title, xlabel, ylabel, name, series, log_y=False):
    fig, ax = plt.subplots(figsize=(7.2, 4.4))
    plotted = False
    for i, (algo, label, metric) in enumerate(series):
        xs, ys, ye = col(rows, algo, metric)
        if not xs:
            continue
        ax.errorbar(xs, ys, yerr=ye, label=label, color=ALGORITHM_COLORS.get(algo),
                    marker=MARKERS[i % len(MARKERS)], capsize=3, linewidth=2,
                    markersize=6, markeredgecolor="white", markeredgewidth=0.6)
        plotted = True
    if not plotted:
        plt.close(fig)
        return
    ax.set_title(title, color="#e0e0e0", pad=12)
    ax.set_xlabel(xlabel, color="#e0e0e0")
    ax.set_ylabel(ylabel, color="#e0e0e0")
    if log_y:
        ax.set_yscale("log")
    ax.legend(frameon=True, facecolor="#2a2a2a", edgecolor="#555556", labelcolor="#e0e0e0")
    save(fig, name)


def bar_plot(rows, title, xlabel, ylabel, name, series, log_y=False):
    fig, ax = plt.subplots(figsize=(7.2, 4.4))
    labels, xs_pos, vals, errs, colors = [], [], [], [], []
    for i, (algo, label, metric) in enumerate(series):
        xs, ys, ye = col(rows, algo, metric)
        if not ys:
            continue
        labels.append(label)
        xs_pos.append(len(xs_pos))
        vals.append(ys[0])
        errs.append(ye[0] if ye else 0.0)
        colors.append(ALGORITHM_COLORS.get(algo))
    if not labels:
        plt.close(fig)
        return
    ax.bar(xs_pos, vals, yerr=errs, width=0.6, capsize=3,
           color=colors, edgecolor="white", linewidth=0.6)
    ax.set_xticks(xs_pos)
    ax.set_xticklabels(labels, rotation=12, ha="right", color="#e0e0e0")
    ax.set_title(title, color="#e0e0e0", pad=12)
    ax.set_xlabel(xlabel, color="#e0e0e0")
    ax.set_ylabel(ylabel, color="#e0e0e0")
    if log_y:
        ax.set_yscale("log")
    save(fig, name)


def failure_curve(title, name):
    raw_path = os.path.normpath(
        os.path.join(PROCESSED_DIR, os.pardir, "raw_data", "resilience", "raw.csv")
    )
    fig, ax = plt.subplots(figsize=(7.2, 4.4))
    algos = {}
    if os.path.exists(raw_path):
        for r in csv.DictReader(open(raw_path)):
            frac = r.get("failure_fraction")
            if frac is None or frac == "":
                continue
            frac = float(frac)
            algo = r["algorithm"]
            algos.setdefault(algo, {})
            y = r.get("pdr")
            if y is None or y == "":
                continue
            algos[algo].setdefault(frac, []).append(float(y))
    plotted = False
    for i, (algo, d) in enumerate(sorted(algos.items())):
        xs = sorted(d)
        ys = [np.mean(d[x]) for x in xs]
        ax.plot(xs, ys, marker=MARKERS[i % len(MARKERS)], linewidth=2,
                markersize=6, label=algo, color=ALGORITHM_COLORS.get(algo),
                markeredgecolor="white")
        plotted = True
    if not plotted:
        plt.close(fig)
        return
    ax.set_title(title, color="#e0e0e0", pad=12)
    ax.set_xlabel("Node / link failure fraction", color="#e0e0e0")
    ax.set_ylabel("Packet Delivery Ratio (%)", color="#e0e0e0")
    ax.set_ylim(0, 105)
    ax.legend(frameon=True, facecolor="#2a2a2a", edgecolor="#555556", labelcolor="#e0e0e0")
    save(fig, name)


def main() -> None:
    os.makedirs(PLOT_DIR, exist_ok=True)

    # ---- Graph 1: Average residual energy vs network size ----
    rows = load_agg("clustering")
    line_plot(
        rows,
        "Average Residual Energy vs Network Size",
        "Network Size (nodes)", "Residual Energy (J)",
        "01_average_residual_energy",
        [("VECTOR_HEED", "VECTOR (HEED)", "avg_residual_energy"),
         ("LEACH", "LEACH", "avg_residual_energy"),
         ("RANDOM_DIRECT", "Random / Direct", "avg_residual_energy")],
    )

    # ---- Graph 2: Energy fairness (Jain's index) vs network size ----
    line_plot(
        rows,
        "Energy Fairness (Jain's Index) vs Network Size",
        "Network Size (nodes)", "Jain's Fairness Index",
        "02_energy_fairness",
        [("VECTOR_HEED", "VECTOR (HEED)", "jains_fairness"),
         ("LEACH", "LEACH", "jains_fairness"),
         ("RANDOM_DIRECT", "Random / Direct", "jains_fairness")],
    )

    # ---- Graph 3: Packet latency vs network size (topology comparison) ----
    rrows = load_agg("routing")
    line_plot(
        rrows,
        "Average End-to-End Packet Latency vs Network Size",
        "Network Size (nodes)", "Latency (s)",
        "03_packet_latency",
        [("debruijn", "VECTOR (De Bruijn)", "avg_latency"),
         ("chordal_ring", "Chordal Ring", "avg_latency"),
         ("ring", "Ring", "avg_latency"),
         ("random", "Random Geometric", "avg_latency")],
    )

    # ---- Graph 4: PDR under failures ----
    failure_curve(
        "Packet Delivery Ratio Under Node/Link Failures",
        "04_packet_delivery_under_failures",
    )

    # ---- Graph 5: Energy per delivered packet vs network size ----
    line_plot(
        rows,
        "Energy Consumed per Successfully Delivered Packet vs Network Size",
        "Network Size (nodes)", "Energy per Packet (J)",
        "05_energy_per_delivered_packet",
        [("VECTOR_HEED", "VECTOR (HEED)", "energy_per_delivered_packet"),
         ("LEACH", "LEACH", "energy_per_delivered_packet"),
         ("RANDOM_DIRECT", "Random / Direct", "energy_per_delivered_packet")],
        log_y=True,
    )

    # Additional: network lifetime (LND) vs network size
    line_plot(
        rows,
        "Network Lifetime (Last Node Death) vs Network Size",
        "Network Size (nodes)", "LND (s)",
        "06_network_lifetime",
        [("VECTOR_HEED", "VECTOR (HEED)", "lnd"),
         ("LEACH", "LEACH", "lnd"),
         ("RANDOM_DIRECT", "Random / Direct", "lnd")],
    )

    # Additional: throughput vs network size
    line_plot(
        rrows,
        "Throughput vs Network Size",
        "Network Size (nodes)", "Throughput (bits/s)",
        "07_throughput_vs_network_size",
        [("debruijn", "VECTOR (De Bruijn)", "throughput"),
         ("ring", "Ring", "throughput"),
         ("random", "Random Geometric", "throughput")],
    )

    # Additional: control overhead / transmissions per packet
    line_plot(
        rrows,
        "Physical Transmissions per Delivered Packet vs Network Size",
        "Network Size (nodes)", "Transmissions / Packet",
        "08_control_overhead",
        [("debruijn", "VECTOR (De Bruijn)", "transmissions_per_packet"),
         ("ring", "Ring", "transmissions_per_packet"),
         ("random", "Random Geometric", "transmissions_per_packet")],
    )

    # Additional: ablation - energy consumption
    arows = load_agg("ablation")
    bar_plot(
        arows,
        "Ablation: Energy Consumption by Component Removal",
        "VECTOR Variant", "Energy Consumed (J)",
        "09_ablation_energy",
        [("VECTOR_Full", "VECTOR Full", "energy_consumption"),
         ("No_Energy_Awareness", "No Energy Awareness", "energy_consumption"),
         ("No_Clustering", "No Clustering", "energy_consumption"),
         ("No_Structured_Topology", "No Structured Topology", "energy_consumption"),
         ("No_TurboBlom", "No TurboBlom", "energy_consumption")],
    )

    # Additional: ablation - recovery time
    bar_plot(
        arows,
        "Ablation: Recovery Time by Component Removal",
        "VECTOR Variant", "Recovery Time (s)",
        "10_ablation_recovery",
        [("VECTOR_Full", "VECTOR Full", "recovery_time"),
         ("No_Energy_Awareness", "No Energy Awareness", "recovery_time"),
         ("No_Clustering", "No Clustering", "recovery_time"),
         ("No_Structured_Topology", "No Structured Topology", "recovery_time"),
         ("No_TurboBlom", "No TurboBlom", "recovery_time")],
    )

    # Additional: security overhead (bar)
    srows = load_agg("security")
    bar_plot(
        srows,
        "Security: Pairwise Key Derivation Time",
        "Key Scheme", "Derivation Time (ms)",
        "11_security_derivation_time",
        [("TurboBlom", "TurboBlom", "pairwise_key_derivation_time_ms"),
         ("PairwisePreSharedKeys", "Pairwise Pre-Shared Keys", "pairwise_key_derivation_time_ms")],
    )

    bar_plot(
        srows,
        "Security: Memory Overhead per Node",
        "Key Scheme", "Memory (bytes)",
        "12_security_memory",
        [("TurboBlom", "TurboBlom", "memory_overhead_bytes"),
         ("PairwisePreSharedKeys", "Pairwise Pre-Shared Keys", "memory_overhead_bytes")],
    )

    # Additional: election convergence
    erows = load_agg("election")
    bar_plot(
        erows,
        "Leader Election Convergence Time",
        "Election Scheme", "Convergence Time (ms)",
        "13_election_convergence",
        [("VECTOR_BatteryAware", "VECTOR Battery-Aware", "election_convergence_time_ms"),
         ("MaxConsensus_Unaware", "Max-Consensus (Unaware)", "election_convergence_time_ms"),
         ("Random", "Random Selection", "election_convergence_time_ms")],
    )

    bar_plot(
        erows,
        "Elected Leader Residual Energy",
        "Election Scheme", "Residual Energy (J)",
        "14_election_leader_energy",
        [("VECTOR_BatteryAware", "VECTOR Battery-Aware", "leader_residual_energy"),
         ("MaxConsensus_Unaware", "Max-Consensus (Unaware)", "leader_residual_energy"),
         ("Random", "Random Selection", "leader_residual_energy")],
    )

    print(f"[PLOTS] Figures exported to {PLOT_DIR}")


if __name__ == "__main__":
    import csv
    main()
