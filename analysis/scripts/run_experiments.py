#!/usr/bin/env python3
"""VECTOR Comparative Analysis - Experiment Runner.

Executes all experiments, collects raw metrics into structured CSV files.

Usage:
    python3 analysis/scripts/run_experiments.py --all
    python3 analysis/scripts/run_experiments.py --experiment clustering
"""

import argparse
import csv
import os
import sys
import uuid
from datetime import datetime
from typing import Dict, List

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, os.path.join(PROJECT_ROOT, "analysis", "scripts"))

from sim_engine import (
    SimConfig,
    run_clustering_experiment,
    run_routing_experiment,
    run_security_experiment,
    run_election_experiment,
    run_failure_experiment,
    run_ablation_experiment,
)

ANALYSIS_DIR = os.path.join(PROJECT_ROOT, "analysis")
RAW_DIR = os.path.join(ANALYSIS_DIR, "experiments", "raw_data")
PROCESSED_DIR = os.path.join(ANALYSIS_DIR, "experiments", "processed_data")

NETWORK_SIZES = [10, 20, 30, 50, 75, 100]
N_SEEDS = 30


def ensure_dirs() -> None:
    os.makedirs(RAW_DIR, exist_ok=True)
    os.makedirs(PROCESSED_DIR, exist_ok=True)
    for sub in ["clustering", "routing", "security", "election", "resilience", "ablation"]:
        os.makedirs(os.path.join(RAW_DIR, sub), exist_ok=True)
        os.makedirs(os.path.join(PROCESSED_DIR, sub), exist_ok=True)


def flatten_metrics(r) -> Dict:
    return {
        "run_id": r.run_id,
        "experiment": r.experiment,
        "algorithm": r.algorithm,
        "topology": r.topology,
        "seed": r.seed,
        "num_nodes": r.config.num_nodes,
        "area_width": r.config.area_width,
        "area_height": r.config.area_height,
        "wireless_range": r.config.wireless_range,
        "simulation_time": r.config.simulation_time,
        "initial_energy": r.config.initial_energy,
        "packet_size_bits": r.config.packet_size_bits,
        "topology_type": r.config.topology,
        "status": r.status,
        "error": r.error or "",
        "timestamp": datetime.now().isoformat(),
        **r.metrics,
    }


def save_raw(results, experiment: str) -> None:
    exp_dir = os.path.join(RAW_DIR, experiment)
    os.makedirs(exp_dir, exist_ok=True)
    path = os.path.join(exp_dir, "raw.csv")
    rows = [flatten_metrics(r) for r in results]
    if not rows:
        return
    fields = list(rows[0].keys())
    write_header = not os.path.exists(path)
    with open(path, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        if write_header:
            w.writeheader()
        w.writerows(rows)
    print(f"  [RAW] {experiment}: {len(rows)} rows -> {path}")


def run_experiment(name: str, sizes: List[int], seeds: List[int]) -> List:
    all_results = []
    for size in sizes:
        cfg = SimConfig(
            num_nodes=size,
            area_width=1000.0,
            area_height=1000.0,
            wireless_range=200.0,
            simulation_time=1000.0,
            round_time=10.0,
            initial_energy=100.0,
            packet_size_bits=1000,
            packet_gen_rate=1.0,
            seed=42,
            topology="debruijn",
        )
        if name == "clustering":
            res = run_clustering_experiment(cfg, seeds)
        elif name == "routing":
            res = run_routing_experiment(cfg, seeds)
        elif name == "security":
            res = run_security_experiment(cfg, seeds)
        elif name == "election":
            res = run_election_experiment(cfg, seeds)
        elif name == "resilience":
            res = run_failure_experiment(cfg, seeds)
        elif name == "ablation":
            res = run_ablation_experiment(cfg, seeds)
        else:
            raise ValueError(f"Unknown experiment: {name}")
        all_results.extend(res)
    save_raw(all_results, name)
    return all_results


def main() -> None:
    parser = argparse.ArgumentParser(description="VECTOR Comparative Analysis Runner")
    parser.add_argument("--all", action="store_true", help="Run all experiments")
    parser.add_argument("--experiment", type=str, default=None, help="Run a single experiment")
    parser.add_argument("--sizes", type=str, default=None, help="Comma-separated network sizes")
    parser.add_argument("--seeds", type=int, default=N_SEEDS, help="Number of independent seeds")
    args = parser.parse_args()

    ensure_dirs()
    sizes = [int(s) for s in args.sizes.split(",")] if args.sizes else NETWORK_SIZES
    seeds = list(range(args.seeds))

    experiments = ["clustering", "routing", "security", "election", "resilience", "ablation"] if args.all else \
        ([args.experiment] if args.experiment else [])

    if not experiments:
        parser.print_help()
        return

    for exp in experiments:
        print(f"[RUN] {exp} (sizes={sizes}, seeds={len(seeds)})")
        run_experiment(exp, sizes, seeds)

    print("\n[DONE] Raw data saved to analysis/experiments/raw_data/")


if __name__ == "__main__":
    main()