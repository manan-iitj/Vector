#!/usr/bin/env python3
"""VECTOR Reproducibility Verification.

Executes a small representative experiment set twice and compares corresponding
raw numerical outputs for exact equality. Deterministic experiments must produce
identical metrics across reruns with identical seeds and configurations.

Usage:
    python3 analysis/scripts/verify_reproducibility.py

Exit status:
    0  All experiments reproducible
    1  One or more discrepancies detected
"""

import csv
import os
import sys
import uuid

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

# Numeric tolerance for floating-point comparison. Deterministic outputs should
# match exactly; this tolerance exists only for edge cases where FP ordering
# could theoretically differ (it should not with the same seed).
TOLERANCE = 1e-12

# Small representative configuration for verification
VERIFY_SIZES = [10, 50]
VERIFY_SEEDS = [0, 1, 2]

EXPERIMENT_RUNNERS = {
    "clustering": run_clustering_experiment,
    "routing": run_routing_experiment,
    "security": run_security_experiment,
    "election": run_election_experiment,
    "resilience": run_failure_experiment,
    "ablation": run_ablation_experiment,
}

# Metrics that are allowed to be nondeterministic (wall-clock / host benchmarks).
# All other metrics must match exactly.
NONDETERMINISTIC_METRICS = {
    "security": {"key_provisioning_time_ms", "pairwise_key_derivation_time_ms", "auth_latency_ms"},
    "election": {"election_convergence_time_ms"},
}


def run_once(exp_name: str, sizes: list, seeds: list) -> list:
    """Run a single experiment configuration and return raw result dicts."""
    cfg = SimConfig(
        num_nodes=sizes[0],
        area_width=1000.0,
        area_height=1000.0,
        wireless_range=200.0,
        simulation_time=500.0,
        round_time=10.0,
        initial_energy=100.0,
        packet_size_bits=1000,
        packet_gen_rate=1.0,
        seed=42,
        topology="debruijn",
    )
    runner = EXPERIMENT_RUNNERS[exp_name]
    results = runner(cfg, seeds)
    return [
        {
            "experiment": r.experiment,
            "algorithm": r.algorithm,
            "topology": r.topology,
            "seed": r.seed,
            "num_nodes": r.config.num_nodes,
            **r.metrics,
        }
        for r in results
    ]


def key_for(row: dict) -> tuple:
    """Build a comparison key from scenario fields (excluding nondeterministic IDs)."""
    return (
        row["experiment"],
        row["algorithm"],
        row["topology"],
        row["seed"],
        row["num_nodes"],
        row.get("failure_fraction", ""),
    )


def compare_runs(run_a: list, run_b: list) -> list:
    """Compare two result lists for exact numeric equality."""
    discrepancies = []
    map_a = {key_for(r): r for r in run_a}
    map_b = {key_for(r): r for r in run_b}

    keys_a = set(map_a)
    keys_b = set(map_b)

    missing_in_b = keys_a - keys_b
    missing_in_a = keys_b - keys_a
    for k in sorted(missing_in_b):
        discrepancies.append(f"MISSING in run 2: {k}")
    for k in sorted(missing_in_a):
        discrepancies.append(f"MISSING in run 1: {k}")

    for k in sorted(keys_a & keys_b):
        ra = map_a[k]
        rb = map_b[k]
        exp = ra["experiment"]
        nondet = NONDETERMINISTIC_METRICS.get(exp, set())
        for metric in sorted(set(ra) | set(rb)):
            if metric in ("experiment", "algorithm", "topology", "seed", "num_nodes", "failure_fraction"):
                continue
            va = ra.get(metric, "")
            vb = rb.get(metric, "")
            if va == "" and vb == "":
                continue
            try:
                fa = float(va)
                fb = float(vb)
            except (ValueError, TypeError):
                if va != vb:
                    discrepancies.append(f"MISMATCH {k} metric={metric}: run1={va!r} run2={vb!r}")
                continue
            if metric in nondet:
                # Nondeterministic host benchmarks are not required to match.
                continue
            if abs(fa - fb) > TOLERANCE:
                discrepancies.append(
                    f"MISMATCH {k} metric={metric}: run1={fa} run2={fb} diff={abs(fa - fb)}"
                )
    return discrepancies


def main() -> None:
    os.makedirs(RAW_DIR, exist_ok=True)
    all_discrepancies = []

    for exp_name in sorted(EXPERIMENT_RUNNERS):
        print(f"[VERIFY] {exp_name} ...")
        run_a = run_once(exp_name, VERIFY_SIZES, VERIFY_SEEDS)
        run_b = run_once(exp_name, VERIFY_SIZES, VERIFY_SEEDS)
        disc = compare_runs(run_a, run_b)
        if disc:
            print(f"  {len(disc)} discrepancy/discrepancies found")
            for d in disc[:20]:
                print(f"    - {d}")
            if len(disc) > 20:
                print(f"    ... and {len(disc) - 20} more")
            all_discrepancies.extend(disc)
        else:
            print(f"  OK — all deterministic metrics match exactly")

    print()
    if all_discrepancies:
        print(f"REPRODUCIBILITY VERIFICATION FAILED: {len(all_discrepancies)} discrepancy/discrepancies")
        sys.exit(1)
    else:
        print("REPRODUCIBILITY VERIFICATION PASSED: all deterministic experiments are reproducible")


if __name__ == "__main__":
    main()
