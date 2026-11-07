#!/usr/bin/env python3
"""
Parse ns-3 topology sweep results and generate comparative plots.
"""

import json
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR))
PLOTS_DIR = os.path.join(PROJECT_ROOT, "analysis", "plots")
RESULTS_FILE = os.path.join(PROJECT_ROOT, "analysis", "experiments", "ns3_topology_sweep.json")

os.makedirs(PLOTS_DIR, exist_ok=True)


def parse_results(json_path):
    """Parse multi-line JSON objects from file."""
    results = []
    with open(json_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    results.append(json.loads(line))
                except json.JSONDecodeError as e:
                    print(f"Failed to parse line: {e}")
    return results


def plot_comparison(results, output_dir):
    """Generate comparative plots for all topologies."""
    network_sizes = sorted(set(r["config"]["numNodes"] for r in results))
    topologies = sorted(set(r["config"].get("topology", "debruijn") for r in results))

    print(f"Network sizes: {network_sizes}")
    print(f"Topologies: {topologies}")
    print(f"Total results: {len(results)}")

    # Organize data by topology
    topo_data = {}
    for topo in topologies:
        topo_data[topo] = {}
        for size in network_sizes:
            matching = [r for r in results
                        if r["config"]["numNodes"] == size
                        and r["config"].get("topology", "debruijn") == topo]
            if matching:
                topo_data[topo][size] = {
                    "pdr": np.mean([r["pdr"] for r in matching]),
                    "pdr_std": np.std([r["pdr"] for r in matching]),
                    "latency": np.mean([r["avgLatency"] for r in matching]),
                    "latency_std": np.std([r["avgLatency"] for r in matching]),
                    "energy": np.mean([r["avgEnergy"] for r in matching]),
                    "energy_std": np.std([r["avgEnergy"] for r in matching]),
                    "hops": np.mean([r.get("hopCount", r.get("avgHops", 0)) for r in matching]),
                    "hops_std": np.std([r.get("hopCount", r.get("avgHops", 0)) for r in matching]),
                    "route_found": np.mean([1.0 if r.get("routeFound", True) else 0.0 for r in matching]),
                }

    # Print summary table
    print("\n=== Summary Table ===")
    print(f"{'Size':>6} | {'Topology':>12} | {'PDR':>6} | {'Latency':>10} | {'Energy':>10} | {'Hops':>5}")
    print("-" * 65)
    for size in network_sizes:
        for topo in topologies:
            if size in topo_data.get(topo, {}):
                d = topo_data[topo][size]
                print(f"{size:>6} | {topo:>12} | {d['pdr']:.3f} | {d['latency']:.6f} | {d['energy']:.6f} | {d['hops']:.1f}")

    colors = {"debruijn": "#58a6ff", "ring": "#ff7b72",
              "chordal_ring": "#d29922", "random": "#3fb950"}

    # Create 1x3 panel plots (latency, energy, hops) - NO PDR
    fig, axes = plt.subplots(1, 3, figsize=(18, 5))

    metrics = [
        ("latency", "Avg Latency (s)", "Latency (s)", True),
        ("energy", "Energy per Packet (J)", "Energy (J)", True),
        ("hops", "Hop Count", "Hop Count", True),
    ]

    for idx, (metric, label, ylabel, log_y) in enumerate(metrics):
        ax = axes[idx]

        for topo in topologies:
            x_vals = []
            y_vals = []
            y_errs = []
            for size in network_sizes:
                if size in topo_data.get(topo, {}):
                    x_vals.append(size)
                    y_vals.append(topo_data[topo][size][metric])
                    y_errs.append(topo_data[topo][size][f"{metric}_std"])

            if x_vals:
                ax.errorbar(x_vals, y_vals, yerr=y_errs, fmt='o-', label=topo.replace('_', ' ').title(),
                           linewidth=2.5, markersize=8, capsize=4,
                           color=colors.get(topo, "#c9d1d9"), alpha=0.9)

        ax.set_xlabel("Network Size (nodes)", fontsize=12)
        ax.set_ylabel(ylabel, fontsize=12)
        ax.set_title(label, fontsize=14, fontweight="bold")
        ax.legend(fontsize=10, loc='upper left')
        ax.grid(True, alpha=0.3, which='both')
        ax.set_xscale('log')
        ax.set_xticks([5, 10, 20, 50, 100, 200, 500])
        ax.get_xaxis().set_major_formatter(matplotlib.ticker.ScalarFormatter())
        
        if log_y:
            ax.set_yscale('log')
            # Set y-ticks nicely for log scale
            ax.set_yticks([0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1, 2, 5, 10, 20, 50, 100])
            ax.get_yaxis().set_major_formatter(matplotlib.ticker.ScalarFormatter())
            ax.tick_params(axis='y', labelsize=10)

    plt.suptitle("ns-3 VECTOR Topology Comparison (All-Pairs Routing, 10 Trials)", fontsize=15, fontweight="bold", y=1.02)
    plt.tight_layout()
    png_path = os.path.join(output_dir, "ns3_topology_comparison.png")
    pdf_path = os.path.join(output_dir, "ns3_topology_comparison.pdf")
    plt.savefig(png_path, dpi=300, bbox_inches='tight')
    plt.savefig(pdf_path, bbox_inches='tight')
    plt.close()
    print(f"\nSaved {png_path}")
    print(f"Saved {pdf_path}")


def main():
    results = parse_results(RESULTS_FILE)
    if not results:
        print("No results found!")
        return

    print(f"Total records: {len(results)}")
    plot_comparison(results, PLOTS_DIR)


if __name__ == "__main__":
    main()