#!/usr/bin/env python3
"""
Generate ns-3 De Bruijn vs Python DE De Bruijn comparison plot.
"""

import json
import os
import csv
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
PLOTS_DIR = PROJECT_ROOT / "analysis" / "plots"
NS3_RESULTS_FILE = PROJECT_ROOT / "analysis" / "experiments" / "ns3_topology_sweep.json"
PY_ROUTING_FILE = PROJECT_ROOT / "analysis" / "experiments" / "processed_data" / "routing" / "aggregated.csv"

os.makedirs(PLOTS_DIR, exist_ok=True)


def parse_ns3_results(json_path):
    """Parse multi-line JSON objects from ns-3 sweep."""
    results = []
    with open(json_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    results.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return results


def parse_py_results(csv_path):
    """Parse Python DE routing aggregated CSV."""
    data = {}
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            topo = row['topology']
            size = int(row['num_nodes'])
            if topo not in data:
                data[topo] = {}
            data[topo][size] = {
                'pdr': float(row['pdr_mean']),
                'pdr_std': float(row['pdr_std']),
                'latency': float(row['avg_latency_mean']),
                'latency_std': float(row['avg_latency_std']),
                'hops': float(row['avg_hops_mean']),
                'hops_std': float(row['avg_hops_std']),
                'energy': float(row['energy_per_delivered_packet_mean']),
                'energy_std': float(row['energy_per_delivered_packet_std']),
            }
    return data


def plot_debruijn_comparison(ns3_results, py_results, output_dir):
    """Generate ns-3 De Bruijn vs Python DE De Bruijn comparison."""
    # Filter ns3 results for debruijn only
    ns3_debruijn = [r for r in ns3_results if r["config"].get("topology", "debruijn") == "debruijn"]
    
    ns3_sizes = sorted(set(r["config"]["numNodes"] for r in ns3_debruijn))
    py_sizes = sorted(py_results.get("debruijn", {}).keys())
    
    print(f"ns-3 sizes: {ns3_sizes}")
    print(f"Python sizes: {py_sizes}")

    colors = {"ns3": "#58a6ff", "python": "#ff7b72"}

    # Organize ns3 data
    ns3_data = {}
    for size in ns3_sizes:
        matching = [r for r in ns3_debruijn if r["config"]["numNodes"] == size]
        if matching:
            ns3_data[size] = {
                'pdr': np.mean([r["pdr"] for r in matching]),
                'pdr_std': np.std([r["pdr"] for r in matching]),
                'latency': np.mean([r["avgLatency"] for r in matching]),
                'latency_std': np.std([r["avgLatency"] for r in matching]),
                'hops': np.mean([r.get("hopCount", r.get("avgHops", 0)) for r in matching]),
                'hops_std': np.std([r.get("hopCount", r.get("avgHops", 0)) for r in matching]),
                'energy': np.mean([r["avgEnergy"] for r in matching]),
                'energy_std': np.std([r["avgEnergy"] for r in matching]),
            }

    # Organize Python data
    py_data = py_results.get("debruijn", {})

    # Create 2x2 panel plots
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle("De Bruijn Topology: ns-3 Packet-Level vs Python Discrete-Event", 
                 fontsize=15, fontweight="bold", y=1.02)

    # Panel 1: PDR
    ax = axes[0, 0]
    # ns-3
    x_ns3 = [s for s in ns3_sizes if s in ns3_data]
    y_ns3 = [ns3_data[s]['pdr'] * 100 for s in x_ns3]
    e_ns3 = [ns3_data[s]['pdr_std'] * 100 for s in x_ns3]
    ax.errorbar(x_ns3, y_ns3, yerr=e_ns3, fmt='o-', label='ns-3', 
               color=colors['ns3'], linewidth=2.5, markersize=8, capsize=4, alpha=0.9)
    # Python
    x_py = [s for s in py_sizes if s in py_data]
    y_py = [py_data[s]['pdr'] for s in x_py]
    e_py = [py_data[s]['pdr_std'] for s in x_py]
    ax.errorbar(x_py, y_py, yerr=e_py, fmt='s-', label='Python DE', 
               color=colors['python'], linewidth=2.5, markersize=8, capsize=4, alpha=0.9)
    
    ax.set_xlabel("Network Size (nodes)", fontsize=12)
    ax.set_ylabel("PDR (%)", fontsize=12)
    ax.set_title("Packet Delivery Ratio", fontsize=14, fontweight="bold")
    ax.legend(fontsize=11, loc='lower left')
    ax.grid(True, alpha=0.3, which='both')
    ax.set_ylim(-5, 105)
    ax.set_xscale('log')
    ax.set_xticks([5, 10, 20, 50, 100, 200, 500])
    ax.get_xaxis().set_major_formatter(matplotlib.ticker.ScalarFormatter())

    # Panel 2: Latency
    ax = axes[0, 1]
    x_ns3 = [s for s in ns3_sizes if s in ns3_data]
    y_ns3 = [ns3_data[s]['latency'] for s in x_ns3]
    e_ns3 = [ns3_data[s]['latency_std'] for s in x_ns3]
    ax.errorbar(x_ns3, y_ns3, yerr=e_ns3, fmt='o-', label='ns-3', 
               color=colors['ns3'], linewidth=2.5, markersize=8, capsize=4, alpha=0.9)
    
    x_py = [s for s in py_sizes if s in py_data]
    y_py = [py_data[s]['latency'] for s in x_py]
    e_py = [py_data[s]['latency_std'] for s in x_py]
    ax.errorbar(x_py, y_py, yerr=e_py, fmt='s-', label='Python DE', 
               color=colors['python'], linewidth=2.5, markersize=8, capsize=4, alpha=0.9)
    
    ax.set_xlabel("Network Size (nodes)", fontsize=12)
    ax.set_ylabel("Latency (s)", fontsize=12)
    ax.set_title("Average Latency", fontsize=14, fontweight="bold")
    ax.legend(fontsize=11)
    ax.grid(True, alpha=0.3, which='both')
    ax.set_xscale('log')
    ax.set_yscale('log')
    ax.set_xticks([5, 10, 20, 50, 100, 200, 500])
    ax.get_xaxis().set_major_formatter(matplotlib.ticker.ScalarFormatter())
    ax.set_yticks([0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1.0])
    ax.get_yaxis().set_major_formatter(matplotlib.ticker.ScalarFormatter())

    # Panel 3: Hop Count
    ax = axes[1, 0]
    x_ns3 = [s for s in ns3_sizes if s in ns3_data]
    y_ns3 = [ns3_data[s]['hops'] for s in x_ns3]
    e_ns3 = [ns3_data[s]['hops_std'] for s in x_ns3]
    ax.errorbar(x_ns3, y_ns3, yerr=e_ns3, fmt='o-', label='ns-3', 
               color=colors['ns3'], linewidth=2.5, markersize=8, capsize=4, alpha=0.9)
    
    x_py = [s for s in py_sizes if s in py_data]
    y_py = [py_data[s]['hops'] for s in x_py]
    e_py = [py_data[s]['hops_std'] for s in x_py]
    ax.errorbar(x_py, y_py, yerr=e_py, fmt='s-', label='Python DE', 
               color=colors['python'], linewidth=2.5, markersize=8, capsize=4, alpha=0.9)
    
    ax.set_xlabel("Network Size (nodes)", fontsize=12)
    ax.set_ylabel("Hop Count", fontsize=12)
    ax.set_title("Average Hop Count", fontsize=14, fontweight="bold")
    ax.legend(fontsize=11)
    ax.grid(True, alpha=0.3, which='both')
    ax.set_xscale('log')
    ax.set_yscale('log')
    ax.set_xticks([5, 10, 20, 50, 100, 200, 500])
    ax.get_xaxis().set_major_formatter(matplotlib.ticker.ScalarFormatter())
    ax.set_yticks([1, 2, 5, 10, 20, 50, 100])
    ax.get_yaxis().set_major_formatter(matplotlib.ticker.ScalarFormatter())

    # Panel 4: Energy per Packet
    ax = axes[1, 1]
    x_ns3 = [s for s in ns3_sizes if s in ns3_data]
    y_ns3 = [ns3_data[s]['energy'] for s in x_ns3]
    e_ns3 = [ns3_data[s]['energy_std'] for s in x_ns3]
    ax.errorbar(x_ns3, y_ns3, yerr=e_ns3, fmt='o-', label='ns-3', 
               color=colors['ns3'], linewidth=2.5, markersize=8, capsize=4, alpha=0.9)
    
    x_py = [s for s in py_sizes if s in py_data]
    y_py = [py_data[s]['energy'] for s in x_py]
    e_py = [py_data[s]['energy_std'] for s in x_py]
    ax.errorbar(x_py, y_py, yerr=e_py, fmt='s-', label='Python DE', 
               color=colors['python'], linewidth=2.5, markersize=8, capsize=4, alpha=0.9)
    
    ax.set_xlabel("Network Size (nodes)", fontsize=12)
    ax.set_ylabel("Energy (J)", fontsize=12)
    ax.set_title("Energy per Delivered Packet", fontsize=14, fontweight="bold")
    ax.legend(fontsize=11)
    ax.grid(True, alpha=0.3, which='both')
    ax.set_xscale('log')
    ax.set_yscale('log')
    ax.set_xticks([5, 10, 20, 50, 100, 200, 500])
    ax.get_xaxis().set_major_formatter(matplotlib.ticker.ScalarFormatter())
    ax.set_yticks([0.001, 0.002, 0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1.0])
    ax.get_yaxis().set_major_formatter(matplotlib.ticker.ScalarFormatter())

    plt.tight_layout()
    png_path = output_dir / "ns3_vs_python_debruijn_comparison.png"
    pdf_path = output_dir / "ns3_vs_python_debruijn_comparison.pdf"
    plt.savefig(png_path, dpi=300, bbox_inches='tight')
    plt.savefig(pdf_path, bbox_inches='tight')
    plt.close()
    print(f"Saved {png_path}")
    print(f"Saved {pdf_path}")


def main():
    print("Loading ns-3 results...")
    ns3_results = parse_ns3_results(NS3_RESULTS_FILE)
    print(f"  {len(ns3_results)} records")

    print("Loading Python DE routing results...")
    py_results = parse_py_results(PY_ROUTING_FILE)
    for topo, sizes in py_results.items():
        print(f"  {topo}: {len(sizes)} sizes")

    print("Generating De Bruijn comparison plot...")
    plot_debruijn_comparison(ns3_results, py_results, PLOTS_DIR)
    print("Done.")


if __name__ == "__main__":
    main()