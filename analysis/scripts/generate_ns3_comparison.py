#!/usr/bin/env python3
"""
Parse ns-3 simulation results and generate comparative plots across all topologies.

Reads ns3_all_topologies.json (multi-line JSON objects) and generates:
- PDR comparison
- Latency comparison
- Energy per packet comparison
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
RESULTS_FILE = os.path.join(PROJECT_ROOT, "analysis", "experiments", "ns3_all_topologies.json")


def parse_results(json_path):
    """Parse multi-line JSON objects from file."""
    results = []
    current = ""
    brace_count = 0
    in_string = False
    escape = False

    with open(json_path, "r") as f:
        for line in f:
            for ch in line:
                current += ch
                if in_string:
                    if ch == "\\":
                        escape = not escape
                    elif ch == '"' and not escape:
                        in_string = False
                    elif ch == "\\" and not escape:
                        escape = True
                elif not in_string:
                    if ch == '"':
                        in_string = True
                    elif ch == "{":
                        brace_count += 1
                    elif ch == "}":
                        brace_count -= 1
                        if brace_count == 0 and current.strip():
                            try:
                                results.append(json.loads(current.strip()))
                            except json.JSONDecodeError:
                                pass
                        current = ""

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
                    "latency": np.mean([r["avgLatency"] for r in matching]),
                    "energy": np.mean([r["avgEnergy"] for r in matching]),
                }

    # Create plots
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))

    colors = {"debruijn": "#58a6ff", "ring": "#ff7b72",
              "chordal_ring": "#d29922", "random": "#3fb950"}

    metrics = [("pdr", "PDR (Packet Delivery Ratio)", 0, 1.05),
               ("latency", "Avg Latency (s)", 0, None),
               ("energy", "Energy per Packet (J)", 0, None)]

    for idx, (metric, label, ymin, ymax) in enumerate(metrics):
        ax = axes[idx]
        for topo in topologies:
            x_vals = []
            y_vals = []
            for size in network_sizes:
                if size in topo_data.get(topo, {}):
                    x_vals.append(size)
                    y_vals.append(topo_data[topo][size][metric])
            if x_vals:
                ax.plot(x_vals, y_vals, "o-", label=topo.capitalize(),
                        linewidth=2.5, markersize=8,
                        color=colors.get(topo, "#c9d1d9"))

        ax.set_xlabel("Network Size (nodes)", fontsize=11)
        ax.set_ylabel(label, fontsize=11)
        ax.set_title(label.title(), fontsize=13, fontweight="bold")
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.3)
        if ymin is not None:
            ax.set_ylim(ymin, ymax)

    plt.suptitle("Network Performance by Topology", fontsize=14, fontweight="bold")
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "ns3_topology_comparison.png"), dpi=300)
    plt.close()
    print(f"Saved {os.path.join(output_dir, 'ns3_vs_python_comparison.png')}")


def main():
    results = parse_results(RESULTS_FILE)
    if not results:
        print("No results found!")
        return

    print(f"Total records: {len(results)}")
    print(f"Network sizes: {sorted(set(r['config']['numNodes'] for r in results))}")
    print(f"Topologies: {sorted(set(r['config'].get('topology', 'debruijn') for r in results))}")

    plot_comparison(results, PLOTS_DIR)


if __name__ == "__main__":
    main()