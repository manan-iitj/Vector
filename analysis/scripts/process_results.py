#!/usr/bin/env python3
"""Aggregate raw experiment CSV files into mean/std/min/max per (experiment, algorithm, num_nodes)."""

import csv
import os
import sys
from collections import defaultdict

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

ANALYSIS_DIR = os.path.join(PROJECT_ROOT, "analysis")
RAW_DIR = os.path.join(ANALYSIS_DIR, "experiments", "raw_data")
PROCESSED_DIR = os.path.join(ANALYSIS_DIR, "experiments", "processed_data")


def mean_std(vals):
    vals = [float(v) for v in vals if v != "" and v is not None]
    if not vals:
        return None
    m = sum(vals) / len(vals)
    s = (sum((v - m) ** 2 for v in vals) / (len(vals) - 1)) ** 0.5 if len(vals) > 1 else 0.0
    return m, s, min(vals), max(vals), sorted(vals)[len(vals) // 2]


def main() -> None:
    os.makedirs(PROCESSED_DIR, exist_ok=True)
    for exp in sorted(os.listdir(RAW_DIR)):
        exp_dir = os.path.join(RAW_DIR, exp)
        if not os.path.isdir(exp_dir):
            continue
        raw_path = os.path.join(exp_dir, "raw.csv")
        if not os.path.exists(raw_path):
            continue
        rows = list(csv.DictReader(open(raw_path)))
        # metric columns = everything after the fixed config columns
        fixed = {
            "run_id", "experiment", "algorithm", "topology", "seed", "num_nodes",
            "area_width", "area_height", "wireless_range", "simulation_time",
            "initial_energy", "packet_size_bits", "topology_type", "status",
            "error", "timestamp",
        }
        metric_cols = [c for c in rows[0].keys() if c not in fixed]
        groups = defaultdict(list)
        for r in rows:
            # Include failure_fraction in grouping key for resilience experiment
            # so that different failure fractions are not averaged together.
            extra = r.get("failure_fraction", "")
            key = (r["algorithm"], r["topology"], int(r["num_nodes"]), extra)
            groups[key].append(r)
        out_dir = os.path.join(PROCESSED_DIR, exp)
        os.makedirs(out_dir, exist_ok=True)
        out_path = os.path.join(out_dir, "aggregated.csv")
        with open(out_path, "w", newline="") as f:
            w = csv.writer(f)
            header = ["experiment", "algorithm", "topology", "num_nodes", "failure_fraction", "n_runs"]
            for m in metric_cols:
                header += [f"{m}_mean", f"{m}_std", f"{m}_min", f"{m}_max", f"{m}_median"]
            w.writerow(header)
            for key in sorted(groups):
                algo, topo, size, extra = key
                items = groups[key]
                row = ["clustering" if exp == "clustering" else exp, algo, topo, size, extra, len(items)]
                for m in metric_cols:
                    vals = [it[m] for it in items if it.get(m, "") != ""]
                    ms = mean_std(vals)
                    if ms is None:
                        row += ["", "", "", "", ""]
                    else:
                        row += ms
                w.writerow(row)
        print(f"[PROCESS] {exp}: {len(rows)} raw -> {len(groups)} aggregated rows -> {out_path}")


if __name__ == "__main__":
    import csv
    main()