#!/usr/bin/env python3
"""
Generate the definitive ns-3 vs Python DE comparative topology analysis.
Shows: ns-3 packet-level simulator (flat, limited) vs Python DE simulator (realistic topology differences).
"""

import csv
import os
import json
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


def plot_final_comparison(ns3_results, py_results, output_dir):
    """Generate the definitive 2x3 comparison plot."""
    ns3_sizes = sorted(set(r["config"]["numNodes"] for r in ns3_results))
    ns3_topo = sorted(set(r["config"].get("topology", "debruijn") for r in ns3_results))
    py_sizes_set = set()
    for t in py_results:
        py_sizes_set.update(py_results[t].keys())
    py_sizes = sorted(py_sizes_set)
    py_topo = sorted(py_results.keys())

    colors = {"debruijn": "#58a6ff", "ring": "#ff7b72",
              "chordal_ring": "#d29922", "random": "#3fb950"}
    
    # Marker/styles
    ns3_style = {'fmt': 'o--', 'ms': 6, 'lw': 2, 'alpha': 0.6, 'label_suffix': ' (ns-3)'}
    py_style = {'fmt': 's-', 'ms': 7, 'lw': 2.5, 'alpha': 0.95, 'label_suffix': ' (Python DE)'}

    fig, axes = plt.subplots(2, 3, figsize=(18, 10))
    fig.suptitle("VECTOR Topology Comparison: ns-3 Packet-Level vs Python Discrete-Event\n"
                 "ns-3 tests single source→dest (0→1); Python DE tests all-pairs traffic",
                 fontsize=13, fontweight="bold", y=1.02)

    # Organize ns3 data
    ns3_data = {}
    for topo in ns3_topo:
        ns3_data[topo] = {}
        for size in ns3_sizes:
            matching = [r for r in ns3_results
                        if r["config"]["numNodes"] == size
                        and r["config"].get("topology", "debruijn") == topo]
            if matching:
                ns3_data[topo][size] = {
                    'pdr': np.mean([r["pdr"] for r in matching]),
                    'pdr_std': np.std([r["pdr"] for r in matching]),
                    'latency': np.mean([r["avgLatency"] for r in matching]),
                    'latency_std': np.std([r["avgLatency"] for r in matching]),
                    'hops': np.mean([r.get("hopCount", r.get("avgHops", 0)) for r in matching]),
                    'hops_std': np.std([r.get("hopCount", r.get("avgHops", 0)) for r in matching]),
                    'energy': np.mean([r["avgEnergy"] for r in matching]),
                    'energy_std': np.std([r["avgEnergy"] for r in matching]),
                }

    # Panel 1: PDR
    ax = axes[0, 0]
    for topo in ns3_topo:
        x = [s for s in ns3_sizes if s in ns3_data.get(topo, {})]
        y = [ns3_data[topo][s]['pdr'] for s in x]
        e = [ns3_data[topo][s]['pdr_std'] for s in x]
        if x:
            ax.errorbar(x, y, yerr=e, fmt=ns3_style['fmt'], 
                       label=topo.replace('_', ' ').title() + ns3_style['label_suffix'],
                       color=colors[topo], markersize=ns3_style['ms'], linewidth=ns3_style['lw'],
                       alpha=ns3_style['alpha'], capsize=3)
    for topo in py_topo:
        x = [s for s in py_sizes if s in py_results.get(topo, {})]
        y = [py_results[topo][s]['pdr'] for s in x]
        e = [py_results[topo][s]['pdr_std'] for s in x]
        if x:
            ax.errorbar(x, y, yerr=e, fmt=py_style['fmt'],
                       label=topo.replace('_', ' ').title() + py_style['label_suffix'],
                       color=colors[topo], markersize=py_style['ms'], linewidth=py_style['lw'],
                       alpha=py_style['alpha'], capsize=3)
    ax.set_xlabel("Network Size (nodes)", fontsize=10)
    ax.set_ylabel("PDR (%)", fontsize=10)
    ax.set_title("Packet Delivery Ratio", fontsize=11, fontweight="bold")
    ax.legend(fontsize=7, ncol=2, loc='lower left')
    ax.grid(True, alpha=0.3)
    ax.set_ylim(-5, 105)
    ax.set_xscale('log')
    ax.set_xticks([5, 10, 20, 50, 100])
    ax.get_xaxis().set_major_formatter(matplotlib.ticker.ScalarFormatter())

    # Panel 2: Latency
    ax = axes[0, 1]
    for topo in ns3_topo:
        x = [s for s in ns3_sizes if s in ns3_data.get(topo, {})]
        y = [ns3_data[topo][s]['latency'] for s in x]
        e = [ns3_data[topo][s]['latency_std'] for s in x]
        if x:
            ax.errorbar(x, y, yerr=e, fmt=ns3_style['fmt'],
                       color=colors[topo], markersize=ns3_style['ms'], linewidth=ns3_style['lw'],
                       alpha=ns3_style['alpha'], capsize=3)
    for topo in py_topo:
        x = [s for s in py_sizes if s in py_results.get(topo, {})]
        y = [py_results[topo][s]['latency'] for s in x]
        e = [py_results[topo][s]['latency_std'] for s in x]
        if x:
            ax.errorbar(x, y, yerr=e, fmt=py_style['fmt'],
                       label=topo.replace('_', ' ').title(),
                       color=colors[topo], markersize=py_style['ms'], linewidth=py_style['lw'],
                       alpha=py_style['alpha'], capsize=3)
    ax.set_xlabel("Network Size (nodes)", fontsize=10)
    ax.set_ylabel("Latency (s)", fontsize=10)
    ax.set_title("Average Latency", fontsize=11, fontweight="bold")
    ax.grid(True, alpha=0.3)
    ax.set_xscale('log')
    ax.set_xticks([5, 10, 20, 50, 100])
    ax.get_xaxis().set_major_formatter(matplotlib.ticker.ScalarFormatter())

    # Panel 3: Hop Count
    ax = axes[0, 2]
    for topo in ns3_topo:
        x = [s for s in ns3_sizes if s in ns3_data.get(topo, {})]
        y = [ns3_data[topo][s]['hops'] for s in x]
        e = [ns3_data[topo][s]['hops_std'] for s in x]
        if x:
            ax.errorbar(x, y, yerr=e, fmt=ns3_style['fmt'],
                       color=colors[topo], markersize=ns3_style['ms'], linewidth=ns3_style['lw'],
                       alpha=ns3_style['alpha'], capsize=3)
    for topo in py_topo:
        x = [s for s in py_sizes if s in py_results.get(topo, {})]
        y = [py_results[topo][s]['hops'] for s in x]
        e = [py_results[topo][s]['hops_std'] for s in x]
        if x:
            ax.errorbar(x, y, yerr=e, fmt=py_style['fmt'],
                       color=colors[topo], markersize=py_style['ms'], linewidth=py_style['lw'],
                       alpha=py_style['alpha'], capsize=3)
    ax.set_xlabel("Network Size (nodes)", fontsize=10)
    ax.set_ylabel("Hop Count", fontsize=10)
    ax.set_title("Average Hop Count", fontsize=11, fontweight="bold")
    ax.grid(True, alpha=0.3)
    ax.set_xscale('log')
    ax.set_xticks([5, 10, 20, 50, 100])
    ax.get_xaxis().set_major_formatter(matplotlib.ticker.ScalarFormatter())

    # Panel 4: Energy per Packet
    ax = axes[1, 0]
    for topo in ns3_topo:
        x = [s for s in ns3_sizes if s in ns3_data.get(topo, {})]
        y = [ns3_data[topo][s]['energy'] for s in x]
        e = [ns3_data[topo][s]['energy_std'] for s in x]
        if x:
            ax.errorbar(x, y, yerr=e, fmt=ns3_style['fmt'],
                       color=colors[topo], markersize=ns3_style['ms'], linewidth=ns3_style['lw'],
                       alpha=ns3_style['alpha'], capsize=3)
    for topo in py_topo:
        x = [s for s in py_sizes if s in py_results.get(topo, {})]
        y = [py_results[topo][s]['energy'] for s in x]
        e = [py_results[topo][s]['energy_std'] for s in x]
        if x:
            ax.errorbar(x, y, yerr=e, fmt=py_style['fmt'],
                       color=colors[topo], markersize=py_style['ms'], linewidth=py_style['lw'],
                       alpha=py_style['alpha'], capsize=3)
    ax.set_xlabel("Network Size (nodes)", fontsize=10)
    ax.set_ylabel("Energy (J)", fontsize=10)
    ax.set_title("Energy per Delivered Packet", fontsize=11, fontweight="bold")
    ax.grid(True, alpha=0.3)
    ax.set_xscale('log')
    ax.set_xticks([5, 10, 20, 50, 100])
    ax.get_xaxis().set_major_formatter(matplotlib.ticker.ScalarFormatter())
    ax.set_yscale('log')

    # Panel 5: Throughput (Python only - ns-3 doesn't measure)
    ax = axes[1, 1]
    for topo in py_topo:
        x = [s for s in py_sizes if s in py_results.get(topo, {})]
        # throughput = delivered * bits / sim_time; bits=1000, sim_time=1000
        # Actually throughput is in the CSV
        y = [py_results[topo][s].get('throughput', 0) for s in x if 'throughput' in py_results[topo][s]]
        if not y:
            # compute from delivered * 1000 / 1000
            # We don't have delivered count in aggregated, skip
            pass
    ax.text(0.5, 0.5, "Throughput\n(Python DE only)\nNot measured in ns-3",
            ha='center', va='center', transform=ax.transAxes, fontsize=11, color='gray')
    ax.set_title("Throughput", fontsize=11, fontweight="bold")
    ax.axis('off')

    # Panel 6: Key finding summary
    ax = axes[1, 2]
    ax.axis('off')
    summary_text = (
        "KEY FINDINGS\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "ns-3 PACKET-LEVEL SIMULATOR\n"
        "• Tests ONLY source=0 → dest=1\n"
        "• BFS always finds identical 3-hop path\n"
        "• PDR=100%, Latency=15ms, Energy=3mJ\n"
        "• IDENTICAL across ALL topologies & sizes\n"
        "• Topology parameter has ZERO effect on metrics\n\n"
        "PYTHON DISCRETE-EVENT SIMULATOR\n"
        "• Tests ALL source→dest pairs (all-pairs)\n"
        "• Proper BFS over logical topology graph\n"
        "• Real topology differentiation:\n"
        "  – Chordal Ring: best (1.4–2.8 hops)\n"
        "  – De Bruijn: good (2–4 hops)\n"
        "  – Ring: worst (2.7–25 hops, O(n))\n"
        "  – Random Geometric: PDR scales with density\n"
        "• Latency scales: Ring O(n) vs De Bruijn O(log n)\n\n"
        "CONCLUSION\n"
        "ns-3 model in current form CANNOT\n"
        "differentiate topologies. Python DE\n"
        "reveals true VECTOR topology behavior."
    )
    ax.text(0.02, 0.98, summary_text, transform=ax.transAxes,
            fontsize=9, va='top', ha='left', fontfamily='monospace',
            bbox=dict(boxstyle='round,pad=0.5', facecolor='#f6f8fa', edgecolor='#c9d1d9', alpha=0.9))

    plt.tight_layout()
    png_path = output_dir / "ns3_vs_python_de_topology_comparison.png"
    pdf_path = output_dir / "ns3_vs_python_de_topology_comparison.pdf"
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

    print("Generating final comparison plot...")
    plot_final_comparison(ns3_results, py_results, PLOTS_DIR)
    print("Done.")


if __name__ == "__main__":
    main()