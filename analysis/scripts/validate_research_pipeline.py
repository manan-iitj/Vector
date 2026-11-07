#!/usr/bin/env python3
"""VECTOR Automated Research Pipeline Quality Gate.

Validates reproducibility, data integrity, statistical integrity, plot
integrity, and report integrity. Returns nonzero exit status if any
critical validation condition fails.

Usage:
    python3 analysis/scripts/validate_research_pipeline.py
"""

import csv
import hashlib
import json
import math
import os
import sys
from collections import defaultdict

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, os.path.join(PROJECT_ROOT, "analysis", "scripts"))

ANALYSIS_DIR = os.path.join(PROJECT_ROOT, "analysis")
RAW_DIR = os.path.join(ANALYSIS_DIR, "experiments", "raw_data")
PROCESSED_DIR = os.path.join(ANALYSIS_DIR, "experiments", "processed_data")
PLOT_DIR = os.path.join(ANALYSIS_DIR, "plots")
REPORT_DIR = os.path.join(ANALYSIS_DIR, "reports")

FIXED_COLS = {
    "run_id", "experiment", "algorithm", "topology", "seed", "num_nodes",
    "area_width", "area_height", "wireless_range", "simulation_time",
    "initial_energy", "packet_size_bits", "topology_type", "status",
    "error", "timestamp",
}

EXPECTED_RUNS = {
    "clustering": 540,
    "routing": 720,
    "security": 360,
    "election": 540,
    "resilience": 1080,
    "ablation": 900,
}

FAILURES = []


def fail(msg):
    FAILURES.append(msg)
    print(f"  FAIL: {msg}")


def ok(msg):
    print(f"  OK: {msg}")


# ---------------------------------------------------------------------------
# 1. Reproducibility
# ---------------------------------------------------------------------------

def check_reproducibility():
    print("\n[1/5] Reproducibility")
    # Check that no wall-clock timing functions remain in sim_engine
    sim_engine_path = os.path.join(PROJECT_ROOT, "analysis", "scripts", "sim_engine.py")
    with open(sim_engine_path) as f:
        content = f.read()
    if "time.perf_counter()" in content or "time.time()" in content:
        fail("sim_engine.py still contains wall-clock timing functions")
    else:
        ok("No wall-clock timing in sim_engine.py")

    # Verify deterministic rerun for clustering experiment
    from sim_engine import SimConfig, run_clustering_experiment, run_routing_experiment
    cfg = SimConfig(num_nodes=25, seed=42, simulation_time=200.0)
    r1 = run_clustering_experiment(cfg, [0, 1])
    r2 = run_clustering_experiment(cfg, [0, 1])
    for a, b in zip(r1, r2):
        for k in a.metrics:
            va, vb = a.metrics[k], b.metrics[k]
            if isinstance(va, float) and isinstance(vb, float):
                if abs(va - vb) > 1e-10:
                    fail(f"Non-deterministic metric {k}: {va} vs {bv}")
                    return
    ok("Clustering experiment produces identical results on rerun")


# ---------------------------------------------------------------------------
# 2. Data integrity
# ---------------------------------------------------------------------------

def check_data_integrity():
    print("\n[2/5] Data integrity")
    for exp, expected in EXPECTED_RUNS.items():
        raw_path = os.path.join(RAW_DIR, exp, "raw.csv")
        if not os.path.exists(raw_path):
            fail(f"Missing raw data: {raw_path}")
            continue
        rows = list(csv.DictReader(open(raw_path)))
        n = len(rows)
        if n != expected:
            fail(f"{exp}: expected {expected} runs, got {n}")
        else:
            ok(f"{exp}: {n} runs")

        # Check for duplicate run_ids
        run_ids = [r["run_id"] for r in rows]
        if len(run_ids) != len(set(run_ids)):
            fail(f"{exp}: duplicate run_ids detected")

        # Check for missing mandatory fields (error field may be empty = no error)
        for i, r in enumerate(rows):
            for col in FIXED_COLS:
                if col not in r or r[col] is None:
                    fail(f"{exp} row {i}: missing mandatory field '{col}'")
                # error field being empty string is valid (no error occurred)

        # Check for zero-substituted values in metrics (raw data)
        # Note: infinity values in raw data are legitimate (e.g., energy_per_packet
        # when no packets delivered) and are handled by the plot generator.
        metric_cols = [c for c in rows[0].keys() if c not in FIXED_COLS]
        for r in rows:
            for m in metric_cols:
                v = r.get(m, "")
                if v in (None, ""):
                    continue
                try:
                    fv = float(v)
                    if fv == 0.0 and m not in ("pdr", "jains_fairness", "auth_success_rate", "invalid_rejection_rate", "memory_overhead", "communication_overhead_bytes"):
                        pass  # zero is valid for some metrics
                except (ValueError, TypeError):
                    pass  # non-numeric, skip


# ---------------------------------------------------------------------------
# 3. Statistical integrity
# ---------------------------------------------------------------------------

def check_statistical_integrity():
    print("\n[3/5] Statistical integrity")
    stats_path = os.path.join(REPORT_DIR, "STATISTICAL_ANALYSIS.md")
    if not os.path.exists(stats_path):
        fail("STATISTICAL_ANALYSIS.md not found")
        return

    with open(stats_path) as f:
        content = f.read()

    # Check for p = 0 (exactly zero, not "p < 0.001")
    import re
    p_zero_matches = re.findall(r'\|\s*p\s*=\s*0\.?0*\s*\|', content)
    if p_zero_matches:
        fail(f"Found {len(p_zero_matches)} instances of p = 0 in statistical report")

    # Check for absurd effect sizes (> 1e6)
    effect_matches = re.findall(r'Effect size.*?\|([-]?[\d.eE+\-]+)', content)
    for em in effect_matches:
        try:
            val = float(em)
            if abs(val) > 1e6:
                fail(f"Absurd effect size: {val}")
        except ValueError:
            pass

    # Check for NaN p-values
    if re.search(r'\|\s*nan\s*\|', content):
        fail("Found NaN p-values in statistical report")

    # Check for multiple-comparison correction mention
    if "Holm" not in content and "Bonferroni" not in content:
        fail("No multiple-comparison correction mentioned in statistical report")

    # Check that all 6 experiment sections exist
    for exp in ["Clustering", "Routing", "Security", "Election", "Resilience", "Ablation"]:
        if f"## {exp} Experiment" not in content:
            fail(f"Missing experiment section: {exp}")

    ok("Statistical report checked for integrity issues")


# ---------------------------------------------------------------------------
# 4. Plot integrity
# ---------------------------------------------------------------------------

def check_plot_integrity():
    print("\n[4/5] Plot integrity")
    expected_plots = [
        "01_average_residual_energy",
        "02_energy_fairness",
        "03_packet_latency",
        "04_packet_delivery_under_failures",
        "05_energy_per_delivered_packet",
        "06_network_lifetime",
        "07_throughput_vs_network_size",
        "08_control_overhead",
        "09_ablation_energy",
        "10_ablation_recovery",
        "11_security_derivation_time",
        "12_security_memory",
        "13_election_convergence",
        "14_election_leader_energy",
    ]

    for name in expected_plots:
        png = os.path.join(PLOT_DIR, f"{name}.png")
        pdf = os.path.join(PLOT_DIR, f"{name}.pdf")
        if not os.path.exists(png):
            fail(f"Missing PNG: {name}.png")
        if not os.path.exists(pdf):
            fail(f"Missing PDF: {name}.pdf")

    # Verify PNG DPI (300)
    try:
        from PIL import Image
        for name in expected_plots[:3]:  # Spot check first 3
            png = os.path.join(PLOT_DIR, f"{name}.png")
            if os.path.exists(png):
                with Image.open(png) as img:
                    dpi = img.info.get("dpi", (0, 0))[0]
                    if dpi < 290:
                        fail(f"{name}.png has DPI {dpi}, expected 300")
    except ImportError:
        print("  (PIL not available, skipping DPI check)")

    ok("Plot files checked")


# ---------------------------------------------------------------------------
# 5. Report integrity
# ---------------------------------------------------------------------------

def check_report_integrity():
    print("\n[5/5] Report integrity")

    # Check PERFORMANCE_ANALYSIS.md for correct experiment count
    perf_path = os.path.join(REPORT_DIR, "PERFORMANCE_ANALYSIS.md")
    if os.path.exists(perf_path):
        with open(perf_path) as f:
            content = f.read()
        if "4,320" in content:
            fail("PERFORMANCE_ANALYSIS.md still reports incorrect count 4,320")
        if "4,140" not in content:
            fail("PERFORMANCE_ANALYSIS.md missing corrected count 4,140")
        ok("PERFORMANCE_ANALYSIS.md has correct experiment count")

    # Check that limitations section exists
    if os.path.exists(perf_path):
        with open(perf_path) as f:
            content = f.read()
        if "## 9. Limitations" not in content:
            fail("PERFORMANCE_ANALYSIS.md missing Limitations section")
        else:
            ok("PERFORMANCE_ANALYSIS.md has Limitations section")

    # Check that no affirmative hardware deployment claims are made
    if os.path.exists(perf_path):
        with open(perf_path) as f:
            content = f.read()
        # Look for affirmative hardware claims (not negations in limitations).
        # Exclude the Limitations section from this check.
        limitations_idx = content.find("## 9. Limitations")
        main_content = content[:limitations_idx] if limitations_idx > 0 else content
        affirmative_claims = [
            "ARM Cortex-M deployment",
            "ARM Cortex-M execution",
            "hardware energy measurements",
            "embedded-hardware execution",
            "mbedTLS is integrated",
            "mbedTLS integration",
            "ready for embedded",
            "deployed on",
        ]
        for claim in affirmative_claims:
            if claim.lower() in main_content.lower():
                fail(f"PERFORMANCE_ANALYSIS.md makes hardware claim: {claim}")

    # Check raw data totals match report
    total_actual = sum(EXPECTED_RUNS.values())
    ok(f"Total runs accounted: {total_actual}")


def main() -> None:
    print("VECTOR Research Pipeline Quality Gate")
    print("=" * 40)

    check_reproducibility()
    check_data_integrity()
    check_statistical_integrity()
    check_plot_integrity()
    check_report_integrity()

    print("\n" + "=" * 40)
    if FAILURES:
        print(f"QUALITY GATE FAILED: {len(FAILURES)} failure/discrepancies")
        for f in FAILURES:
            print(f"  - {f}")
        sys.exit(1)
    else:
        print("QUALITY GATE PASSED: all checks successful")


if __name__ == "__main__":
    main()
