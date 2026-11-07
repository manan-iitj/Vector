#!/usr/bin/env python3
"""
Comparative Analysis: Python Discrete-Event Simulator vs ns-3 Packet-Level Simulator
====================================================================================

This script runs both the Python discrete-event simulator and the ns-3 packet-level
simulator at multiple network sizes and topologies, then generates comparative plots for:

- PDR (Packet Delivery Ratio)
- Average Latency
- Energy per Delivered Packet

Usage:
    python3 generate_comparative_analysis.py --nodes 30,50,100,200,500 --trials 4
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

# Add scripts dir to path for sim_engine
sys.path.insert(0, SCRIPT_DIR)
from sim_engine import Simulator, SimConfig, run_routing_experiment

# Ensure output directories exist
os.makedirs(PLOTS_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)

# Default test configuration
NETWORK_SIZES = [30, 50, 100, 200, 500]
TRIALS = 4
SEED = 42

PYTHON_TOPOLOGIES = ["debruijn", "ring", "chordal_ring", "random"]
NS3_TOPOLOGY = "debruijn"


def run_python_simulation(num_nodes, seed=42, topology="debruijn", wireless_range=200.0):
    """Run Python discrete-event simulation and return metrics."""
    cfg = SimConfig(
        num_nodes=num_nodes,
        seed=seed,
        area_width=1000.0,
        area_height=1000.0,
        wireless_range=wireless_range,
        initial_energy=100.0,
        packet_size_bits=1000,
        topology=topology,
    )
    sim = Simulator(cfg, seed=seed)
    sim.setup_network()

    results = run_routing_experiment(cfg, seeds=[seed])

    topo_results = [r for r in results if r.topology == topology]
    if not topo_results:
        return None

    total_pdr = 0.0
    total_latency = 0.0
    total_energy = 0.0
    total_hops = 0.0
    count = 0

    for r in topo_results:
        m = r.metrics
        total_pdr += m.get("pdr", 0)
        total_latency += m.get("avg_latency", 0)
        total_energy += m.get("energy_per_delivered_packet", 0)
        total_hops += m.get("avg_hops", 0)
        count += 1

    if count == 0:
        return None

    return {
        "pdr": total_pdr / count,
        "avg_latency": total_latency / count,
        "avg_energy": total_energy / count,
        "avg_hops": total_hops / count,
    }


def run_ns3_simulation(num_nodes, seed=42, topology="debruijn", wireless_range=200.0):
    """Run ns-3 packet-level simulation and return metrics."""
    ns3_bin = os.path.join(
        PROJECT_ROOT,
        "build",
        "src",
        "vector",
        "vector_ns3_sim",
    )

    if not os.path.exists(ns3_bin):
        print(f"  WARNING: ns-3 binary not found at {ns3_bin}")
        return None

    cmd = [
        ns3_bin,
        f"--numNodes={num_nodes}",
        f"--seed={seed}",
        f"--areaWidth=1000",
        f"--areaHeight=1000",
        f"--wirelessRange={wireless_range}",
        f"--topology={topology}",
    ]

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=120
        )
        if result.returncode != 0:
            print(f"  ns-3 failed for n={num_nodes}: {result.stderr}")
            return None

        output = json.loads(result.stdout)
        return {
            "pdr": output.get("pdr", 0.0),
            "avg_latency": output.get("avgLatency", 0.0),
            "avg_energy": output.get("avgEnergy", 0.0),
            "num_ch": output.get("chCount", 0),
            "auth_success": output.get("authSuccessRate", 0.0),
        }
    except (json.JSONDecodeError, subprocess.TimeoutExpired) as e:
        print(f"  ns-3 error for n={num_nodes}: {e}")
        return None


def run_comparative_analysis(network_sizes, trials=4, seed=42):
    """Run both Python and ns-3 simulators at multiple network sizes and topologies,
    then generate comparative plots."""

    results = {
        "network_sizes": network_sizes,
        "trials": trials,
        "seed": seed,
        "topologies": PYTHON_TOPOLOGIES,
        "python": {},
        "ns3": [],
    }

    for topo in PYTHON_TOPOLOGIES:
        results["python"][topo] = []

    for n in network_sizes:
        print(f"\n{'='*70}")
        print(f"Running simulations for {n} nodes")
        print(f"{'='*70}")

        for topo in PYTHON_TOPOLOGIES:
            python_results = []
            for t in range(trials):
                trial_seed = seed + t
                r = run_python_simulation(n, seed=trial_seed, topology=topo)
                if r:
                    python_results.append(r)
                    print(f"  Python {topo} trial {t+1}: PDR={r['pdr']:.3f}, "
                          f"Latency={r['avg_latency']:.4f}s, "
                          f"Energy={r['avg_energy']:.6f}J")

            if python_results:
                py_avg = {
                    "pdr": sum(r["pdr"] for r in python_results) / len(python_results),
                    "avg_latency": sum(r["avg_latency"] for r in python_results) / len(python_results),
                    "avg_energy": sum(r["avg_energy"] for r in python_results) / len(python_results),
                    "avg_hops": sum(r["avg_hops"] for r in python_results) / len(python_results),
                }
            else:
                py_avg = {"pdr": 0, "avg_latency": 0, "avg_energy": 0, "avg_hops": 0}

            results["python"][topo].append(py_avg)
            print(f"    Python {topo} avg: PDR={py_avg['pdr']:.3f}, "
                  f"Latency={py_avg['avg_latency']:.4f}s, "
                  f"Energy={py_avg['avg_energy']:.6f}J")

        print(f"\n  Running ns-3 SEARCH simulation for {n} nodes...")
        ns3_results = []
        for t in range(trials):
            trial_seed = seed + t
            r = run_ns3_simulation(n, seed=trial_seed, topology=NS3_TOPOLOGY)
            if r:
                ns3_results.append(r)
                print(f"  ns-3 trial {t+1}: PDR={r['pdr']:.3f}, "
                      f"Latency={r['avg_latency']:.4f}s, "
                      f"Energy={r['avg_energy']:.6f}J, "
                      f"CHs={r['num_ch']}, Auth={r['auth_success']}%")

        if ns3_results:
            ns3_avg = {
                "pdr": sum(r["pdr"] for r in ns3_results) / len(ns3_results),
                "avg_latency": sum(r["avg_latency"] for r in ns3_results) / len(ns3_results),
                "avg_energy": sum(r["avg_energy"] for r in ns3_results) / len(ns3_results),
                "num_ch": sum(r["num_ch"] for r in ns3_results) / len(ns3_results),
                "auth_success": sum(r["auth_success"] for r in ns3_results) / len(ns3_results),
            }
        else:
            ns3_avg = {"pdr": 0, "avg_latency": 0, "avg_energy": 0, "num_ch": 0, "auth_success": 0}

        results["ns3"].append(ns3_avg)
        print(f"\n  SUMMARY for {n} nodes:")
        print(f"    Python De Bruijn: PDR={results['python']['debruijn'][-1]['pdr']:.3f}, "
              f"Latency={results['python']['debruijn'][-1]['avg_latency']:.4f}s, "
              f"Energy={results['python']['debruijn'][-1]['avg_energy']:.6f}J")
        print(f"    Python Ring:      PDR={results['python']['ring'][-1]['pdr']:.3f}, "
              f"Latency={results['python']['ring'][-1]['avg_latency']:.4f}s, "
              f"Energy={results['python']['ring'][-1]['avg_energy']:.6f}J")
        print(f"    Python Chordal:   PDR={results['python']['chordal_ring'][-1]['pdr']:.3f}, "
              f"Latency={results['python']['chordal_ring'][-1]['avg_latency']:.4f}s, "
              f"Energy={results['python']['chordal_ring'][-1]['avg_energy']:.6f}J")
        print(f"    Python Random:    PDR={results['python']['random'][-1]['pdr']:.3f}, "
              f"Latency={results['python']['random'][-1]['avg_latency']:.4f}s, "
              f"Energy={results['python']['random'][-1]['avg_energy']:.6f}J")
        print(f"    ns-3 De Bruijn:   PDR={ns3_avg['pdr']:.3f}, "
              f"Latency={ns3_avg['avg_latency']:.4f}s, "
              f"Energy={ns3_avg['avg_energy']:.6f}J, "
              f"CHs={ns3_avg['num_ch']:.1f}, Auth={ns3_avg['auth_success']:.1f}%")

    return results


def plot_comparison(results, output_dir):
    """Generate comparative plots."""

    network_sizes = results["network_sizes"]
    python = results["python"]
    ns3 = results["ns3"]

    python_pdr = {topo: [r["pdr"] for r in python[topo]] for topo in PYTHON_TOPOLOGIES}
    python_latency = {topo: [r["avg_latency"] for r in python[topo]] for topo in PYTHON_TOPOLOGIES}
    python_energy = {topo: [r["avg_energy"] for r in python[topo]] for topo in PYTHON_TOPOLOGIES}

    ns3_pdr = [r["pdr"] for r in ns3]
    ns3_latency = [r["avg_latency"] for r in ns3]
    ns3_energy = [r["avg_energy"] for r in ns3]

    fig, axes = plt.subplots(1, 3, figsize=(16, 5))

    # PDR comparison
    ax = axes[0]
    colors = ["#58a6ff", "#ff7b72", "#d29922", "#3fb950"]
    for i, topo in enumerate(PYTHON_TOPOLOGIES):
        ax.plot(network_sizes, python_pdr[topo], "o-", label=f"Python {topo}",
                linewidth=2.5, markersize=8, color=colors[i])
    ax.plot(network_sizes, ns3_pdr, "s-", label="ns-3 De Bruijn",
            linewidth=2.5, markersize=10, color="#f0c808")
    ax.set_xlabel("Network Size (nodes)", fontsize=11)
    ax.set_ylabel("PDR", fontsize=11)
    ax.set_title("Packet Delivery Ratio: ns-3 vs Python Simulator",
                 fontsize=13, fontweight="bold")
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3)
    ax.set_ylim(0, 1.05)

    # Latency comparison
    ax = axes[1]
    for i, topo in enumerate(PYTHON_TOPOLOGIES):
        ax.plot(network_sizes, python_latency[topo], "o-", label=f"Python {topo}",
                linewidth=2.5, markersize=8, color=colors[i])
    ax.plot(network_sizes, ns3_latency, "s-", label="ns-3 De Bruijn",
            linewidth=2.5, markersize=10, color="#f0c808")
    ax.set_xlabel("Network Size (nodes)", fontsize=11)
    ax.set_ylabel("Average Latency (seconds)", fontsize=11)
    ax.set_title("End-to-End Latency: ns-3 vs Python Simulator",
                 fontsize=13, fontweight="bold")
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3)

    # Energy comparison
    ax = axes[2]
    for i, topo in enumerate(PYTHON_TOPOLOGIES):
        ax.plot(network_sizes, python_energy[topo], "o-", label=f"Python {topo}",
                linewidth=2.5, markersize=8, color=colors[i])
    ax.plot(network_sizes, ns3_energy, "s-", label="ns-3 De Bruijn",
            linewidth=2.5, markersize=10, color="#f0c808")
    ax.set_xlabel("Network Size (nodes)", fontsize=11)
    ax.set_ylabel("Energy per Delivered Packet (J)", fontsize=11)
    ax.set_title("Energy per Delivered Packet: ns-3 vs Python Simulator",
                 fontsize=13, fontweight="bold")
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "ns3_vs_python_comparison.png"), dpi=300)
    plt.close()
    print(f"\nComparison plots saved to {output_dir}/ns3_vs_python_comparison.png")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Comparative analysis: Python vs ns-3")
    parser.add_argument("--nodes", type=str, default="30,50,100,200,500",
                        help="Comma-separated list of network sizes")
    parser.add_argument("--trials", type=int, default=4,
                        help="Number of trials per network size")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    args = parser.parse_args()

    network_sizes = [int(x) for x in args.nodes.split(",")]

    print("=" * 70)
    print("VECTOR Comparative Analysis: Python DE Simulator vs ns-3")
    print("=" * 70)

    results = run_comparative_analysis(network_sizes, trials=args.trials, seed=args.seed)

    plot_comparison(results, PLOTS_DIR)

    results_file = os.path.join(DATA_DIR, "ns3_vs_python_comparison.json")
    with open(results_file, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to {results_file}")
    print(f"Plots saved to {PLOTS_DIR}/")


if __name__ == "__main__":
    main()