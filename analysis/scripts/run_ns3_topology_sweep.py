#!/usr/bin/env python3
"""
Run ns-3 simulation for all topologies and network sizes.
Comprehensive sweep: 4 topologies x 13 sizes x 10 trials = 520 runs.
"""

import os
import sys
import json
import subprocess
import numpy as np
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
NS3_BIN = PROJECT_ROOT / "build" / "src" / "vector" / "vector_ns3_sim"
OUTPUT_FILE = PROJECT_ROOT / "analysis" / "experiments" / "ns3_topology_sweep.json"

NODE_SIZES = [5, 10, 15, 20, 30, 50, 75, 100, 150, 200, 300, 400, 500]
TOPOLOGIES = ["debruijn", "chordal_ring", "ring"]
TRIALS = 10
BASE_SEED = 42
AREA_WIDTH = 1000.0
AREA_HEIGHT = 1000.0
WIRELESS_RANGE = 200.0

def run_ns3_simulation(num_nodes, topology, seed):
    """Run ns-3 simulation and return parsed JSON metrics."""
    cmd = [
        str(NS3_BIN),
        f"--numNodes={num_nodes}",
        f"--seed={seed}",
        f"--areaWidth={AREA_WIDTH}",
        f"--areaHeight={AREA_HEIGHT}",
        f"--wirelessRange={WIRELESS_RANGE}",
        f"--topology={topology}",
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if result.returncode != 0:
            print(f"  ns-3 failed for n={num_nodes}, topo={topology}, seed={seed}: {result.stderr[:200]}")
            return None

        content = result.stdout.strip()
        # Find the JSON object (might have log output before it)
        start = content.find("{")
        end = content.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(content[start:end])
    except (json.JSONDecodeError, subprocess.TimeoutExpired, Exception) as e:
        print(f"  Error for n={num_nodes}, topo={topology}, seed={seed}: {e}")
        return None

    return None

def main():
    print("=" * 70)
    print("VECTOR ns-3 Topology Sweep: 4 topologies x 13 sizes x 10 trials")
    print("=" * 70)
    print(f"Node sizes: {NODE_SIZES}")
    print(f"Topologies: {TOPOLOGIES}")
    print(f"Trials per config: {TRIALS}")
    print(f"Total runs: {len(NODE_SIZES) * len(TOPOLOGIES) * TRIALS}")
    print(f"Output: {OUTPUT_FILE}")
    print("=" * 70)

    all_results = []

    for size in NODE_SIZES:
        print(f"\n{'='*70}")
        print(f"Running ns-3 for {size} nodes")
        print(f"{'='*70}")

        for topo in TOPOLOGIES:
            print(f"\n  Topology: {topo}")
            topo_results = []

            for trial in range(TRIALS):
                seed = BASE_SEED + trial
                r = run_ns3_simulation(size, topo, seed)
                if r:
                    topo_results.append(r)
                    # Handle both old (hopCount) and new (avgHops) field names
                    hops = r.get('hopCount', r.get('avgHops', 0))
                    print(f"  Trial {trial+1}: PDR={r['pdr']:.3f}, "
                          f"Latency={r['avgLatency']:.4f}s, "
                          f"Energy={r['avgEnergy']:.6f}J, "
                          f"Hops={hops}")

            if topo_results:
                # Add size and topology to each result for easier parsing
                for r in topo_results:
                    r["config"]["numNodes"] = size
                    r["config"]["topology"] = topo
                all_results.extend(topo_results)

                avg_pdr = sum(r["pdr"] for r in topo_results) / len(topo_results)
                avg_latency = sum(r["avgLatency"] for r in topo_results) / len(topo_results)
                avg_energy = sum(r["avgEnergy"] for r in topo_results) / len(topo_results)
                avg_hops = sum(r.get('hopCount', r.get('avgHops', 0)) for r in topo_results) / len(topo_results)

                print(f"    Average: PDR={avg_pdr:.3f}, Latency={avg_latency:.4f}s, "
                      f"Energy={avg_energy:.6f}J, Hops={avg_hops:.1f}")

    # Save all results
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        for r in all_results:
            f.write(json.dumps(r) + "\n")
    print(f"\n{'='*70}")
    print(f"Results saved to {OUTPUT_FILE}")
    print(f"Total records: {len(all_results)}")
    print(f"{'='*70}")

if __name__ == "__main__":
    main()