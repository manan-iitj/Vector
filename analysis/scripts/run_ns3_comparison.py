#!/usr/bin/env python3
"""
Run ns-3 simulation for all topologies and network sizes.
Generate comparison plots for SEARCH route discovery across all topologies.
"""

import os
import sys
import json
import subprocess
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR))
PLOTS_DIR = os.path.join(PROJECT_ROOT, "analysis", "plots")
DATA_DIR = os.path.join(PROJECT_ROOT, "analysis", "experiments", "processed_data")

NS3_BIN = os.path.join(PROJECT_ROOT, "build", "src", "vector", "vector_ns3_sim")

NETWORK_SIZES = [30, 50, 100, 200, 500]
TOPOLOGIES = ["debruijn", "ring", "chordal_ring", "random"]
TRIALS = 4
SEED = 42


def run_ns3_simulation(num_nodes, topology, seed):
    """Run ns-3 simulation and return metrics."""
    cmd = [
        NS3_BIN,
        f"--numNodes={num_nodes}",
        f"--seed={seed}",
        f"--areaWidth=1000",
        f"--areaHeight=1000",
        f"--wirelessRange=200",
        f"--topology={topology}",
    ]

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=60
        )
        if result.returncode != 0:
            return None

        content = result.stdout.strip()
        start = content.find("{")
        end = content.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(content[start:end])
    except (json.JSONDecodeError, subprocess.TimeoutExpired, Exception) as e:
        print(f"  ns-3 error for n={num_nodes}, topo={topology}: {e}")
        return None

    return None


def main():
    print("=" * 70)
    print("VECTOR ns-3 Comparative Analysis: All Topologies")
    print("=" * 70)

    results = {
        "network_sizes": NETWORK_SIZES,
        "topologies": TOPOLOGIES,
        "trials": TRIALS,
        "seed": SEED,
        "ns3": {topo: [] for topo in TOPOLOGIES},
    }

    for size in NETWORK_SIZES:
        print(f"\n{'='*70}")
        print(f"Running ns-3 for {size} nodes")
        print(f"{'='*70}")

        results["ns3"][size] = {}

        for topo in TOPOLOGIES:
            print(f"\n  Topology: {topo}")
            topo_results = []

            for trial in range(TRIALS):
                seed = SEED + trial
                r = run_ns3_simulation(size, topo, seed)
                if r:
                    topo_results.append(r)
                    print(f"  Trial {trial+1}: PDR={r['pdr']:.3f}, "
                          f"Latency={r['avgLatency']:.4f}s, "
                          f"Energy={r['avgEnergy']:.6f}J")

            if topo_results:
                results["ns3"][size][topo] = topo_results

                avg_pdr = sum(r["pdr"] for r in topo_results) / len(topo_results)
                avg_latency = sum(r["avgLatency"] for r in topo_results) / len(topo_results)
                avg_energy = sum(r["avgEnergy"] for r in topo_results) / len(topo_results)

                print(f"    Average: PDR={avg_pdr:.3f}, Latency={avg_latency:.4f}s, "
                      f"Energy={avg_energy:.6f}J")

    # Generate plots
    plot_comparison(results, PLOTS_DIR)

    # Save results
    results_file = os.path.join(DATA_DIR, "ns3_all_topologies.json")
    with open(results_file, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to {results_file}")
    print(f"Plots saved to {PLOTS_DIR}/")


def plot_comparison(results, output_dir):
    """Generate comparison plots."""
    network_sizes = results["network_sizes"]
    topologies = results["topologies"]

    colors = {"debruijn": "#58a6ff", "ring": "#ff7b72",
              "chordal_ring": "#d29922", "random": "#3fb950"}

    fig, axes = plt.subplots(1, 3, figsize=(16, 5))

    metrics = ["pdr", "avgLatency", "avgEnergy"]
    metric_labels = ["PDR", "Latency (s)", "Energy per Packet (J)"]

    for idx, (metric, label) in enumerate(zip(metrics, metric_labels)):
        ax = axes[idx]

        for topo in topologies:
            x_vals = []
            y_vals = []
            for size in network_sizes:
                matching = [r for r in results["ns3"].get(size, {}).get(topo, [])]
                if matching:
                    x_vals.append(size)
                    y_vals.append(np.mean([r[metric] for r in matching]))

            if x_vals:
                ax.plot(x_vals, y_vals, "o-", label=topo.capitalize(),
                        linewidth=2.5, markersize=8,
                        color=colors.get(topo, "#c9d1d9"))

        ax.set_xlabel("Network Size (nodes)", fontsize=11)
        ax.set_ylabel(label, fontsize=11)
        ax.set_title(label.title(), fontsize=13, fontweight="bold")
        ax.legend(fontsize=9)
        ax.grid(True, alpha=0.3)

        if metric == "pdr":
            ax.set_ylim(0, 1.05)

    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "ns3_all_topologies_comparison.png"),
                dpi=300)
    plt.close()
    print(f"\nSaved {os.path.join(output_dir, 'ns3_all_topologies_comparison.png')}")


if __name__ == "__main__":
    main()